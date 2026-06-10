"""FastAPI routes for FlowLamp."""

from __future__ import annotations

import asyncio
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from study_records import StudyRecordRepository, StudyRecordsError
except ImportError:
    from .study_records import StudyRecordRepository, StudyRecordsError


VALUE_LOG_PREFIX = "[FlowLamp API]"


class BrightnessInput(BaseModel):
    value: int = Field(..., ge=0, le=100)


class ColorInput(BaseModel):
    r: int = Field(..., ge=0, le=255)
    g: int = Field(..., ge=0, le=255)
    b: int = Field(..., ge=0, le=255)


class NightScheduleInput(BaseModel):
    is_on: bool
    start_time: str
    end_time: str


class PersonInput(BaseModel):
    detected: bool


class GestureInput(BaseModel):
    gesture: str


class PostureInput(BaseModel):
    turtle_neck: bool


class MotorVelocityInput(BaseModel):
    velocity: int = Field(..., ge=-100, le=100)


class MotorVectorInput(BaseModel):
    x: float = Field(..., ge=-1.0, le=1.0)
    y: float = Field(..., ge=-1.0, le=1.0)
    speed: int = Field(20, ge=0, le=100)


@dataclass
class ApiState:
    led: Any
    runtime: Any
    night_schedule: dict[str, Any]
    motor: Any | None = None
    night_schedule_lock: Any | None = None
    is_night_active: Any | None = None
    person_state: dict[str, Any] | None = None
    person_state_lock: Any | None = None
    person_absence_delay_seconds: float = 7.0
    study_records: StudyRecordRepository | None = None


async def _run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


def _require_motor(state: ApiState):
    if state.motor is None:
        raise HTTPException(
            status_code=503,
            detail="Motor controller is not configured.",
        )
    return state.motor


def _raise_if_motor_failed(result):
    failed = [
        motor
        for motor in result.values()
        if isinstance(motor, dict) and motor.get("disabled")
    ]
    if not failed:
        return

    details = ", ".join(
        f"id={motor.get('id')}: {motor.get('error') or 'disabled'}"
        for motor in failed
    )
    raise HTTPException(status_code=503, detail=f"Motor command failed: {details}")


def _current_mode_name(runtime) -> str | None:
    return runtime.current_mode.name if runtime.current_mode else None


def _color_dict(color) -> dict[str, int]:
    r, g, b = color
    return {"r": int(r), "g": int(g), "b": int(b)}


def _color_log_value(color) -> str:
    rgb = _color_dict(color)
    return f"{rgb['r']},{rgb['g']},{rgb['b']}"


def _log_value_event(message: str):
    print(f"{VALUE_LOG_PREFIX} {message}", flush=True)


def _parse_schedule_time(value: str):
    if re.fullmatch(r"\d{2}:\d{2}", value) is None:
        raise HTTPException(
            status_code=400,
            detail="Time must use HH:MM format.",
        )

    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Time must use HH:MM format.",
        ) from exc


def _night_schedule_response(state: ApiState) -> dict[str, Any]:
    if state.night_schedule_lock is None:
        schedule = state.night_schedule.copy()
    else:
        with state.night_schedule_lock:
            schedule = state.night_schedule.copy()

    currently_active = (
        bool(state.is_night_active()) if state.is_night_active is not None else False
    )
    return {
        "is_on": bool(schedule["is_on"]),
        "start_time": schedule["start_time"],
        "end_time": schedule["end_time"],
        "currently_active": currently_active,
    }


def _person_detected(state: ApiState) -> bool:
    if state.person_state is None:
        return False

    if state.person_state_lock is None:
        return bool(state.person_state.get("detected", False))

    with state.person_state_lock:
        return bool(state.person_state.get("detected", False))


def _cancel_person_timer(state: ApiState):
    if state.person_state is None:
        return

    timer = state.person_state.get("absence_timer")
    if timer is not None:
        timer.cancel()
        state.person_state["absence_timer"] = None


def _standby_if_person_still_absent(state: ApiState, version: int):
    if state.person_state is None:
        return

    if state.person_state_lock is None:
        still_absent = (
            not state.person_state.get("detected", False)
            and state.person_state.get("version") == version
        )
        state.person_state["absence_timer"] = None
    else:
        with state.person_state_lock:
            still_absent = (
                not state.person_state.get("detected", False)
                and state.person_state.get("version") == version
            )
            if still_absent:
                state.person_state["absence_timer"] = None

    if still_absent:
        try:
            state.runtime.set_mode_threadsafe("standby")
        except RuntimeError as exc:
            print(f"Delayed standby failed: {exc}")


def _schedule_delayed_standby(state: ApiState) -> float:
    if state.person_state is None:
        return state.person_absence_delay_seconds

    if state.person_state_lock is None:
        _cancel_person_timer(state)
        version = int(state.person_state.get("version", 0)) + 1
        state.person_state["detected"] = False
        state.person_state["version"] = version
        state.person_state["last_update"] = time.monotonic()
        timer = threading.Timer(
            state.person_absence_delay_seconds,
            _standby_if_person_still_absent,
            args=(state, version),
        )
        timer.daemon = True
        state.person_state["absence_timer"] = timer
        timer.start()
        return state.person_absence_delay_seconds

    with state.person_state_lock:
        _cancel_person_timer(state)
        version = int(state.person_state.get("version", 0)) + 1
        state.person_state["detected"] = False
        state.person_state["version"] = version
        state.person_state["last_update"] = time.monotonic()
        timer = threading.Timer(
            state.person_absence_delay_seconds,
            _standby_if_person_still_absent,
            args=(state, version),
        )
        timer.daemon = True
        state.person_state["absence_timer"] = timer
        timer.start()

    return state.person_absence_delay_seconds


def _mark_person_detected(state: ApiState):
    if state.person_state is None:
        return

    if state.person_state_lock is None:
        _cancel_person_timer(state)
        state.person_state["detected"] = True
        state.person_state["version"] = int(state.person_state.get("version", 0)) + 1
        state.person_state["last_update"] = time.monotonic()
        return

    with state.person_state_lock:
        _cancel_person_timer(state)
        state.person_state["detected"] = True
        state.person_state["version"] = int(state.person_state.get("version", 0)) + 1
        state.person_state["last_update"] = time.monotonic()


def create_app(state: ApiState) -> FastAPI:
    app = FastAPI()
    _log_value_event("value logging enabled")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/status")
    async def get_status():
        return {
            "mode": _current_mode_name(state.runtime),
            "power": state.led.is_on,
            "night_mode": state.led.is_night_mode,
            "brightness": state.led.brightness_percent,
            "color": _color_dict(state.led.current_color),
            "person_detected": _person_detected(state),
        }

    @app.get("/study-records")
    async def get_study_records(
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        if start_date is not None and end_date is not None and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date must be on or before end_date.",
            )
        if state.study_records is None:
            raise HTTPException(
                status_code=503,
                detail="Study records DB is not configured.",
            )

        try:
            records = await _run_blocking(
                state.study_records.get_records,
                start_date,
                end_date,
            )
        except StudyRecordsError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        return {
            "start_date": start_date,
            "end_date": end_date,
            "count": len(records),
            "records": records,
        }

    @app.post("/mode/{mode_name}")
    async def set_mode(mode_name: str):
        if mode_name not in ("standby", "normal"):
            raise HTTPException(
                status_code=400,
                detail="mode_name must be standby or normal.",
            )

        try:
            await _run_blocking(state.runtime.set_mode_threadsafe, mode_name)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"mode": _current_mode_name(state.runtime)}

    @app.post("/power")
    async def toggle_power(status: str):
        if status not in ("on", "off"):
            raise HTTPException(
                status_code=400,
                detail="status must be on or off.",
            )

        mode_name = "normal" if status == "on" else "standby"
        await _run_blocking(state.runtime.set_mode_threadsafe, mode_name)
        return {
            "status": "success",
            "mode": _current_mode_name(state.runtime),
            "power": state.led.is_on,
        }

    @app.post("/color")
    async def set_color(color: ColorInput):
        before_color = _color_log_value(state.led.current_color)
        state.led.set_color(color.r, color.g, color.b)
        after_color = _color_log_value(state.led.current_color)
        _log_value_event(
            "color "
            f"requested={color.r},{color.g},{color.b} "
            f"before={before_color} "
            f"applied={after_color} "
            f"brightness={state.led.brightness_percent}% "
            f"power={state.led.is_on}"
        )
        return {
            "status": "success",
            "color": _color_dict(state.led.current_color),
            "power": state.led.is_on,
        }

    @app.post("/brightness")
    async def set_brightness(brightness: BrightnessInput):
        before_percent = state.led.brightness_percent
        state.led.set_brightness(brightness.value)
        after_percent = state.led.brightness_percent
        _log_value_event(
            "brightness "
            f"requested={brightness.value}% "
            f"before={before_percent}% "
            f"applied={after_percent}% "
            f"raw={state.led.brightness}/255"
        )
        return {
            "status": "success",
            "brightness": after_percent,
        }

    @app.post("/timer/done")
    async def notify_timer_done():
        state.led.blink_alert()
        return {
            "status": "success",
            "action": "timer_alert",
        }

    @app.post("/motors/{motor_id}/velocity")
    async def set_motor_velocity(motor_id: int, command: MotorVelocityInput):
        motor = _require_motor(state)

        try:
            result = await _run_blocking(
                motor.set_goal_velocities,
                {motor_id: command.velocity},
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        _raise_if_motor_failed(result)
        return {
            "status": "success",
            "motor": result.get(motor_id),
        }

    @app.post("/motors/xy")
    async def set_motor_xy(command: MotorVectorInput):
        motor = _require_motor(state)

        try:
            result = await _run_blocking(
                motor.move_xy,
                command.x,
                command.y,
                command.speed,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        _raise_if_motor_failed(result)
        return {
            "status": "success",
            "motors": result,
        }

    @app.post("/motors/stop")
    async def stop_motors():
        motor = _require_motor(state)

        try:
            result = await _run_blocking(motor.stop)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        _raise_if_motor_failed(result)
        return {
            "status": "success",
            "motors": result,
        }

    @app.post("/night_mode/schedule")
    async def set_night_schedule(schedule_input: NightScheduleInput):
        _parse_schedule_time(schedule_input.start_time)
        _parse_schedule_time(schedule_input.end_time)

        if state.night_schedule_lock is None:
            state.night_schedule["is_on"] = schedule_input.is_on
            state.night_schedule["start_time"] = schedule_input.start_time
            state.night_schedule["end_time"] = schedule_input.end_time
        else:
            with state.night_schedule_lock:
                state.night_schedule["is_on"] = schedule_input.is_on
                state.night_schedule["start_time"] = schedule_input.start_time
                state.night_schedule["end_time"] = schedule_input.end_time

        currently_active = (
            bool(state.is_night_active()) if state.is_night_active is not None else False
        )

        if schedule_input.is_on and currently_active and not state.led.is_night_mode:
            state.led.set_night_mode(True)
            print("Night mode enabled immediately")
        elif (not schedule_input.is_on or not currently_active) and state.led.is_night_mode:
            state.led.set_night_mode(False)
            print("Night mode disabled immediately")

        return _night_schedule_response(state)

    @app.get("/night_mode/schedule")
    async def get_night_schedule():
        return _night_schedule_response(state)

    @app.post("/vision/person")
    async def update_person_detection(person: PersonInput):
        if person.detected:
            _mark_person_detected(state)
            await _run_blocking(state.runtime.set_mode_threadsafe, "normal")
            return {
                "person_detected": True,
                "mode": _current_mode_name(state.runtime),
            }

        delay_seconds = _schedule_delayed_standby(state)
        return {
            "person_detected": False,
            "standby_delay_seconds": delay_seconds,
            "mode": _current_mode_name(state.runtime),
        }

    @app.post("/vision/posture")
    async def update_posture(posture: PostureInput):
        if posture.turtle_neck:
            state.led.start_posture_alert()
            action = "posture_alert_started"
        else:
            state.led.stop_posture_alert()
            action = "posture_alert_stopped"

        return {
            "status": "success",
            "turtle_neck": posture.turtle_neck,
            "action": action,
        }

    @app.post("/vision/gesture")
    async def handle_gesture(gesture_input: GestureInput):
        gesture = gesture_input.gesture
        brightness_step = 10

        if gesture == "brightness_up":
            before_percent = state.led.brightness_percent
            next_value = min(100, state.led.brightness_percent + brightness_step)
            state.led.set_brightness(next_value)
            after_percent = state.led.brightness_percent
            _log_value_event(
                "gesture-brightness "
                f"gesture={gesture} "
                f"requested={next_value}% "
                f"before={before_percent}% "
                f"applied={after_percent}% "
                f"raw={state.led.brightness}/255"
            )
            return {
                "gesture": gesture,
                "action": "brightness_changed",
                "brightness": after_percent,
            }

        if gesture == "brightness_down":
            before_percent = state.led.brightness_percent
            next_value = max(0, state.led.brightness_percent - brightness_step)
            state.led.set_brightness(next_value)
            after_percent = state.led.brightness_percent
            _log_value_event(
                "gesture-brightness "
                f"gesture={gesture} "
                f"requested={next_value}% "
                f"before={before_percent}% "
                f"applied={after_percent}% "
                f"raw={state.led.brightness}/255"
            )
            return {
                "gesture": gesture,
                "action": "brightness_changed",
                "brightness": after_percent,
            }

        raise HTTPException(status_code=400, detail=f"Unknown gesture: {gesture}")

    return app
