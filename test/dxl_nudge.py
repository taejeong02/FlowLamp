#!/usr/bin/env python3
"""Move Dynamixel servos a tiny amount and return them to their start position."""

import argparse
import sys
import time

from dynamixel_sdk import PacketHandler, PortHandler

ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
ADDR_PRESENT_POSITION = 132


def parse_ids(value: str) -> list[int]:
    ids = []
    for item in value.split(","):
        item = item.strip()
        if item:
            ids.append(int(item))
    if not ids:
        raise argparse.ArgumentTypeError("at least one ID is required")
    return ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gently nudge Dynamixel servos.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device path")
    parser.add_argument("--baudrate", type=int, default=57600, help="Baudrate")
    parser.add_argument("--protocol", type=float, default=2.0, choices=(1.0, 2.0))
    parser.add_argument("--ids", type=parse_ids, default=[1], help="Comma-separated IDs")
    parser.add_argument("--delta", type=int, default=80, help="Position tick movement")
    parser.add_argument("--pause", type=float, default=0.6, help="Seconds between moves")
    return parser.parse_args()


def check_result(packet_handler: PacketHandler, result: int, error: int) -> bool:
    if result != 0:
        print(packet_handler.getTxRxResult(result), file=sys.stderr)
        return False
    if error != 0:
        print(packet_handler.getRxPacketError(error), file=sys.stderr)
        return False
    return True


def read_position(packet_handler: PacketHandler, port_handler: PortHandler, dxl_id: int) -> int | None:
    position, result, error = packet_handler.read4ByteTxRx(
        port_handler,
        dxl_id,
        ADDR_PRESENT_POSITION,
    )
    if not check_result(packet_handler, result, error):
        return None
    return position


def write_position(
    packet_handler: PacketHandler,
    port_handler: PortHandler,
    dxl_id: int,
    position: int,
) -> bool:
    result, error = packet_handler.write4ByteTxRx(
        port_handler,
        dxl_id,
        ADDR_GOAL_POSITION,
        position,
    )
    return check_result(packet_handler, result, error)


def write_torque(
    packet_handler: PacketHandler,
    port_handler: PortHandler,
    dxl_id: int,
    enabled: bool,
) -> bool:
    result, error = packet_handler.write1ByteTxRx(
        port_handler,
        dxl_id,
        ADDR_TORQUE_ENABLE,
        1 if enabled else 0,
    )
    return check_result(packet_handler, result, error)


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

        start_positions = {}
        for dxl_id in args.ids:
            position = read_position(packet_handler, port_handler, dxl_id)
            if position is None:
                print(f"Failed to read present position for ID {dxl_id}", file=sys.stderr)
                return 1
            start_positions[dxl_id] = position
            print(f"ID {dxl_id}: start position {position}")

        for dxl_id in args.ids:
            if not write_torque(packet_handler, port_handler, dxl_id, True):
                print(f"Failed to enable torque for ID {dxl_id}", file=sys.stderr)
                return 1

        for dxl_id, start in start_positions.items():
            target = start + args.delta
            print(f"ID {dxl_id}: moving to {target}")
            if not write_position(packet_handler, port_handler, dxl_id, target):
                return 1

        time.sleep(args.pause)

        for dxl_id, start in start_positions.items():
            print(f"ID {dxl_id}: returning to {start}")
            if not write_position(packet_handler, port_handler, dxl_id, start):
                return 1

        time.sleep(args.pause)
        print("Nudge test complete.")
        return 0
    finally:
        port_handler.closePort()


if __name__ == "__main__":
    raise SystemExit(main())
