# Raspberry Pi Device Tests

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

Start a browser camera stream:

```bash
python3 camera_web.py --port 8080
```

Then open:

```text
http://<raspberry-pi-ip>:8080
```
