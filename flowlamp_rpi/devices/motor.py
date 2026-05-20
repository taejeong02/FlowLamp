"""Dynamixel motor device control."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

    HAS_DYNAMIXEL_SDK = True
except ImportError:
    COMM_SUCCESS = 0
    PacketHandler = None
    PortHandler = None
    HAS_DYNAMIXEL_SDK = False
    print("Dynamixel SDK가 감지되지 않아 모터 시뮬레이션 모드로 동작합니다.")


@dataclass(frozen=True)
class DynamixelConfig:
    """Protocol 2.0 계열 Dynamixel 기본 설정입니다."""

    port: str = field(default_factory=lambda: os.getenv("FLOWLAMP_DXL_PORT", "/dev/ttyUSB0"))
    baudrate: int = field(default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_BAUDRATE", "57600")))
    protocol_version: float = 2.0
    motor_ids: tuple[int, ...] = (1, 2, 3, 4)
    min_position: int = 0
    max_position: int = 4095
    default_velocity: int = 80


class MotorController:
    """앱이나 제스처 입력에서 호출할 수 있는 1~4번 모터 제어기입니다."""

    ADDR_TORQUE_ENABLE = 64
    ADDR_PROFILE_VELOCITY = 112
    ADDR_GOAL_POSITION = 116
    ADDR_PRESENT_POSITION = 132

    TORQUE_OFF = 0
    TORQUE_ON = 1

    def __init__(self, config: DynamixelConfig | None = None, simulate_on_error: bool = True):
        self.config = config or DynamixelConfig()
        self.simulate_on_error = simulate_on_error
        self.connected = False
        self.simulation = not HAS_DYNAMIXEL_SDK
        self._positions = {motor_id: 2048 for motor_id in self.config.motor_ids}
        self._velocities = {
            motor_id: self.config.default_velocity for motor_id in self.config.motor_ids
        }
        self._torque_enabled = {motor_id: False for motor_id in self.config.motor_ids}
        self._port_handler = None
        self._packet_handler = None

    def connect(self):
        """포트를 열고 토크를 켭니다. 실패 시 설정에 따라 시뮬레이션으로 전환합니다."""
        if self.connected or self.simulation:
            return self.status()

        self._port_handler = PortHandler(self.config.port)
        self._packet_handler = PacketHandler(self.config.protocol_version)

        try:
            port_opened = self._port_handler.openPort()
        except Exception as exc:
            return self._handle_connection_error(f"모터 포트를 열 수 없습니다: {exc}")

        if not port_opened:
            return self._handle_connection_error(f"모터 포트를 열 수 없습니다: {self.config.port}")

        try:
            baudrate_set = self._port_handler.setBaudRate(self.config.baudrate)
        except Exception as exc:
            self._port_handler.closePort()
            return self._handle_connection_error(f"모터 baudrate 설정 실패: {exc}")

        if not baudrate_set:
            self._port_handler.closePort()
            return self._handle_connection_error(f"모터 baudrate 설정 실패: {self.config.baudrate}")

        self.connected = True
        try:
            for motor_id in self.config.motor_ids:
                self.set_profile_velocity(motor_id, self.config.default_velocity)
                self.enable_torque(motor_id)
        except RuntimeError as exc:
            self._port_handler.closePort()
            self.connected = False
            return self._handle_connection_error(str(exc))

        print(f"Dynamixel 연결 완료: {self.config.port} @ {self.config.baudrate}")
        return self.status()

    def close(self):
        """모터 토크를 끄고 포트를 닫습니다."""
        if not self.connected and not self.simulation:
            return

        for motor_id in self.config.motor_ids:
            try:
                self.disable_torque(motor_id)
            except RuntimeError as exc:
                print(f"모터 토크 해제 실패: {exc}")

        if self._port_handler and self.connected:
            self._port_handler.closePort()

        self.connected = False
        print("Dynamixel 연결 종료")

    def enable_torque(self, motor_id: int):
        self._validate_motor_id(motor_id)
        self._write_1_byte(motor_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_ON)
        self._torque_enabled[motor_id] = True

    def disable_torque(self, motor_id: int):
        self._validate_motor_id(motor_id)
        self._write_1_byte(motor_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_OFF)
        self._torque_enabled[motor_id] = False

    def set_profile_velocity(self, motor_id: int, velocity: int):
        self._validate_motor_id(motor_id)
        velocity = max(0, int(velocity))
        self._write_4_bytes(motor_id, self.ADDR_PROFILE_VELOCITY, velocity)
        self._velocities[motor_id] = velocity

    def move_motor(self, motor_id: int, position: int, velocity: int | None = None):
        """모터 하나를 목표 위치로 이동합니다."""
        self.connect()
        self._validate_motor_id(motor_id)
        position = self._clamp_position(position)

        if velocity is not None:
            self.set_profile_velocity(motor_id, velocity)

        if not self._torque_enabled[motor_id]:
            self.enable_torque(motor_id)

        self._write_4_bytes(motor_id, self.ADDR_GOAL_POSITION, position)
        self._positions[motor_id] = position
        return self.motor_status(motor_id)

    def move_all(self, positions: dict[int, int], velocity: int | None = None):
        """여러 모터를 한 번에 이동합니다. 예: {1: 2048, 2: 1800}"""
        result = {}
        for motor_id, position in positions.items():
            result[motor_id] = self.move_motor(motor_id, position, velocity)
        return result

    def apply_pose(self, pose: str, velocity: int | None = None):
        """자주 쓰는 자세 프리셋을 적용합니다."""
        poses = {
            "home": {1: 2048, 2: 2048, 3: 2048, 4: 2048},
            "up": {1: 2048, 2: 1700, 3: 1700, 4: 2048},
            "down": {1: 2048, 2: 2400, 3: 2400, 4: 2048},
            "left": {1: 1700, 2: 2048, 3: 2048, 4: 1700},
            "right": {1: 2400, 2: 2048, 3: 2048, 4: 2400},
        }

        if pose not in poses:
            raise ValueError(f"Unknown motor pose: {pose}")

        return self.move_all(poses[pose], velocity)

    def read_position(self, motor_id: int):
        self.connect()
        self._validate_motor_id(motor_id)

        if self.simulation:
            return self._positions[motor_id]

        position, comm_result, error = self._packet_handler.read4ByteTxRx(
            self._port_handler,
            motor_id,
            self.ADDR_PRESENT_POSITION,
        )
        self._check_result(motor_id, comm_result, error)
        self._positions[motor_id] = position
        return position

    def motor_status(self, motor_id: int):
        self._validate_motor_id(motor_id)
        return {
            "id": motor_id,
            "position": self._positions[motor_id],
            "velocity": self._velocities[motor_id],
            "torque_enabled": self._torque_enabled[motor_id],
        }

    def status(self):
        return {
            "connected": self.connected,
            "simulation": self.simulation,
            "port": self.config.port,
            "baudrate": self.config.baudrate,
            "motors": [self.motor_status(motor_id) for motor_id in self.config.motor_ids],
        }

    def _write_1_byte(self, motor_id: int, address: int, value: int):
        if self.simulation:
            print(f"[MOTOR SIM] id={motor_id} addr={address} value={value}")
            return

        comm_result, error = self._packet_handler.write1ByteTxRx(
            self._port_handler,
            motor_id,
            address,
            int(value),
        )
        self._check_result(motor_id, comm_result, error)

    def _write_4_bytes(self, motor_id: int, address: int, value: int):
        if self.simulation:
            print(f"[MOTOR SIM] id={motor_id} addr={address} value={value}")
            return

        comm_result, error = self._packet_handler.write4ByteTxRx(
            self._port_handler,
            motor_id,
            address,
            int(value),
        )
        self._check_result(motor_id, comm_result, error)

    def _check_result(self, motor_id: int, comm_result: int, error: int):
        if comm_result != COMM_SUCCESS:
            message = self._packet_handler.getTxRxResult(comm_result)
            raise RuntimeError(f"Dynamixel 통신 실패(id={motor_id}): {message}")

        if error:
            message = self._packet_handler.getRxPacketError(error)
            raise RuntimeError(f"Dynamixel 패킷 에러(id={motor_id}): {message}")

    def _handle_connection_error(self, message: str):
        if not self.simulate_on_error:
            raise RuntimeError(message)

        print(f"{message} 시뮬레이션 모드로 전환합니다.")
        self.connected = False
        self.simulation = True
        return self.status()

    def _validate_motor_id(self, motor_id: int):
        if motor_id not in self.config.motor_ids:
            raise ValueError(f"Unknown motor id: {motor_id}")

    def _clamp_position(self, position: int):
        return max(self.config.min_position, min(self.config.max_position, int(position)))
