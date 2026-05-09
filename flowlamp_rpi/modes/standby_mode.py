"""Standby mode behavior."""


class StandbyMode:
    """전원이 꺼진 대기 상태를 관리합니다."""

    name = "standby"

    def __init__(self, led):
        self.led = led

    async def enter(self):
        print("대기모드 진입")
        self.led.turn_off()

    async def update(self):
        """대기모드에서 반복적으로 실행할 작업을 둡니다."""
