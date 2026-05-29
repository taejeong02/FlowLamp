"""FastAPI routes for FlowLamp."""

from __future__ import annotations

import asyncio
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


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


class MotorVectorInput(BaseModel):
    x: float = Field(0.0, ge=-1.0, le=1.0)
    y: float = Field(0.0, ge=-1.0, le=1.0)
    z: float = Field(0.0, ge=-1.0, le=1.0)
    speed: int | None = Field(None, ge=0, le=200)


@dataclass
class ApiState:
    led: Any
    motor: Any
    runtime: Any
    night_schedule: dict[str, Any]
    night_schedule_lock: Any | None = None
    is_night_active: Any | None = None
    person_state: dict[str, Any] | None = None
    person_state_lock: Any | None = None
    person_absence_delay_seconds: float = 7.0


async def _run_blocking(func, *args):
    return await asyncio.to_thread(func, *args)


def _current_mode_name(runtime) -> str | None:
    return runtime.current_mode.name if runtime.current_mode else None


def _color_dict(color) -> dict[str, int]:
    r, g, b = color
    return {"r": int(r), "g": int(g), "b": int(b)}


def _motor_ready(motor) -> bool:
    return bool(getattr(motor, "connected", False)) and not bool(
        getattr(motor, "simulation", False)
    )


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
            "motor_ready": _motor_ready(state.motor),
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
        state.led.set_color(color.r, color.g, color.b)
        return {
            "status": "success",
            "color": _color_dict(state.led.current_color),
            "power": state.led.is_on,
        }

    @app.post("/brightness")
    async def set_brightness(brightness: BrightnessInput):
        state.led.set_brightness(brightness.value)
        return {
            "status": "success",
            "brightness": state.led.brightness_percent,
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

    @app.post("/vision/gesture")
    async def handle_gesture(gesture_input: GestureInput):
        gesture = gesture_input.gesture
        brightness_step = 10

        if gesture == "brightness_up":
            next_value = min(100, state.led.brightness_percent + brightness_step)
            state.led.set_brightness(next_value)
            return {
                "gesture": gesture,
                "action": "brightness_changed",
                "brightness": state.led.brightness_percent,
            }

        if gesture == "brightness_down":
            next_value = max(0, state.led.brightness_percent - brightness_step)
            state.led.set_brightness(next_value)
            return {
                "gesture": gesture,
                "action": "brightness_changed",
                "brightness": state.led.brightness_percent,
            }

        motor_gestures = {
            "move_x_plus",
            "move_x_minus",
            "move_y_plus",
            "move_y_minus",
            "move_z_plus",
            "move_z_minus",
            "stop",
        }

        if gesture in motor_gestures:
            vector_by_gesture = {
                "move_x_plus": {"x": 1.0},
                "move_x_minus": {"x": -1.0},
                "move_y_plus": {"y": 1.0},
                "move_y_minus": {"y": -1.0},
                "move_z_plus": {"z": 1.0},
                "move_z_minus": {"z": -1.0},
                "stop": {"x": 0.0, "y": 0.0, "z": 0.0},
            }
            try:
                motor_status = await _run_blocking(
                    state.motor.move_xyz,
                    vector_by_gesture[gesture].get("x", 0.0),
                    vector_by_gesture[gesture].get("y", 0.0),
                    vector_by_gesture[gesture].get("z", 0.0),
                )
            except (RuntimeError, ValueError) as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc

            return {
                "gesture": gesture,
                "action": "motor_moved",
                "motor": motor_status,
            }

        raise HTTPException(status_code=400, detail=f"Unknown gesture: {gesture}")

    @app.post("/motor/xyz")
    async def move_motor_xyz(vector: MotorVectorInput):
        try:
            motor_status = await _run_blocking(
                state.motor.move_xyz,
                vector.x,
                vector.y,
                vector.z,
                vector.speed,
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "status": "success",
            "motor": motor_status,
        }

    @app.post("/motor/stop")
    async def stop_motor():
        try:
            motor_status = await _run_blocking(state.motor.stop)
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "status": "success",
            "motor": motor_status,
        }

    return app
