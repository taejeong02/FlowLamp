"""Dynamixel velocity control for hand tracking."""
from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field

try:
    from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler

    HAS_DYNAMIXEL_SDK = True
except ImportError:
    COMM_SUCCESS = 0
    PacketHandler = None
    PortHandler = None
    HAS_DYNAMIXEL_SDK = False
    print("Dynamixel SDK가 없어 모터 시뮬레이션 모드로 동작합니다.")


@dataclass(frozen=True)
class DynamixelConfig:
    port: str = field(
        default_factory=lambda: os.getenv(
            "FLOWLAMP_DXL_PORT",
            "/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTBEQDJL-if00-port0",
        )
    )
    baudrate: int = field(
        default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_BAUDRATE", "57600"))
    )
    protocol_version: float = 2.0
    motor_ids: tuple[int, ...] = (1, 2, 3, 4)
    min_position: int = field(
        default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_MIN_POSITION", "0"))
    )
    max_position: int = field(
        default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_MAX_POSITION", "4095"))
    )
    soft_limit_margin: int = field(
        default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_SOFT_LIMIT_MARGIN", "160"))
    )
    max_velocity: int = field(
        default_factory=lambda: int(os.getenv("FLOWLAMP_DXL_MAX_VELOCITY", "5"))
    )


class MotorController:
    ADDR_OPERATING_MODE = 11
    ADDR_TORQUE_ENABLE = 64
    ADDR_HARDWARE_ERROR_STATUS = 70
    ADDR_GOAL_VELOCITY = 104
    ADDR_PRESENT_POSITION = 132

    MODE_VELOCITY_CONTROL = 1
    TORQUE_OFF = 0
    TORQUE_ON = 1

    def __init__(
        self,
        config: DynamixelConfig | None = None,
        simulate_on_error: bool = True,
    ):
        self.config = config or DynamixelConfig()
        self.simulate_on_error = simulate_on_error
        self.connected = False
        self.simulation = not HAS_DYNAMIXEL_SDK
        self._goal_velocities = {motor_id: 0 for motor_id in self.config.motor_ids}
        self._positions = {motor_id: 2048 for motor_id in self.config.motor_ids}
        self._disabled_motors: dict[int, str] = {}
        self._port_handler = None
        self._packet_handler = None
        self._lock = threading.RLock()

    def connect(self):
        """Connect in velocity mode with zero velocity; no startup movement."""
        if self.connected or self.simulation:
            return self.status()

        with self._lock:
            if self.connected:
                return self.status()

            self._port_handler = PortHandler(self.config.port)
            self._packet_handler = PacketHandler(self.config.protocol_version)
            try:
                port_opened = self._port_handler.openPort()
            except Exception as exc:
                return self._handle_connection_error(f"모터 포트 열기 실패: {exc}")
            if not port_opened:
                return self._handle_connection_error(
                    f"모터 포트를 열 수 없습니다: {self.config.port}"
                )

            try:
                baudrate_set = self._port_handler.setBaudRate(self.config.baudrate)
            except Exception as exc:
                self._port_handler.closePort()
                return self._handle_connection_error(f"모터 baudrate 설정 실패: {exc}")
            if not baudrate_set:
                self._port_handler.closePort()
                return self._handle_connection_error(
                    f"모터 baudrate 설정 실패: {self.config.baudrate}"
                )

            self.connected = True
            for motor_id in self.config.motor_ids:
                try:
                    self._write_1_byte(motor_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_OFF)
                    self._write_1_byte(
                        motor_id,
                        self.ADDR_OPERATING_MODE,
                        self.MODE_VELOCITY_CONTROL,
                    )
                    self._write_4_bytes(motor_id, self.ADDR_GOAL_VELOCITY, 0)
                    self._write_1_byte(motor_id, self.ADDR_TORQUE_ENABLE, self.TORQUE_ON)
                except RuntimeError as exc:
                    self._disable_motor(motor_id, str(exc))

            print(f"Dynamixel 연결 완료: {self.config.port} @ {self.config.baudrate}")
            return self.status()

    def move_xyz(self, x: float, y: float, z: float, speed: int = 2):
        """Map normalized hand axes to four motor velocities."""
        speed = max(0, min(int(speed), self.config.max_velocity))
        x = self._normalize_axis(x)
        y = self._normalize_axis(y)
        z = self._normalize_axis(z)
        velocities = {
            1: self._axis_to_velocity(x, speed),
            2: self._axis_to_velocity(z + y, speed),
            3: self._axis_to_velocity(-z, speed),
            4: self._axis_to_velocity(y - z, speed),
        }
        return self.set_goal_velocities(velocities)

    def set_goal_velocities(self, velocities: dict[int, int]):
        with self._lock:
            self.connect()
            result = {}
            for motor_id, velocity in velocities.items():
                result[motor_id] = self._set_goal_velocity(motor_id, velocity)
            return result

    def stop(self):
        return self.set_goal_velocities(
            {motor_id: 0 for motor_id in self.config.motor_ids}
        )

    def close(self):
        with self._lock:
            if self.connected:
                for motor_id in self.config.motor_ids:
                    if motor_id in self._disabled_motors:
                        continue
                    try:
                        self._write_4_bytes(motor_id, self.ADDR_GOAL_VELOCITY, 0)
                        self._write_1_byte(
                            motor_id,
                            self.ADDR_TORQUE_ENABLE,
                            self.TORQUE_OFF,
                        )
                    except RuntimeError:
                        pass
                self._port_handler.closePort()
            self.connected = False

    def status(self):
        return {
            "connected": self.connected,
            "simulation": self.simulation,
            "disabled_motors": dict(self._disabled_motors),
            "motors": [
                {
                    "id": motor_id,
                    "position": self._positions[motor_id],
                    "goal_velocity": self._goal_velocities[motor_id],
                    "disabled": motor_id in self._disabled_motors,
                }
                for motor_id in self.config.motor_ids
            ],
        }

    def _set_goal_velocity(self, motor_id: int, velocity: int):
        if motor_id not in self.config.motor_ids:
            raise ValueError(f"Unknown motor id: {motor_id}")
        if motor_id in self._disabled_motors:
            return self._motor_result(motor_id)

        velocity = max(
            -self.config.max_velocity,
            min(self.config.max_velocity, int(velocity)),
        )
        try:
            velocity = self._limit_velocity_by_position(motor_id, velocity)
            self._write_4_bytes(
                motor_id,
                self.ADDR_GOAL_VELOCITY,
                velocity & 0xFFFFFFFF,
            )
            self._goal_velocities[motor_id] = velocity
        except RuntimeError as exc:
            self._disable_motor(motor_id, str(exc))
        return self._motor_result(motor_id)

    def _limit_velocity_by_position(self, motor_id: int, velocity: int):
        if velocity == 0:
            return 0

        position = self._read_position(motor_id)
        margin = max(0, self.config.soft_limit_margin)
        if velocity < 0 and position <= self.config.min_position + margin:
            return 0
        if velocity > 0 and position >= self.config.max_position - margin:
            return 0
        return velocity

    def _read_position(self, motor_id: int):
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

    def _disable_motor(self, motor_id: int, reason: str):
        self._disabled_motors[motor_id] = reason
        self._goal_velocities[motor_id] = 0
        print(f"모터 {motor_id} 비활성화: {reason}")

    def _handle_connection_error(self, message: str):
        if not self.simulate_on_error:
            raise RuntimeError(message)
        print(f"{message}; 시뮬레이션 모드로 전환합니다.")
        self.connected = False
        self.simulation = True
        return self.status()

    def _motor_result(self, motor_id: int):
        return {
            "id": motor_id,
            "position": self._positions[motor_id],
            "goal_velocity": self._goal_velocities[motor_id],
            "disabled": motor_id in self._disabled_motors,
            "error": self._disabled_motors.get(motor_id),
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
            raise RuntimeError(f"통신 실패: {message}")
        if error:
            message = self._packet_handler.getRxPacketError(error)
            hardware_status = self._read_hardware_error_status(motor_id)
            details = self._decode_hardware_error_status(hardware_status)
            suffix = f" ({', '.join(details)})" if details else ""
            raise RuntimeError(
                f"패킷 에러: {message}; status=0x{hardware_status:02X}{suffix}"
            )

    def _read_hardware_error_status(self, motor_id: int):
        status, comm_result, _ = self._packet_handler.read1ByteTxRx(
            self._port_handler,
            motor_id,
            self.ADDR_HARDWARE_ERROR_STATUS,
        )
        return status if comm_result == COMM_SUCCESS else 0

    @staticmethod
    def _decode_hardware_error_status(status: int):
        bits = (
            (0, "input voltage"),
            (2, "overheating"),
            (3, "motor encoder"),
            (4, "electrical shock"),
            (5, "overload"),
        )
        return [name for bit, name in bits if status & (1 << bit)]

    @staticmethod
    def _normalize_axis(value: float):
        value = max(-1.0, min(1.0, float(value)))
        return 0.0 if abs(value) < 0.05 else value

    @staticmethod
    def _axis_to_velocity(value: float, speed: int):
        if value == 0.0 or speed <= 0:
            return 0

        velocity = round(value * speed)
        if velocity == 0:
            return 1 if value > 0 else -1
        return velocity
