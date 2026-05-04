from fastapi import FastAPI, BackgroundTasks
from devices.led import LEDController
import asyncio

app = FastAPI()
led = LEDController()

# 1. 앱 제어: 전원 ON/OFF
@app.post("/power")
async def toggle_power(status: str):
    if status == "on":
        led.turn_on()
    else:
        led.turn_off()
    return {"status": "success", "is_on": led.is_on}

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
        led.turn_off()
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
    uvicorn.run(app, host="0.0.0.0", port=8000)