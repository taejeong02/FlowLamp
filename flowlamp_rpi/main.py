import os
import asyncio
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import uvicorn

try:
    from api import ApiState, create_app
    from study_records import StudyRecordRepository
except ImportError:
    from .api import ApiState, create_app
    from .study_records import StudyRecordRepository
from devices.led import LEDController
from devices.motor import MotorController
from modes.normal_mode import NormalMode
from modes.standby_mode import StandbyMode

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STUDY_DB_PATH = Path(
    os.getenv("FLOWLAMP_STUDY_DB", str(PROJECT_ROOT / "ai" / "study_records.db"))
)
AI_SCRIPTS = {
    "face": PROJECT_ROOT / "ai" / "facetest.py",
    "hand": PROJECT_ROOT / "ai" / "handtest.py",
}

led = LEDController()
motor = MotorController()
night_schedule = {"is_on": False, "start_time": "23:00", "end_time": "06:00"}
night_schedule_lock = threading.Lock()
person_state = {
    "detected": False,
    "version": 0,
    "last_update": None,
    "absence_timer": None,
}
person_state_lock = threading.Lock()


class LampRuntime:
    def __init__(self, led_controller):
        self.led = led_controller
        self.modes = {
            "standby": StandbyMode(self.led),
            "normal": NormalMode(self.led),
        }
        if os.getenv("FLOWLAMP_ENABLE_TEST_MODE") == "1":
            from modes.test_mode import TestMode

            self.modes["test"] = TestMode(self.led)
        self.current_mode = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._main_task: asyncio.Task | None = None
        self._mode_changed: asyncio.Event | None = None
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    async def start(self):
        self._mode_changed = asyncio.Event()
        await self.set_mode("standby")
        self._ready.set()

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
        if self._mode_changed is not None:
            self._mode_changed.set()

    async def handle_test_input(self, trigger: str, value):
        if "test" not in self.modes:
            raise RuntimeError(
                "Test mode is disabled. Set FLOWLAMP_ENABLE_TEST_MODE=1 to enable it."
            )

        await self.set_mode("test")
        return self.current_mode.handle_input(trigger, value)

    def start_thread(self):
        if self._thread is not None and self._thread.is_alive():
            return

        self._thread = threading.Thread(
            target=self._run_event_loop,
            name="lamp-runtime",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Lamp runtime thread did not become ready.")

    def stop_thread(self):
        if self._loop is not None and self._main_task is not None:
            self._loop.call_soon_threadsafe(self._main_task.cancel)

        if self._thread is not None:
            self._thread.join(timeout=5)

    def set_mode_threadsafe(self, mode_name: str):
        return self._run_threadsafe(lambda: self.set_mode(mode_name))

    def handle_test_input_threadsafe(self, trigger: str, value):
        return self._run_threadsafe(lambda: self.handle_test_input(trigger, value))

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._main_task = self._loop.create_task(self.start())

        try:
            self._loop.run_until_complete(self._main_task)
        except asyncio.CancelledError:
            pass
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            if pending:
                self._loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            self._loop.close()

    def _run_threadsafe(self, coroutine_factory):
        if not self._ready.wait(timeout=5):
            raise RuntimeError("Lamp runtime thread is not ready.")
        if self._loop is None:
            raise RuntimeError("Lamp runtime loop is not running.")

        future = asyncio.run_coroutine_threadsafe(coroutine_factory(), self._loop)
        return future.result(timeout=5)


runtime = LampRuntime(led)


def is_night_schedule_active(schedule=None):
    if schedule is None:
        with night_schedule_lock:
            schedule = night_schedule.copy()

    if not schedule["is_on"]:
        return False

    try:
        current_time = datetime.now().time()
        start_time = datetime.strptime(schedule["start_time"], "%H:%M").time()
        end_time = datetime.strptime(schedule["end_time"], "%H:%M").time()
    except ValueError as exc:
        print(f"Invalid night schedule time: {exc}")
        return False

    if start_time <= end_time:
        return start_time <= current_time <= end_time

    return current_time >= start_time or current_time <= end_time


def time_checker_loop(stop_event: threading.Event):
    while not stop_event.is_set():
        with night_schedule_lock:
            schedule = night_schedule.copy()

        if schedule["is_on"]:
            is_night_time = is_night_schedule_active(schedule)
            if is_night_time and not led.is_night_mode:
                led.set_night_mode(True)
                print("Night mode enabled automatically")
            elif not is_night_time and led.is_night_mode:
                led.set_night_mode(False)
                print("Night mode disabled automatically")

        stop_event.wait(60)


def create_flowlamp_app():
    return create_app(
        ApiState(
            led=led,
            motor=motor,
            runtime=runtime,
            night_schedule=night_schedule,
            night_schedule_lock=night_schedule_lock,
            is_night_active=is_night_schedule_active,
            person_state=person_state,
            person_state_lock=person_state_lock,
            study_records=StudyRecordRepository(STUDY_DB_PATH),
        )
    )


app = create_flowlamp_app()


class ApiServerThread:
    def __init__(self, app, host: str, port: int):
        self.server = uvicorn.Server(
            uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=False,
            )
        )
        self.thread = threading.Thread(
            target=self.server.run,
            name="flowlamp-api",
            daemon=True,
        )

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.should_exit = True
        self.thread.join(timeout=5)


class VisionScriptThread:
    def __init__(self, name: str, script_path: Path, extra_env: dict[str, str] | None = None):
        self.name = name
        self.script_path = script_path
        self.extra_env = extra_env or {}
        self.process: subprocess.Popen | None = None
        self.thread = threading.Thread(
            target=self._run,
            name=f"vision-{name}",
            daemon=True,
        )
        self._stopping = False

    def start(self):
        if not self.script_path.exists():
            print(f"Vision script not found: {self.script_path}")
            return

        self.thread.start()

    def stop(self):
        self._stopping = True

        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()

        self.thread.join(timeout=5)

    def _run(self):
        env = os.environ.copy()
        env.update(self.extra_env)

        print(f"Starting vision script: {self.name} ({self.script_path})")
        try:
            self.process = subprocess.Popen(
                [sys.executable, str(self.script_path)],
                cwd=PROJECT_ROOT,
                env=env,
            )
            return_code = self.process.wait()
        except OSError as exc:
            print(f"Vision script failed to start: {self.name}: {exc}")
            return

        if not self._stopping:
            print(f"Vision script exited: {self.name} code={return_code}")


def create_vision_threads(port: int):
    if os.getenv("FLOWLAMP_ENABLE_VISION", "1") == "0":
        return []

    api_url = os.getenv("FLOWLAMP_API_URL", f"http://127.0.0.1:{port}")
    shared_env = {"FLOWLAMP_API_URL": api_url}
    threads = []

    if os.getenv("FLOWLAMP_ENABLE_FACE_AI", "1") != "0":
        threads.append(VisionScriptThread("face", AI_SCRIPTS["face"], shared_env))

    if os.getenv("FLOWLAMP_ENABLE_HAND_AI", "1") != "0":
        threads.append(VisionScriptThread("hand", AI_SCRIPTS["hand"], shared_env))

    return threads


def main():
    stop_event = threading.Event()
    host = os.getenv("FLOWLAMP_HOST", "0.0.0.0")
    port = int(os.getenv("FLOWLAMP_PORT", "8000"))
    vision_threads = []

    motor.connect()
    runtime.start_thread()

    night_thread = threading.Thread(
        target=time_checker_loop,
        args=(stop_event,),
        name="night-mode-checker",
        daemon=True,
    )
    night_thread.start()

    api_server = ApiServerThread(app, host, port)
    api_server.start()
    vision_threads = create_vision_threads(port)
    for vision_thread in vision_threads:
        vision_thread.start()

    print(f"FlowLamp API server started on {host}:{port}")
    print("Runtime, night checker, API server, and vision scripts are running.")

    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("FlowLamp shutdown requested.")
    finally:
        stop_event.set()
        for vision_thread in vision_threads:
            vision_thread.stop()
        api_server.stop()
        runtime.stop_thread()
        night_thread.join(timeout=5)
        motor.close()
        led.close()


if __name__ == "__main__":
    main()
