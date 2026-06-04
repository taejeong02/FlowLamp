from time import sleep
from pathlib import Path

import spidev


LED_COUNT = 72
BRIGHTNESS = 255

SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 2_400_000

COLOR_ORDER = "GRB"


def scale(value):
    return max(0, min(255, value * BRIGHTNESS // 255))


def order_color(red, green, blue):
    values = {
        "R": scale(red),
        "G": scale(green),
        "B": scale(blue),
    }
    return [values[channel] for channel in COLOR_ORDER]


def encode_byte(value):
    encoded = 0
    for bit in range(7, -1, -1):
        encoded <<= 3
        encoded |= 0b110 if value & (1 << bit) else 0b100

    return [
        (encoded >> 16) & 0xFF,
        (encoded >> 8) & 0xFF,
        encoded & 0xFF,
    ]


def encode_pixels(pixels):
    data = []
    for red, green, blue in pixels:
        for value in order_color(red, green, blue):
            data.extend(encode_byte(value))

    data.extend([0] * 80)
    return data


def show(spi, pixels):
    spi.xfer3(encode_pixels(pixels))


def fill(spi, color):
    show(spi, [color] * LED_COUNT)


def color_wipe(spi, color, wait_seconds=0.03):
    pixels = [(0, 0, 0)] * LED_COUNT

    for index in range(LED_COUNT):
        pixels[index] = color
        show(spi, pixels)
        sleep(wait_seconds)


def clear(spi):
    fill(spi, (0, 0, 0))


def main():
    spi = spidev.SpiDev()

    try:
        spi.open(SPI_BUS, SPI_DEVICE)
    except FileNotFoundError as error:
        print("SPI device was not found: /dev/spidev0.0")
        print("")
        if Path("/sys/class/spidev/spidev0.0/dev").exists():
            print("The kernel sees spidev0.0, but /dev/spidev0.0 was not created.")
            print("Try rebooting first:")
            print("  sudo reboot")
            print("")
            print("If it is still missing after reboot, recreate device nodes:")
            print("  sudo udevadm trigger")
            print("")
        print("Enable SPI:")
        print("  sudo raspi-config")
        print("  Interface Options -> SPI -> Enable")
        print("")
        print("Then reboot:")
        print("  sudo reboot")
        raise SystemExit(1) from error
    except PermissionError as error:
        print("SPI device exists, but this user cannot access it.")
        print("Try:")
        print("  sudo .venv/bin/python led_test.py")
        raise SystemExit(1) from error

    spi.max_speed_hz = SPI_SPEED_HZ
    spi.mode = 0

    try:
        print("Testing WS2812 strip over SPI.", flush=True)
        print("Data wire: physical pin 19, GPIO10, SPI0 MOSI", flush=True)
        print(f"LED count: {LED_COUNT}, brightness: {BRIGHTNESS}/255", flush=True)
        print("Press Ctrl+C to stop.", flush=True)

        while True:
            print("Red", flush=True)
            color_wipe(spi, (255, 0, 0))
            sleep(0.5)

            print("Green", flush=True)
            color_wipe(spi, (0, 255, 0))
            sleep(0.5)

            print("Blue", flush=True)
            color_wipe(spi, (0, 0, 255))
            sleep(0.5)

            print("White", flush=True)
            fill(spi, (255, 255, 255))
            sleep(1.0)

            print("Off", flush=True)
            clear(spi)
            sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)
    finally:
        clear(spi)
        spi.close()


if __name__ == "__main__":
    main()
