# Dynamixel SDK Python Starter

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `pip install -r requirements.txt` says `externally-managed-environment`, the
virtual environment is not active. Run this first:

```bash
source .venv/bin/activate
```

## WS2812 LED Test

For Raspberry Pi 5, use SPI output:

- WS2812 `DIN` or `DI` to physical pin 19, GPIO10, SPI0 MOSI
- WS2812 `5V` to Raspberry Pi 3.3V for a low-power signal test
- WS2812 `GND` to Raspberry Pi GND

The test script only drives the first LED at low brightness. Do not power a long
strip from the Raspberry Pi 3.3V pin.

Enable SPI first:

```bash
sudo raspi-config
```

Choose `Interface Options` -> `SPI` -> `Enable`, then reboot.

Check that SPI is visible:

```bash
ls /dev/spidev*
```

```bash
source .venv/bin/activate
python led_test.py
```

If there is a permission error, run it with sudo:

```bash
sudo .venv/bin/python led_test.py
```

If the virtual environment does not exist yet:

```bash
sudo apt install python3-venv python3-dev build-essential
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python3 dxl_ping.py --port /dev/ttyUSB0 --id 1
```

Scan connected IDs:

```bash
python3 dxl_scan.py --port /dev/ttyUSB0 --start 1 --end 4
```

Gently move one motor and return it to its original position:

```bash
python3 dxl_nudge.py --port /dev/ttyUSB0 --ids 1 --delta 80
```

Gently move all four motors:

```bash
python3 dxl_nudge.py --port /dev/ttyUSB0 --ids 1,2,3,4 --delta 80
```

Control four motors with the keyboard:

```bash
python3 dxl_arrow_test.py --port /dev/ttyUSB0
```

Default motor keys:

```text
ID 1: Q / A
ID 2: W / S
ID 3: E / D
ID 4: R / F
```

Use `Space` to stop all motors and `x` to quit.

The default speed is very slow. Hold a key to move, release it to stop.

Use a slower or faster velocity:

```bash
python3 dxl_arrow_test.py --port /dev/ttyUSB0 --speed 5
```

Start a browser camera stream:

```bash
python3 camera_web.py --port 8080
```

Then open:

```text
http://<raspberry-pi-ip>:8080
```

If the servo uses a different baudrate:

```bash
python3 dxl_ping.py --port /dev/ttyUSB0 --id 1 --baudrate 1000000
```

On Linux, if you get a permission error for `/dev/ttyUSB0`, add your user to the
serial device group and reconnect:

```bash
sudo usermod -aG dialout "$USER"
```

Then log out and log back in.
