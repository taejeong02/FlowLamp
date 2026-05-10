import cv2
import mediapipe as mp
import math
import time
from collections import deque

# --- 초기화 ---
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose

face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

pose = mp_pose.Pose(
    static_image_mode=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def midpoint(p1, p2):
    class Point:
        pass

    p = Point()
    p.x = (p1.x + p2.x) / 2
    p.y = (p1.y + p2.y) / 2
    return p

def get_ear(landmarks, eye_indices):
    try:
        vertical1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
        vertical2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
        horizontal = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
        return (vertical1 + vertical2) / (2.0 * horizontal)
    except:
        return 0.3

def calculate_neck_angle(shoulder_center, ear_center):
    dx = ear_center.x - shoulder_center.x
    dy = shoulder_center.y - ear_center.y
    angle = math.degrees(math.atan2(abs(dx), abs(dy)))
    return angle

# 임시 신호 함수
# 나중에 라즈베리파이 GPIO 코드로 교체하면 됨
def send_warning_signal(reason):
    print(f"SIGNAL: WARNING_ON / REASON: {reason}")

def send_good_signal(reason):
    print(f"SIGNAL: GOOD_OFF / REASON: {reason}")

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# 눈 깜빡임 설정
blink_count = 0
blink_threshold = 0.20
blink_frames = 0
blink_frame_limit = 2

# 눈 감김 / 졸음 설정
EYE_CLOSED_THRESHOLD = 0.20
EYE_CLOSED_HOLD_SECONDS = 5
eye_closed_start_time = None
eye_state = "OPEN"   # OPEN / CLOSED_WARNING

# 목 각도 기준값
TURTLE_ENTER_THRESHOLD = 24
TURTLE_EXIT_THRESHOLD = 18

# 거북목 흔들림 방지
angle_history = deque(maxlen=10)
is_turtle_neck = False

# 거북목 3초 유지 신호 설정
TURTLE_HOLD_SECONDS = 3
turtle_start_time = None
posture_state = "GOOD"   # GOOD / TURTLE_WARNING

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        print("카메라 프레임을 읽지 못했습니다.")
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_result = face_mesh.process(rgb)
    pose_result = pose.process(rgb)

    turtle_elapsed = 0.0
    eye_closed_elapsed = 0.0

    posture_signal_msg = "Posture Signal: NONE"
    eye_signal_msg = "Eye Signal: NONE"

    # =========================
    # 1. 거북목 자세 인식
    # =========================
    if pose_result.pose_landmarks:
        p_landmarks = pose_result.pose_landmarks.landmark

        left_ear = p_landmarks[7]
        right_ear = p_landmarks[8]
        left_shoulder = p_landmarks[11]
        right_shoulder = p_landmarks[12]

        ear_center = midpoint(left_ear, right_ear)
        shoulder_center = midpoint(left_shoulder, right_shoulder)

        neck_angle = calculate_neck_angle(shoulder_center, ear_center)

        angle_history.append(neck_angle)
        avg_angle = sum(angle_history) / len(angle_history)

        if not is_turtle_neck and avg_angle >= TURTLE_ENTER_THRESHOLD:
            is_turtle_neck = True
        elif is_turtle_neck and avg_angle <= TURTLE_EXIT_THRESHOLD:
            is_turtle_neck = False

        if is_turtle_neck:
            if turtle_start_time is None:
                turtle_start_time = time.time()

            turtle_elapsed = time.time() - turtle_start_time

            if turtle_elapsed >= TURTLE_HOLD_SECONDS and posture_state != "TURTLE_WARNING":
                send_warning_signal("TURTLE_NECK")
                posture_state = "TURTLE_WARNING"

            if posture_state == "TURTLE_WARNING":
                posture_signal_msg = "Posture Signal: TURTLE_NECK_ON"
            else:
                posture_signal_msg = "Posture Signal: WAITING..."

        else:
            if posture_state == "TURTLE_WARNING":
                send_good_signal("POSTURE_GOOD")
                posture_signal_msg = "Posture Signal: POSTURE_GOOD"

            posture_state = "GOOD"
            turtle_start_time = None
            turtle_elapsed = 0.0

        if is_turtle_neck:
            posture_color = (0, 0, 255)
            posture_msg = "TURTLE NECK DETECTED"
        else:
            posture_color = (0, 255, 0)
            posture_msg = "Good Posture"

        cv2.putText(frame, f"Neck Angle: {int(avg_angle)} deg", (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, posture_color, 2)

        cv2.putText(frame, posture_msg, (30, 145),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, posture_color, 2)

        cv2.putText(frame, f"Turtle Timer: {turtle_elapsed:.1f} / {TURTLE_HOLD_SECONDS}s", (30, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.putText(frame, posture_signal_msg, (30, 215),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    else:
        cv2.putText(frame, "Pose not detected", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # =========================
    # 2. 눈 깜빡임 + 졸음 인식
    # =========================
    eye_detected = False
    current_ear = 0.0
    is_eye_closed = False

    if face_result.multi_face_landmarks:
        eye_detected = True

        for face_landmarks in face_result.multi_face_landmarks:
            landmarks = face_landmarks.landmark

            left_ear_value = get_ear(landmarks, LEFT_EYE)
            right_ear_value = get_ear(landmarks, RIGHT_EYE)

            current_ear = (left_ear_value + right_ear_value) / 2.0

            # 기존 눈 깜빡임 카운트
            if current_ear < blink_threshold:
                blink_frames += 1
            else:
                if blink_frames >= blink_frame_limit:
                    blink_count += 1
                blink_frames = 0

            # 눈 감김 상태 판단
            if current_ear < EYE_CLOSED_THRESHOLD:
                is_eye_closed = True
            else:
                is_eye_closed = False

    if eye_detected:
        if is_eye_closed:
            if eye_closed_start_time is None:
                eye_closed_start_time = time.time()

            eye_closed_elapsed = time.time() - eye_closed_start_time

            if eye_closed_elapsed >= EYE_CLOSED_HOLD_SECONDS and eye_state != "CLOSED_WARNING":
                send_warning_signal("DROWSINESS_EYE_CLOSED")
                eye_state = "CLOSED_WARNING"

            if eye_state == "CLOSED_WARNING":
                eye_signal_msg = "Eye Signal: DROWSINESS_ON"
            else:
                eye_signal_msg = "Eye Signal: WAITING..."

            eye_color = (0, 0, 255)
            eye_msg = "Eyes Closed"

        else:
            if eye_state == "CLOSED_WARNING":
                send_good_signal("EYES_OPEN")
                eye_signal_msg = "Eye Signal: EYES_OPEN"

            eye_state = "OPEN"
            eye_closed_start_time = None
            eye_closed_elapsed = 0.0

            eye_color = (0, 255, 0)
            eye_msg = "Eyes Open"

        cv2.putText(frame, f"EAR: {current_ear:.2f}", (30, 275),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, eye_color, 2)

        cv2.putText(frame, eye_msg, (30, 310),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, eye_color, 2)

        cv2.putText(frame, f"Eye Closed Timer: {eye_closed_elapsed:.1f} / {EYE_CLOSED_HOLD_SECONDS}s", (30, 345),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.putText(frame, eye_signal_msg, (30, 380),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    else:
        cv2.putText(frame, "Face not detected", (30, 275),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        eye_closed_start_time = None
        eye_closed_elapsed = 0.0

    # =========================
    # 3. 공통 표시
    # =========================
    cv2.putText(frame, f"Blink Count: {blink_count}", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Smart Posture & Drowsiness Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

face_mesh.close()
pose.close()