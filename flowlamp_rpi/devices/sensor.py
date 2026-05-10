"""PIR 센서로 사람의 접근과 움직임을 감지합니다."""

from __future__ import annotations

import time
from typing import Callable

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    GPIO = None


MotionCallback = Callable[[], None]
_pir_sensor: "PIRSensor | None" = None


class PIRSensor:
    """GPIO 입력 핀에 연결된 PIR 센서의 움직임 감지를 처리합니다."""

    def __init__(
        self,
        pin: int = 17,
        *,
        gpio_mode: int | None = None,
        active_high: bool = True,
        pull_up_down: int | None = None,
        debounce_ms: int = 300,
        warmup_seconds: float = 2.0,
    ) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO is required to use PIRSensor on Raspberry Pi.")

        self.pin = pin
        self.active_high = active_high
        self.debounce_ms = debounce_ms
        self._callback: MotionCallback | None = None
        self._event_registered = False

        GPIO.setwarnings(False)
        GPIO.setmode(gpio_mode or GPIO.BCM)
        GPIO.setup(pin, GPIO.IN, pull_up_down=pull_up_down or GPIO.PUD_DOWN)

        if warmup_seconds > 0:
            time.sleep(warmup_seconds)

    def is_person_detected(self) -> bool:
        """PIR 센서가 움직임을 감지하면 True를 반환합니다."""
        value = GPIO.input(self.pin)
        return bool(value) if self.active_high else not bool(value)

    def wait_for_person(self, timeout: float | None = None) -> bool:
        """움직임이 감지되거나 제한 시간이 지날 때까지 기다립니다."""
        start_time = time.monotonic()

        while True:
            if self.is_person_detected():
                return True

            if timeout is not None and time.monotonic() - start_time >= timeout:
                return False

            time.sleep(0.05)

    def on_person_detected(self, callback: MotionCallback) -> None:
        """PIR 센서가 감지 상태로 바뀔 때마다 콜백 함수를 실행합니다."""
        self._callback = callback
        edge = GPIO.RISING if self.active_high else GPIO.FALLING
        GPIO.add_event_detect(
            self.pin,
            edge,
            callback=self._handle_motion,
            bouncetime=self.debounce_ms,
        )
        self._event_registered = True

    def cleanup(self) -> None:
        """이 센서에서 사용한 GPIO 자원을 정리합니다."""
        if self._event_registered:
            GPIO.remove_event_detect(self.pin)
            self._event_registered = False
        GPIO.cleanup(self.pin)

    def _handle_motion(self, _pin: int) -> None:
        if self._callback is not None and self.is_person_detected():
            self._callback()


def setup_pir_sensor(pin: int = 17, *, warmup_seconds: float = 2.0) -> None:
    """메인 프로그램에서 함께 사용할 PIR 센서를 초기화합니다."""
    global _pir_sensor
    _pir_sensor = PIRSensor(pin=pin, warmup_seconds=warmup_seconds)


def is_person_detected() -> bool:
    """공유 PIR 센서가 움직임을 감지하면 True를 반환합니다."""
    if _pir_sensor is None:
        setup_pir_sensor()

    return _pir_sensor.is_person_detected()


def wait_for_person(timeout: float | None = None) -> bool:
    """공유 PIR 센서가 움직임을 감지할 때까지 기다립니다."""
    if _pir_sensor is None:
        setup_pir_sensor()

    return _pir_sensor.wait_for_person(timeout=timeout)


def on_person_detected(callback: MotionCallback) -> None:
    """움직임 감지 시 실행할 콜백 함수를 등록합니다."""
    if _pir_sensor is None:
        setup_pir_sensor()

    _pir_sensor.on_person_detected(callback)


def cleanup_sensor() -> None:
    """공유 PIR 센서에서 사용한 GPIO 자원을 정리합니다."""
    global _pir_sensor

    if _pir_sensor is not None:
        _pir_sensor.cleanup()
        _pir_sensor = None


def main() -> None:
    setup_pir_sensor(pin=17)

    try:
        print("PIR 센서 준비 완료. 움직임을 기다리는 중...")
        while True:
            if wait_for_person(timeout=1.0):
                print("사람 접근이 감지되었습니다.")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("PIR 센서를 종료합니다.")
    finally:
        cleanup_sensor()


if __name__ == "__main__":
    main()
