import cv2
import mediapipe as mp
import math
import time

# --- 설정 ---
BLINK_THRESHOLD = 0.20
DROWSY_TIME_LIMIT = 5.0

DEAD_ZONE_XY = 40      # 좌우/상하 중앙 허용 오차(px)
DEAD_ZONE_Z = 25       # 앞뒤 손 크기 허용 오차(px)

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 100
BRIGHTNESS_LEVEL = 50
ROTATION_BRIGHTNESS_THRESHOLD = 12
ROTATION_BRIGHTNESS_STEP = 1
ROTATION_BRIGHTNESS_SENSITIVITY = 8
ROTATION_HISTORY_SIZE = 6
ROTATION_STABLE_FRAMES = 4

mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    min_detection_confidence=0.5
)

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def get_ear(landmarks, eye_indices):
    try:
        v1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
        v2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
        h = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
        return (v1 + v2) / (2.0 * h)
    except:
        return 0.3

def is_v_gesture(hand_landmarks):
    lm = hand_landmarks.landmark

    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_down = lm[16].y > lm[14].y
    pinky_down = lm[20].y > lm[18].y

    return index_up and middle_up and ring_down and pinky_down

def is_open_palm(hand_landmarks):
    lm = hand_landmarks.landmark

    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_up = lm[16].y < lm[14].y
    pinky_up = lm[20].y < lm[18].y

    return index_up and middle_up and ring_up and pinky_up

def is_closed_fist(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark
    palm_x = (lm[0].x + lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 5 * frame_w
    palm_y = (lm[0].y + lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 5 * frame_h
    hand_size = get_hand_size(hand_landmarks, frame_w, frame_h)
    threshold = hand_size * 0.45

    for idx in [4, 8, 12, 16, 20]:
        tip_x = lm[idx].x * frame_w
        tip_y = lm[idx].y * frame_h
        if math.hypot(tip_x - palm_x, tip_y - palm_y) > threshold:
            return False

    return True

def get_hand_size(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark

    # 손목 0번과 손바닥 중앙 근처 9번 사이 거리
    x0 = lm[0].x * frame_w
    y0 = lm[0].y * frame_h

    x9 = lm[9].x * frame_w
    y9 = lm[9].y * frame_h

    return math.hypot(x9 - x0, y9 - y0)

def get_tracking_command(error_x, error_y):
    move_x = "STOP"
    move_y = "STOP"

    if error_x > DEAD_ZONE_XY:
        move_x = f"RIGHT {abs(error_x)}px"
    elif error_x < -DEAD_ZONE_XY:
        move_x = f"LEFT {abs(error_x)}px"

    if error_y > DEAD_ZONE_XY:
        move_y = f"DOWN {abs(error_y)}px"
    elif error_y < -DEAD_ZONE_XY:
        move_y = f"UP {abs(error_y)}px"

    return move_x, move_y

def get_depth_command(error_z):
    if error_z > DEAD_ZONE_Z:
        return f"HEAD FORWARD {int(error_z)}px"
    elif error_z < -DEAD_ZONE_Z:
        return f"HEAD BACKWARD {int(abs(error_z))}px"
    else:
        return "STOP"
    
def get_hand_rotation(hand_landmarks):
    lm = hand_landmarks.landmark

    # 왼쪽과 오른쪽 손바닥 끝점 간 각도 계산
    index_base = lm[5]
    pinky_base = lm[17]

    dx = pinky_base.x - index_base.x
    dy = pinky_base.y - index_base.y
    angle = math.degrees(math.atan2(dy, dx))

    # 손바닥이 거의 수평일 때를 0도로 정규화
    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    return angle

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

eyes_closed_start_time = 0
drowsy_detected = False

# 앞뒤 기준 손 크기
base_hand_size = 0
fist_rotation_history = []
fist_rotation_reference = None

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    frame_h, frame_w, _ = frame.shape

    center_x = frame_w // 2
    center_y = frame_h // 2

    # 화면 중앙 표시
    cv2.circle(frame, (center_x, center_y), 8, (0, 255, 255), -1)
    cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 255), 2)
    cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 255), 2)

    # 1. 졸음 체크
    face_result = face_mesh.process(rgb_frame)

    if face_result.multi_face_landmarks:
        for face_landmarks in face_result.multi_face_landmarks:
            ear = get_ear(face_landmarks.landmark, LEFT_EYE + RIGHT_EYE)

            if ear < BLINK_THRESHOLD:
                if eyes_closed_start_time == 0:
                    eyes_closed_start_time = time.time()
                elif time.time() - eyes_closed_start_time >= DROWSY_TIME_LIMIT:
                    drowsy_detected = True
            else:
                eyes_closed_start_time = 0
                drowsy_detected = False

            cv2.putText(frame, f"EAR: {ear:.2f}", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # 2. 손 인식
    hand_result = hands.process(rgb_frame)

    v_detected = False
    palm_detected = False
    fist_detected = False

    if hand_result.multi_hand_landmarks:
        for hand_landmarks in hand_result.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            lm = hand_landmarks.landmark

            if is_v_gesture(hand_landmarks):
                v_detected = True

            rotation_angle = get_hand_rotation(hand_landmarks)

            if is_open_palm(hand_landmarks):
                palm_detected = True
            else:
                # 손바닥 tracking이 아닌 경우에만 밝기 참조를 초기화
                pass

            if is_closed_fist(hand_landmarks, frame_w, frame_h):
                fist_detected = True
                fist_rotation_history.append(rotation_angle)
                if len(fist_rotation_history) > ROTATION_HISTORY_SIZE:
                    fist_rotation_history.pop(0)
            else:
                fist_rotation_history.clear()
                fist_rotation_reference = None

            smooth_rotation = rotation_angle
            if len(fist_rotation_history) >= ROTATION_STABLE_FRAMES:
                smooth_rotation = sum(fist_rotation_history) / len(fist_rotation_history)
                if fist_rotation_reference is None:
                    fist_rotation_reference = smooth_rotation

            if fist_rotation_reference is None:
                brightness_msg = "Show fist to set brightness reference"
            else:
                delta_angle = smooth_rotation - fist_rotation_reference
                if delta_angle > ROTATION_BRIGHTNESS_THRESHOLD:
                    brightness_msg = f"BRIGHTNESS UP {int(delta_angle)}°"
                elif delta_angle < -ROTATION_BRIGHTNESS_THRESHOLD:
                    brightness_msg = f"BRIGHTNESS DOWN {int(abs(delta_angle))}°"
                else:
                    brightness_msg = "BRIGHTNESS HOLD"

            if palm_detected:

                # 손 중심 좌표
                hand_x = int(lm[9].x * frame_w)
                hand_y = int(lm[9].y * frame_h)

                error_x = hand_x - center_x
                error_y = hand_y - center_y

                move_x, move_y = get_tracking_command(error_x, error_y)

                # 손 크기 계산
                hand_size = get_hand_size(hand_landmarks, frame_w, frame_h)

                # 처음 손바닥을 펼쳤을 때 기준 크기 저장
                if base_hand_size == 0:
                    base_hand_size = hand_size

                error_z = hand_size - base_hand_size
                move_z = get_depth_command(error_z)

                # 손 중심점 표시
                cv2.circle(frame, (hand_x, hand_y), 10, (255, 0, 0), -1)

                # 중앙점과 손 중심점 연결
                cv2.line(frame, (center_x, center_y), (hand_x, hand_y), (255, 255, 0), 2)

                cv2.putText(frame, "OPEN PALM TRACKING", (50, 160),
                            cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 0), 2)

                cv2.putText(frame, f"Hand Center: ({hand_x}, {hand_y})", (50, 200),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                cv2.putText(frame, f"Screen Center: ({center_x}, {center_y})", (50, 230),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

                cv2.putText(frame, f"Error X: {error_x}px", (50, 270),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                cv2.putText(frame, f"Error Y: {error_y}px", (50, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                cv2.putText(frame, f"Motor X: {move_x}", (50, 340),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                cv2.putText(frame, f"Motor Y: {move_y}", (50, 375),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                cv2.putText(frame, f"Base Hand Size: {int(base_hand_size)}", (50, 420),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.putText(frame, f"Current Hand Size: {int(hand_size)}", (50, 450),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.putText(frame, f"Depth Error: {int(error_z)}px", (50, 480),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                cv2.putText(frame, f"Motor Z: {move_z}", (50, 520),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)
                
                cv2.putText(frame, f"Hand Rotation: {int(rotation_angle)} deg", (50, 560),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

            if fist_detected and fist_rotation_reference is not None and len(fist_rotation_history) >= ROTATION_STABLE_FRAMES:
                delta_angle = smooth_rotation - fist_rotation_reference
                if delta_angle > ROTATION_BRIGHTNESS_THRESHOLD:
                    delta = max(ROTATION_BRIGHTNESS_STEP, int((delta_angle - ROTATION_BRIGHTNESS_THRESHOLD) / ROTATION_BRIGHTNESS_SENSITIVITY))
                    BRIGHTNESS_LEVEL = min(BRIGHTNESS_MAX, BRIGHTNESS_LEVEL + delta)
                elif delta_angle < -ROTATION_BRIGHTNESS_THRESHOLD:
                    delta = max(ROTATION_BRIGHTNESS_STEP, int((abs(delta_angle) - ROTATION_BRIGHTNESS_THRESHOLD) / ROTATION_BRIGHTNESS_SENSITIVITY))
                    BRIGHTNESS_LEVEL = max(BRIGHTNESS_MIN, BRIGHTNESS_LEVEL - delta)

            if fist_detected:
                if fist_rotation_reference is not None:
                    delta_angle = smooth_rotation - fist_rotation_reference
                    cv2.putText(frame, f"Rotation Δ: {int(delta_angle)} deg", (50, 590),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                    cv2.putText(frame, f"Reference Angle: {int(fist_rotation_reference)} deg", (50, 620),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 0), 2)
                    y_offset = 660
                else:
                    y_offset = 600

                cv2.putText(frame, brightness_msg, (50, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                cv2.putText(frame, f"Brightness: {BRIGHTNESS_LEVEL}%", (50, y_offset + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)

    # 손바닥이 안 보이면 기준값 초기화
    if not palm_detected:
        base_hand_size = 0

    # 3. 출력
    if drowsy_detected:
        cv2.putText(frame, "SLEEPING ALERT!", (50, 100),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)

    if v_detected:
        cv2.putText(frame, "V GESTURE!", (50, 130),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 2)

    if not palm_detected:
        cv2.putText(frame, "Show Open Palm to Track Lamp", (50, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 200), 2)

    cv2.imshow('Safety Monitor', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()
hands.close()