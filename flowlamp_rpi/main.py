import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from devices.led import LEDController
from modes.normal_mode import NormalMode
from modes.standby_mode import StandbyMode
from modes.test_mode import TestMode
import asyncio

led = LEDController()


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


@asynccontextmanager
async def lifespan(_app):
    runtime_task = asyncio.create_task(runtime.start())
    yield
    runtime_task.cancel()


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
    }


@app.post("/mode/{mode_name}")
async def set_mode(mode_name: str):
    try:
        await runtime.set_mode(mode_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"mode": runtime.current_mode.name}

# 1. 앱 제어: 전원 ON/OFF
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

# 2. 앱 제어: 야간 모드
@app.post("/mode/night")
async def set_night_mode(active: bool):
    led.set_night_mode(active)
    return {"night_mode": active}

# 2. 앱 제어: 타이머 (n초 뒤 종료)
@app.post("/timer")
async def set_timer(seconds: int):
    async def delayed_off(sec):
        await asyncio.sleep(sec)
        await runtime.set_mode("standby")
        print(f"⏰ 타이머 종료: {sec}초 경과")

    asyncio.create_task(delayed_off(seconds))
    return {"status": "timer_set", "seconds": seconds}

# 3. 카메라 AI 신호 수신 (다른 인원이 보낼 0, 1 신호)
@app.post("/alert")
async def receive_ai_signal(signal: int):
    """
    signal 1: 거북목 또는 졸음 감지됨
    signal 0: 정상 상태
    """
    if signal == 1:
        print("🚨 경고 신호 수신: 사용자 알림 시작")
        led.blink_alert()
        return {"alert": "triggered"}
    return {"alert": "normal"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("FLOWLAMP_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
