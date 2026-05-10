import os
from contextlib import asynccontextmanager
<<<<<<< HEAD
from datetime import datetime
from fastapi import FastAPI, HTTPException
=======

from fastapi import FastAPI, HTTPException, Query
>>>>>>> 7f49034e97268e790c3e959370be3fef907a87d8
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from devices.led import LEDController
from modes.normal_mode import NormalMode
from modes.standby_mode import StandbyMode
from modes.test_mode import TestMode
import asyncio

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

# 👈 추가된 부분: 1분마다 시간을 확인해서 야간 모드를 켜고 끄는 백그라운드 루프
async def time_checker_loop():
    while True:
        if night_schedule["is_on"]:
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            start = night_schedule["start"]
            end = night_schedule["end"]

            # 자정을 넘기는 시간 계산 (예: 23:00 ~ 06:00)
            if start > end: 
                is_night_time = current_time >= start or current_time <= end
            else:
                is_night_time = start <= current_time <= end

            # 조건에 맞으면 LED 상태 변경
            if is_night_time and not led.is_night_mode:
                led.set_night_mode(True)
                print("🌙 야간 모드 자동 켜짐!")
            elif not is_night_time and led.is_night_mode:
                led.set_night_mode(False)
                print("☀️ 야간 모드 자동 꺼짐!")
        
        await asyncio.sleep(60) # 60초(1분) 대기 후 다시 루프 돎

# 👇 수정된 부분: 앱 실행 시 타임 체커도 같이 실행되도록 등록
@asynccontextmanager
async def lifespan(_app):
    runtime_task = asyncio.create_task(runtime.start())
    time_checker_task = asyncio.create_task(time_checker_loop()) # 타임 체커 시작
    yield
    runtime_task.cancel()
    time_checker_task.cancel() # 타임 체커 종료


app = FastAPI(lifespan=lifespan)
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

# 2. 앱 제어: 야간 모드 스케줄링 설정
@app.post("/night_mode/schedule")
async def set_night_schedule(is_on: bool, start_time: str, end_time: str):
    """
    앱에서 시작/종료 시간을 설정할 때 호출하는 엔드포인트
    - start_time, end_time 예시: "23:00", "06:00"
    """
    night_schedule["is_on"] = is_on
    night_schedule["start"] = start_time
    night_schedule["end"] = end_time
    
    # 만약 스위치를 껐다면 즉시 야간 모드 해제
    if not is_on and led.is_night_mode:
        led.set_night_mode(False)
        print("☀️ 야간 모드 즉시 해제됨")
        
    return {"message": "야간 모드 스케줄 저장 완료", "data": night_schedule}

# 2. 앱 제어: 집중 타이머 종료 알림 수신
@app.post("/timer/done")
async def timer_done_alert():
    print("⏰ 앱에서 타이머 종료 신호 수신! 알림 불빛 작동")
    
    # 램프를 깜빡여서 사용자에게 시간이 다 되었음을 알림
    led.blink_alert() 
    
    #  알림 후에 램프를 아예 꺼버림
    await runtime.set_mode("standby")
    
    return {"status": "alert_triggered"}

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
