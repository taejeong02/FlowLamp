"""LED device control."""
import time
import threading
try:
    from rpi_ws281x import PixelStrip, Color
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False
    print("⚠️ 하드웨어가 감지되지 않아 시뮬레이션 모드로 동작합니다.")

class LEDController:
    def __init__(self):
        # LED 설정 (라즈베리 파이 GPIO 18번 기준)
        self.LED_COUNT = 30      # LED 개수
        self.LED_PIN = 18        # GPIO 핀
        self.LED_BRIGHTNESS = 255 # 밝기 (0-255)
        
        self.is_on = False
        self.is_night_mode = False
        self.current_color = (255, 255, 255) # 초기값: 흰색
        self.alert_running = False

        if HAS_HARDWARE:
            self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, 800000, 10, False, self.LED_BRIGHTNESS)
            self.strip.begin()
        else:
            self.strip = None

    def _apply_color(self, r, g, b):
        """실제 LED에 색상을 적용하는 내부 메서드"""
        if not self.is_on:
            r, g, b = 0, 0, 0
            
        if HAS_HARDWARE and self.strip:
            color = Color(r, g, b)
            for i in range(self.LED_COUNT):
                self.strip.setPixelColor(i, color)
            self.strip.show()
        else:
            state = "ON" if self.is_on else "OFF"
            print(f"🎨 [LED {state}] 색상 적용: R:{r} G:{g} B:{b}")

    def turn_on(self):
        self.is_on = True
        self._apply_color(*self.current_color)

    def turn_off(self):
        self.is_on = False
        self._apply_color(0, 0, 0)

    def set_night_mode(self, active: bool):
        """야간 모드: 블루라이트를 줄이고 따뜻한 색감 적용"""
        self.is_night_mode = active
        if active:
            # 파란색(B)을 확 낮춘 따뜻한 주황/노란색
            self.current_color = (255, 100, 20) 
        else:
            self.current_color = (255, 255, 255)
        
        if self.is_on:
            self._apply_color(*self.current_color)

    def blink_alert(self):
        """거북목/졸음 감지 시 깜빡거림 (비동기 스레드로 동작)"""
        if self.alert_running: return
        
        def run_blink():
            self.alert_running = True
            original_state = self.is_on
            self.is_on = True # 경고를 위해 잠시 켬
            
            for _ in range(3): # 3번 깜빡임
                self._apply_color(255, 0, 0) # 빨간색 경고
                time.sleep(0.3)
                self._apply_color(0, 0, 0)
                time.sleep(0.3)
            
            # 원래 상태로 복구
            self.is_on = original_state
            self._apply_color(*self.current_color)
            self.alert_running = False
            

        threading.Thread(target=run_blink).start()