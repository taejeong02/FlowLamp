#!/usr/bin/env python3
"""Drive four Dynamixel motors with keyboard pairs.

This script targets common Protocol 2.0 X-series control table addresses.
It uses Velocity Control Mode, so it is best suited for wheel/continuous
movement tests.
"""

import argparse
import select
import sys
import termios
import time
import tty

from dynamixel_sdk import PacketHandler, PortHandler

ADDR_OPERATING_MODE = 11
ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_VELOCITY = 104

MODE_VELOCITY_CONTROL = 1
TORQUE_DISABLE = 0
TORQUE_ENABLE = 1

KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT = "\x1b[D"
ALT_KEY_UP = "\x1bOA"
ALT_KEY_DOWN = "\x1bOB"
ALT_KEY_RIGHT = "\x1bOC"
ALT_KEY_LEFT = "\x1bOD"
DEFAULT_KEY_PAIRS = ("qa", "ws", "ed", "rf")


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
    parser = argparse.ArgumentParser(description="Control Dynamixel motors with keyboard pairs.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial device path")
    parser.add_argument("--baudrate", type=int, default=57600, help="Baudrate")
    parser.add_argument("--protocol", type=float, default=2.0, choices=(1.0, 2.0))
    parser.add_argument("--ids", type=parse_ids, default=[1, 2, 3, 4], help="Comma-separated motor IDs")
    parser.add_argument("--left-ids", type=parse_ids, default=[1, 3], help="IDs used for left turn group")
    parser.add_argument("--right-ids", type=parse_ids, default=[2, 4], help="IDs used for right turn group")
    parser.add_argument(
        "--key-pairs",
        default=",".join(DEFAULT_KEY_PAIRS),
        help="Comma-separated forward/backward key pairs for each motor ID",
    )
    parser.add_argument("--speed", type=int, default=10, help="Goal velocity tick value")
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.12,
        help="Stop motors if no control key is received for this many seconds",
    )
    parser.add_argument(
        "--keep-torque",
        action="store_true",
        help="Leave torque enabled when exiting",
    )
    parser.add_argument(
        "--hold",
        action="store_true",
        help="Keep moving until another control key or Space is pressed",
    )
    parser.add_argument(
        "--debug-keys",
        action="store_true",
        help="Print received key codes without driving motors",
    )
    return parser.parse_args()


def check_result(packet_handler: PacketHandler, result: int, error: int, action: str) -> bool:
    if result != 0:
        print(f"{action}: {packet_handler.getTxRxResult(result)}", file=sys.stderr)
        return False
    if error != 0:
        print(f"{action}: {packet_handler.getRxPacketError(error)}", file=sys.stderr)
        return False
    return True


def write_1byte(
    packet_handler: PacketHandler,
    port_handler: PortHandler,
    dxl_id: int,
    address: int,
    value: int,
    action: str,
) -> bool:
    result, error = packet_handler.write1ByteTxRx(port_handler, dxl_id, address, value)
    return check_result(packet_handler, result, error, f"ID {dxl_id} {action}")


def write_velocity(
    packet_handler: PacketHandler,
    port_handler: PortHandler,
    dxl_id: int,
    velocity: int,
) -> bool:
    result, error = packet_handler.write4ByteTxRx(
        port_handler,
        dxl_id,
        ADDR_GOAL_VELOCITY,
        velocity & 0xFFFFFFFF,
    )
    return check_result(packet_handler, result, error, f"ID {dxl_id} set velocity")


def set_all_velocities(
    packet_handler: PacketHandler,
    port_handler: PortHandler,
    velocities: dict[int, int],
) -> bool:
    for dxl_id, velocity in velocities.items():
        if not write_velocity(packet_handler, port_handler, dxl_id, velocity):
            return False
    return True


def read_key(timeout: float) -> str | None:
    readable, _, _ = select.select([sys.stdin], [], [], timeout)
    if not readable:
        return None

    first = sys.stdin.read(1)
    if first != "\x1b":
        return first

    readable, _, _ = select.select([sys.stdin], [], [], 0.05)
    if not readable:
        return first

    second = sys.stdin.read(1)
    readable, _, _ = select.select([sys.stdin], [], [], 0.05)
    third = sys.stdin.read(1) if readable else ""
    return first + second + third


def command_for_key(key: str) -> str | None:
    normalized = key.lower()
    if key in (KEY_UP, ALT_KEY_UP) or normalized == "w":
        return "forward"
    if key in (KEY_DOWN, ALT_KEY_DOWN) or normalized == "s":
        return "backward"
    if key in (KEY_LEFT, ALT_KEY_LEFT) or normalized == "a":
        return "left"
    if key in (KEY_RIGHT, ALT_KEY_RIGHT) or normalized == "d":
        return "right"
    if key == " ":
        return "stop"
    return None


def motor_velocity_for_key(args: argparse.Namespace, key: str) -> dict[int, int] | None:
    normalized = key.lower()
    pairs = [pair.strip().lower() for pair in args.key_pairs.split(",") if pair.strip()]
    if len(pairs) != len(args.ids):
        raise ValueError("--key-pairs count must match --ids count")

    velocities = {dxl_id: 0 for dxl_id in args.ids}
    for dxl_id, pair in zip(args.ids, pairs, strict=True):
        if len(pair) != 2:
            raise ValueError("each --key-pairs item must have exactly two characters")
        forward_key, backward_key = pair
        if normalized == forward_key:
            velocities[dxl_id] = args.speed
            return velocities
        if normalized == backward_key:
            velocities[dxl_id] = -args.speed
            return velocities
    return None


def velocities_for_command(args: argparse.Namespace, command: str) -> dict[int, int]:
    stop = {dxl_id: 0 for dxl_id in args.ids}
    forward = {dxl_id: args.speed for dxl_id in args.ids}
    backward = {dxl_id: -args.speed for dxl_id in args.ids}

    left = stop.copy()
    for dxl_id in args.left_ids:
        left[dxl_id] = -args.speed
    for dxl_id in args.right_ids:
        left[dxl_id] = args.speed

    right = stop.copy()
    for dxl_id in args.left_ids:
        right[dxl_id] = args.speed
    for dxl_id in args.right_ids:
        right[dxl_id] = -args.speed

    if command == "forward":
        return forward
    if command == "backward":
        return backward
    if command == "left":
        return left
    if command == "right":
        return right
    return stop


def configure_motor(packet_handler: PacketHandler, port_handler: PortHandler, dxl_id: int) -> bool:
    if not write_1byte(
        packet_handler,
        port_handler,
        dxl_id,
        ADDR_TORQUE_ENABLE,
        TORQUE_DISABLE,
        "disable torque",
    ):
        return False
    if not write_1byte(
        packet_handler,
        port_handler,
        dxl_id,
        ADDR_OPERATING_MODE,
        MODE_VELOCITY_CONTROL,
        "set velocity mode",
    ):
        return False
    return write_1byte(
        packet_handler,
        port_handler,
        dxl_id,
        ADDR_TORQUE_ENABLE,
        TORQUE_ENABLE,
        "enable torque",
    )


def main() -> int:
    args = parse_args()
    port_handler = PortHandler(args.port)
    packet_handler = PacketHandler(args.protocol)
    stop_velocities = {dxl_id: 0 for dxl_id in args.ids}
    old_terminal_settings = None

    if not sys.stdin.isatty():
        print("Run this script from a real terminal so key input can be read.", file=sys.stderr)
        print("Example: source .venv/bin/activate && python3 dxl_arrow_test.py", file=sys.stderr)
        return 1

    if args.debug_keys:
        old_terminal_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        print("Key debug mode. Press keys to see received codes. Press x to quit.")
        try:
            while True:
                key = read_key(1.0)
                if key is None:
                    continue
                print(f"received: {key!r}")
                if key in ("x", "X", "\x03"):
                    return 0
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)

    if not port_handler.openPort():
        print(f"Failed to open port: {args.port}", file=sys.stderr)
        return 1

    try:
        if not port_handler.setBaudRate(args.baudrate):
            print(f"Failed to set baudrate: {args.baudrate}", file=sys.stderr)
            return 1

        for dxl_id in args.ids:
            if not configure_motor(packet_handler, port_handler, dxl_id):
                return 1

        try:
            pairs = [pair.strip().lower() for pair in args.key_pairs.split(",") if pair.strip()]
            if len(pairs) != len(args.ids):
                raise ValueError("--key-pairs count must match --ids count")
            for pair in pairs:
                if len(pair) != 2:
                    raise ValueError("each --key-pairs item must have exactly two characters")
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1

        print("Keyboard motor test")
        for dxl_id, pair in zip(args.ids, pairs, strict=True):
            print(f"  ID {dxl_id}: {pair[0].upper()} forward / {pair[1].upper()} backward")
        print("  Up/Down: all motors forward/backward")
        print("  Left/Right: left IDs reverse, right IDs forward, and vice versa")
        print("  Space: stop")
        print("  x or Ctrl-C: quit")
        print("  Release the key to stop. This uses terminal key-repeat timing.")
        print(
            f"IDs: {args.ids}, left: {args.left_ids}, right: {args.right_ids}, "
            f"speed: {args.speed}, stop timeout: {args.timeout}s"
        )

        old_terminal_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        last_command_at = 0.0
        last_velocities = stop_velocities

        while True:
            key = read_key(0.05)
            now = time.monotonic()

            if key in ("x", "X", "\x03"):
                break

            motor_velocities = motor_velocity_for_key(args, key) if key else None
            command = command_for_key(key) if key and motor_velocities is None else None
            if motor_velocities is not None:
                if motor_velocities != last_velocities:
                    if not set_all_velocities(packet_handler, port_handler, motor_velocities):
                        return 1
                    last_velocities = motor_velocities
                    print(f"\rKey: {key.upper():<2}       ", end="", flush=True)
                last_command_at = now
            elif command is not None:
                velocities = velocities_for_command(args, command)
                if velocities != last_velocities:
                    if not set_all_velocities(packet_handler, port_handler, velocities):
                        return 1
                    last_velocities = velocities
                    print(f"\rCommand: {command:<8}", end="", flush=True)
                last_command_at = now
            elif (
                not args.hold
                and last_velocities != stop_velocities
                and now - last_command_at > args.timeout
            ):
                if not set_all_velocities(packet_handler, port_handler, stop_velocities):
                    return 1
                last_velocities = stop_velocities
                print("\rCommand: stop    ", end="", flush=True)

        print()
        return 0
    finally:
        if old_terminal_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_terminal_settings)
        set_all_velocities(packet_handler, port_handler, stop_velocities)
        if not args.keep_torque:
            for motor_id in args.ids:
                write_1byte(
                    packet_handler,
                    port_handler,
                    motor_id,
                    ADDR_TORQUE_ENABLE,
                    TORQUE_DISABLE,
                    "disable torque",
                )
        port_handler.closePort()


if __name__ == "__main__":
    raise SystemExit(main())
