"""Normal mode behavior."""


class NormalMode:
    """전원 트리거 이후의 기본 동작 상태를 관리합니다."""

    name = "normal"

    def __init__(self, led):
        self.led = led

    async def enter(self):
        print("기본모드 진입")
        self.led.turn_on()

    async def update(self):
        """기본모드에서 반복적으로 실행할 작업을 둡니다."""
