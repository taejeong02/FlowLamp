#!/usr/bin/env python3
"""Scan a Dynamixel bus for responding IDs."""

import argparse
import sys

from dynamixel_sdk import PacketHandler, PortHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Dynamixel IDs.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device path")
    parser.add_argument("--baudrate", type=int, default=57600, help="Baudrate")
    parser.add_argument("--protocol", type=float, default=2.0, choices=(1.0, 2.0))
    parser.add_argument("--start", type=int, default=0, help="First ID to scan")
    parser.add_argument("--end", type=int, default=20, help="Last ID to scan")
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

        found = []
        for dxl_id in range(args.start, args.end + 1):
            model_number, result, error = packet_handler.ping(port_handler, dxl_id)
            if result == 0 and error == 0:
                found.append((dxl_id, model_number))
                print(f"ID {dxl_id}: model {model_number}")

        if not found:
            print("No Dynamixel IDs found.")
            return 1

        print(f"Found {len(found)} Dynamixel(s).")
        return 0
    finally:
        port_handler.closePort()


if __name__ == "__main__":
    raise SystemExit(main())
