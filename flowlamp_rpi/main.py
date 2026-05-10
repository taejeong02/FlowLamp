import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from devices.led import LEDController
from modes.normal_mode import NormalMode
from modes.standby_mode import StandbyMode
from modes.test_mode import TestMode

led = LEDController()
night_schedule = {"is_on": False, "start": "23:00", "end": "06:00"}


class TestInput(BaseModel):
    trigger: str
    value: str | int | float | bool


class LampRuntime:
    def __init__(self, led_controller):
        self.led = led_controller
        self.modes = {
            "standby": StandbyMode(self.led),
            "normal": NormalMode(self.led),
            "test": TestMode(self.led),
        }
        self.current_mode = None
        self._mode_changed = asyncio.Event()

    async def start(self):
        await self.set_mode("standby")

        while True:
            if self.current_mode is not None:
                await self.current_mode.update()

            try:
                await asyncio.wait_for(self._mode_changed.wait(), timeout=0.2)
                self._mode_changed.clear()
            except asyncio.TimeoutError:
                pass

    async def set_mode(self, mode_name: str):
        if mode_name not in self.modes:
            raise ValueError(f"Unknown mode: {mode_name}")

        next_mode = self.modes[mode_name]
        if self.current_mode is next_mode:
            return

        self.current_mode = next_mode
        await self.current_mode.enter()
        self._mode_changed.set()

    async def handle_test_input(self, test_input: TestInput):
        await self.set_mode("test")
        return self.current_mode.handle_input(test_input.trigger, test_input.value)


runtime = LampRuntime(led)


async def time_checker_loop():
    while True:
        if night_schedule["is_on"]:
            current_time = datetime.now().strftime("%H:%M")
            start = night_schedule["start"]
            end = night_schedule["end"]

            if start > end:
                is_night_time = current_time >= start or current_time <= end
            else:
                is_night_time = start <= current_time <= end

            if is_night_time and not led.is_night_mode:
                led.set_night_mode(True)
                print("Night mode enabled automatically")
            elif not is_night_time and led.is_night_mode:
                led.set_night_mode(False)
                print("Night mode disabled automatically")

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(_app):
    runtime_task = asyncio.create_task(runtime.start())
    time_checker_task = asyncio.create_task(time_checker_loop())
    yield
    runtime_task.cancel()
    time_checker_task.cancel()


app = FastAPI(lifespan=lifespan)
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
        "mode": runtime.current_mode.name if runtime.current_mode else None,
        "is_on": led.is_on,
        "night_mode": led.is_night_mode,
        "color": led.current_color,
        "brightness": led.brightness_percent,
    }


@app.post("/mode/{mode_name}")
async def set_mode(mode_name: str):
    try:
        await runtime.set_mode(mode_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"mode": runtime.current_mode.name}


@app.post("/power")
async def toggle_power(status: str):
    if status == "on":
        await runtime.set_mode("normal")
    else:
        await runtime.set_mode("standby")
    return {
        "status": "success",
        "mode": runtime.current_mode.name if runtime.current_mode else None,
        "is_on": led.is_on,
    }


@app.post("/color")
async def set_color(
    r: int = Query(..., ge=0, le=255),
    g: int = Query(..., ge=0, le=255),
    b: int = Query(..., ge=0, le=255),
):
    led.set_color(r, g, b)
    return {
        "status": "success",
        "color": led.current_color,
        "is_on": led.is_on,
    }


@app.post("/brightness")
async def set_brightness(value: int = Query(..., ge=0, le=100)):
    led.set_brightness(value)
    return {
        "status": "success",
        "brightness": led.brightness_percent,
        "is_on": led.is_on,
    }


@app.post("/test/input")
async def send_test_input(test_input: TestInput):
    try:
        action = await runtime.handle_test_input(test_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "mode": runtime.current_mode.name,
        "trigger": test_input.trigger,
        "value": test_input.value,
        "action": action,
        "is_on": led.is_on,
    }


@app.post("/night_mode/schedule")
async def set_night_schedule(is_on: bool, start_time: str, end_time: str):
    night_schedule["is_on"] = is_on
    night_schedule["start"] = start_time
    night_schedule["end"] = end_time

    if not is_on and led.is_night_mode:
        led.set_night_mode(False)
        print("Night mode disabled immediately")

    return {"message": "night schedule saved", "data": night_schedule}


@app.post("/timer/done")
async def timer_done_alert():
    print("Timer done signal received")
    led.blink_alert()
    await runtime.set_mode("standby")
    return {"status": "alert_triggered"}


@app.post("/alert")
async def receive_ai_signal(signal: int):
    if signal == 1:
        print("Alert signal received")
        led.blink_alert()
        return {"alert": "triggered"}
    return {"alert": "normal"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("FLOWLAMP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
