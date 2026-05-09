"""Temporary manual test mode behavior."""


class TestMode:
    """센서 없이 직접 입력한 값으로 동작을 확인하는 임시 모드입니다."""

    name = "test"

    def __init__(self, led):
        self.led = led
        self.inputs = []

    async def enter(self):
        print("테스트모드 진입")
        self.led.current_color = (0, 80, 255)
        self.led.turn_on()

    async def update(self):
        """테스트모드에서 반복적으로 실행할 작업을 둡니다."""

    def handle_input(self, trigger: str, value):
        self.inputs.append({"trigger": trigger, "value": value})
        print(f"[테스트 입력] {trigger}={value}")

        if trigger == "power":
            if _is_on_value(value):
                self.led.turn_on()
                print("[테스트 결과] 전원이 켜졌습니다.")
                return "power_on"
            self.led.turn_off()
            print("[테스트 결과] 전원이 꺼졌습니다.")
            return "power_off"

        if trigger in ("motion", "person"):
            if _is_on_value(value):
                self.led.turn_on()
                print("[테스트 결과] 사람/움직임이 감지되어 LED가 켜졌습니다.")
                return "person_detected"
            print("[테스트 결과] 사람/움직임이 감지되지 않았습니다.")
            return "no_person"

        if trigger == "night":
            self.led.set_night_mode(_is_on_value(value))
            status = "켜졌습니다" if self.led.is_night_mode else "꺼졌습니다"
            print(f"[테스트 결과] 야간 모드가 {status}.")
            return "night_mode_changed"

        if trigger in ("alert", "drowsy", "posture"):
            if _is_on_value(value):
                self.led.blink_alert()
                print("[테스트 결과] 경고 알림이 실행되었습니다.")
                return "alert_triggered"
            print("[테스트 결과] 경고 상태가 아닙니다.")
            return "alert_normal"

        print("[테스트 결과] 알 수 없는 입력이라 기록만 했습니다.")
        return "recorded"


def _is_on_value(value):
    if isinstance(value, str):
        return value.lower() in ("1", "true", "on", "yes", "detected")
    return bool(value)
