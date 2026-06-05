"""LED device control over SPI."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

try:
    import spidev  # type: ignore

    HAS_SPI = True
except ImportError:
    spidev = None
    HAS_SPI = False
    print("SPI 라이브러리가 없어 LED를 시뮬레이션 모드로 실행합니다.")


class LEDController:
    """WS2812 LED strip controller.

    This uses the same SPI encoding as test/led_test.py, so API requests from
    main.py control the strip connected to SPI0 MOSI, physical pin 19.
    """

    LED_COUNT = 72
    BRIGHTNESS = 255
    SPI_BUS = 0
    SPI_DEVICE = 0
    SPI_SPEED_HZ = 2_400_000
    COLOR_ORDER = "GRB"

    def __init__(self):
        self.is_on = False
        self.is_night_mode = False
        self.brightness = self.BRIGHTNESS
        self.current_color = (255, 255, 255)
        self.alert_running = False
        self.posture_alert_running = False

        self._lock = threading.Lock()
        self._posture_alert_stop = threading.Event()
        self._posture_alert_thread: threading.Thread | None = None
        self.spi: Any | None = None
        self.simulation = True

        self._open_spi()

    def _open_spi(self):
        if not HAS_SPI or spidev is None:
            return

        spi = spidev.SpiDev()

        try:
            spi.open(self.SPI_BUS, self.SPI_DEVICE)
        except FileNotFoundError:
            self._print_spi_setup_help()
            return
        except PermissionError:
            print("SPI 장치 권한이 없어 LED를 시뮬레이션 모드로 실행합니다.")
            print("필요하면 sudo로 실행하거나 /dev/spidev0.0 권한을 확인하세요.")
            return

        spi.max_speed_hz = self.SPI_SPEED_HZ
        spi.mode = 0
        self.spi = spi
        self.simulation = False
        self.clear()
        print("LED SPI controller ready: SPI0 MOSI, physical pin 19.")

    def _print_spi_setup_help(self):
        print("SPI 장치를 찾지 못해 LED를 시뮬레이션 모드로 실행합니다.")
        if Path("/sys/class/spidev/spidev0.0/dev").exists():
            print("커널은 spidev0.0을 보지만 /dev/spidev0.0이 없습니다. 재부팅을 시도하세요.")
        else:
            print("raspi-config에서 SPI를 활성화한 뒤 재부팅하세요.")

    def _clamp_color_value(self, value):
        return max(0, min(255, int(value)))

    def _scale(self, value):
        return max(0, min(255, value * self.brightness // 255))

    def _order_color(self, red, green, blue):
        values = {
            "R": self._scale(red),
            "G": self._scale(green),
            "B": self._scale(blue),
        }
        return [values[channel] for channel in self.COLOR_ORDER]

    def _encode_byte(self, value):
        encoded = 0
        for bit in range(7, -1, -1):
            encoded <<= 3
            encoded |= 0b110 if value & (1 << bit) else 0b100

        return [
            (encoded >> 16) & 0xFF,
            (encoded >> 8) & 0xFF,
            encoded & 0xFF,
        ]

    def _encode_pixels(self, pixels):
        data = []
        for red, green, blue in pixels:
            for value in self._order_color(red, green, blue):
                data.extend(self._encode_byte(value))

        data.extend([0] * 80)
        return data

    def _show(self, pixels):
        if self.simulation or self.spi is None:
            return

        self.spi.xfer3(self._encode_pixels(pixels))

    def _fill(self, color):
        self._show([color] * self.LED_COUNT)

    def _apply_color(self, r, g, b):
        if not self.is_on:
            r, g, b = 0, 0, 0

        r = self._clamp_color_value(r)
        g = self._clamp_color_value(g)
        b = self._clamp_color_value(b)

        with self._lock:
            self._fill((r, g, b))

        if self.simulation:
            state = "ON" if self.is_on else "OFF"
            print(f"[LED {state}] R:{r} G:{g} B:{b} brightness:{self.brightness_percent}%")

    def turn_on(self):
        self.is_on = True
        self._apply_color(*self.current_color)

    def turn_off(self):
        self.is_on = False
        self._apply_color(0, 0, 0)

    def set_color(self, r, g, b):
        self.current_color = (
            self._clamp_color_value(r),
            self._clamp_color_value(g),
            self._clamp_color_value(b),
        )

        if self.is_on:
            self._apply_color(*self.current_color)

    def set_brightness(self, value):
        percent = max(0, min(100, int(value)))
        self.brightness = round(percent / 100 * 255)

        if self.is_on:
            self._apply_color(*self.current_color)

    @property
    def brightness_percent(self):
        return round(self.brightness / 255 * 100)

    def set_night_mode(self, active: bool):
        """Apply a warmer color while preserving the current API contract."""
        self.is_night_mode = active
        self.current_color = (255, 100, 20) if active else (255, 255, 255)

        if self.is_on:
            self._apply_color(*self.current_color)

    def blink_alert(self):
        """Blink red for timer/posture alerts without blocking the API thread."""
        if self.alert_running:
            return

        def run_blink():
            self.alert_running = True
            original_state = self.is_on
            self.is_on = True

            for _ in range(3):
                self._apply_color(255, 0, 0)
                time.sleep(0.3)
                self._apply_color(0, 0, 0)
                time.sleep(0.3)

            self.is_on = original_state
            self._apply_color(*self.current_color)
            self.alert_running = False

        threading.Thread(target=run_blink, name="led-alert", daemon=True).start()

    def start_posture_alert(self):
        """Blink red continuously until the posture warning is cleared."""
        if self.posture_alert_running:
            return

        self.posture_alert_running = True
        self._posture_alert_stop.clear()

        def show_alert_color(color):
            with self._lock:
                self._fill(color)
            if self.simulation:
                print(
                    f"[LED POSTURE ALERT] R:{color[0]} G:{color[1]} B:{color[2]}"
                )

        def run_blink():
            while not self._posture_alert_stop.is_set():
                show_alert_color((255, 0, 0))
                if self._posture_alert_stop.wait(0.35):
                    break
                show_alert_color((0, 0, 0))
                if self._posture_alert_stop.wait(0.35):
                    break

            self._apply_color(*self.current_color)
            self.posture_alert_running = False

        self._posture_alert_thread = threading.Thread(
            target=run_blink,
            name="led-posture-alert",
            daemon=True,
        )
        self._posture_alert_thread.start()

    def stop_posture_alert(self):
        """Stop continuous posture blinking and restore the previous LED state."""
        if not self.posture_alert_running:
            return

        self._posture_alert_stop.set()
        thread = self._posture_alert_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1)
        self._posture_alert_thread = None

    def clear(self):
        with self._lock:
            self._fill((0, 0, 0))

    def close(self):
        self.stop_posture_alert()
        self.clear()
        if self.spi is not None:
            self.spi.close()
            self.spi = None
            self.simulation = True
