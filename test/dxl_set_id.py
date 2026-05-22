#!/usr/bin/env python3
"""Change a Dynamixel servo ID."""

import argparse
import sys

from dynamixel_sdk import PacketHandler, PortHandler

ADDR_ID = 7
ADDR_TORQUE_ENABLE = 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Change a Dynamixel ID.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device path")
    parser.add_argument("--baudrate", type=int, default=57600, help="Baudrate")
    parser.add_argument("--protocol", type=float, default=2.0, choices=(1.0, 2.0))
    parser.add_argument("--old-id", type=int, required=True, help="Current Dynamixel ID")
    parser.add_argument("--new-id", type=int, required=True, help="New Dynamixel ID")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 0 <= args.new_id <= 252:
        print("New ID must be between 0 and 252.", file=sys.stderr)
        return 1

    port_handler = PortHandler(args.port)
    packet_handler = PacketHandler(args.protocol)

    if not port_handler.openPort():
        print(f"Failed to open port: {args.port}", file=sys.stderr)
        return 1

    try:
        if not port_handler.setBaudRate(args.baudrate):
            print(f"Failed to set baudrate: {args.baudrate}", file=sys.stderr)
            return 1

        print(f"Pinging ID {args.old_id}...")
        _, result, error = packet_handler.ping(port_handler, args.old_id)
        if result != 0:
            print(packet_handler.getTxRxResult(result), file=sys.stderr)
            return 1
        if error != 0:
            print(packet_handler.getRxPacketError(error), file=sys.stderr)
            return 1

        print("Disabling torque...")
        result, error = packet_handler.write1ByteTxRx(
            port_handler,
            args.old_id,
            ADDR_TORQUE_ENABLE,
            0,
        )
        if result != 0:
            print(packet_handler.getTxRxResult(result), file=sys.stderr)
            return 1
        if error != 0:
            print(packet_handler.getRxPacketError(error), file=sys.stderr)
            return 1

        print(f"Writing new ID {args.new_id}...")
        result, error = packet_handler.write1ByteTxRx(
            port_handler,
            args.old_id,
            ADDR_ID,
            args.new_id,
        )
        if result != 0:
            print(packet_handler.getTxRxResult(result), file=sys.stderr)
            return 1
        if error != 0:
            print(packet_handler.getRxPacketError(error), file=sys.stderr)
            return 1

        print(f"Changed Dynamixel ID {args.old_id} -> {args.new_id}")
        return 0
    finally:
        port_handler.closePort()


if __name__ == "__main__":
    raise SystemExit(main())
