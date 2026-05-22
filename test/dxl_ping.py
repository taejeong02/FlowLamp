#!/usr/bin/env python3
"""Small Dynamixel SDK smoke test.

Examples:
  python3 dxl_ping.py --port /dev/ttyUSB0 --id 1
  python3 dxl_ping.py --port /dev/ttyUSB0 --id 1 --baudrate 1000000
"""

import argparse
import sys

from dynamixel_sdk import PacketHandler, PortHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ping a Dynamixel servo.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device path")
    parser.add_argument("--id", type=int, default=1, help="Dynamixel ID")
    parser.add_argument("--baudrate", type=int, default=57600, help="Baudrate")
    parser.add_argument(
        "--protocol",
        type=float,
        default=2.0,
        choices=(1.0, 2.0),
        help="Dynamixel protocol version",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    port_handler = PortHandler(args.port)
    packet_handler = PacketHandler(args.protocol)

    if not port_handler.openPort():
        print(f"Failed to open port: {args.port}", file=sys.stderr)
        return 1

    try:
        if not port_handler.setBaudRate(args.baudrate):
            print(f"Failed to set baudrate: {args.baudrate}", file=sys.stderr)
            return 1

        model_number, result, error = packet_handler.ping(port_handler, args.id)
        if result != 0:
            print(packet_handler.getTxRxResult(result), file=sys.stderr)
            return 1
        if error != 0:
            print(packet_handler.getRxPacketError(error), file=sys.stderr)
            return 1

        print(f"Found Dynamixel ID {args.id}, model number: {model_number}")
        return 0
    finally:
        port_handler.closePort()


if __name__ == "__main__":
    raise SystemExit(main())
