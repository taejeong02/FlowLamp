import cv2
import mediapipe as mp
import math
import time
import json
from collections import deque
from datetime import datetime

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

def send_warning_signal(reason):
    print(f"SIGNAL: WARNING_ON / REASON: {reason}")

def send_good_signal(reason):
    print(f"SIGNAL: GOOD_OFF / REASON: {reason}")

def seconds_to_hms(seconds):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def calculate_scores(
    total_study_time,
    good_posture_time,
    away_time,
    drowsy_time,
    turtle_neck_count,
    drowsy_count
):
    if total_study_time <= 0:
        return 0, 0, 0, 0

    # 자세 점수 40점 만점
    posture_ratio = good_posture_time / total_study_time
    posture_score = int(posture_ratio * 40)

    # 거북목 횟수가 많으면 감점
    posture_score -= turtle_neck_count * 1
    posture_score = max(0, min(40, posture_score))

    # 집중 점수 40점 만점
    pure_study_time = max(0, total_study_time - away_time - drowsy_time)
    focus_ratio = pure_study_time / total_study_time
    focus_score = int(focus_ratio * 40)

    # 자리 이탈 시간이 길면 감점
    if away_time >= 300:
        focus_score -= 5
    focus_score = max(0, min(40, focus_score))

    # 졸음 점수 20점 만점
    drowsy_score = 20
    drowsy_score -= drowsy_count * 2
    drowsy_score -= int(drowsy_time // 60)
    drowsy_score = max(0, min(20, drowsy_score))

    total_score = posture_score + focus_score + drowsy_score

    return posture_score, focus_score, drowsy_score, total_score

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# 눈 깜빡임 설정
blink_count = 0
blink_threshold = 0.20
blink_frames = 0
blink_frame_limit = 2

# 졸음 설정
EYE_CLOSED_THRESHOLD = 0.20
EYE_CLOSED_HOLD_SECONDS = 5
eye_closed_start_time = None
eye_state = "OPEN"

# 목 각도 설정
TURTLE_ENTER_THRESHOLD = 24
TURTLE_EXIT_THRESHOLD = 18
TURTLE_HOLD_SECONDS = 3

angle_history = deque(maxlen=10)
is_turtle_neck = False
turtle_start_time = None
posture_state = "GOOD"

# =========================
# 통계 계산용 변수 추가
# =========================
study_date = datetime.now().strftime("%Y-%m-%d")
start_time = time.time()
prev_time = start_time

turtle_neck_count = 0
total_neck_angle = 0.0
neck_angle_sample_count = 0

good_posture_time = 0.0

away_count = 0
away_time = 0.0
away_start_time = None
is_away = False
AWAY_HOLD_SECONDS = 3

drowsy_count = 0
drowsy_time = 0.0

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        print("카메라 프레임을 읽지 못했습니다.")
        break

    current_time = time.time()
    delta_time = current_time - prev_time
    prev_time = current_time

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    face_result = face_mesh.process(rgb)
    pose_result = pose.process(rgb)

    turtle_elapsed = 0.0
    eye_closed_elapsed = 0.0

    posture_signal_msg = "Posture Signal: NONE"
    eye_signal_msg = "Eye Signal: NONE"

    pose_detected = pose_result.pose_landmarks is not None
    face_detected = face_result.multi_face_landmarks is not None
    user_present = pose_detected or face_detected

    # =========================
    # 자리 이탈 계산
    # =========================
    if not user_present:
        if away_start_time is None:
            away_start_time = current_time

        if not is_away and current_time - away_start_time >= AWAY_HOLD_SECONDS:
            is_away = True
            away_count += 1

        if is_away:
            away_time += delta_time
    else:
        away_start_time = None
        is_away = False

    # =========================
    # 1. 거북목 자세 인식
    # =========================
    if pose_detected:
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

        total_neck_angle += avg_angle
        neck_angle_sample_count += 1

        if not is_turtle_neck and avg_angle >= TURTLE_ENTER_THRESHOLD:
            is_turtle_neck = True
        elif is_turtle_neck and avg_angle <= TURTLE_EXIT_THRESHOLD:
            is_turtle_neck = False

        if is_turtle_neck:
            if turtle_start_time is None:
                turtle_start_time = current_time

            turtle_elapsed = current_time - turtle_start_time

            if turtle_elapsed >= TURTLE_HOLD_SECONDS and posture_state != "TURTLE_WARNING":
                send_warning_signal("TURTLE_NECK")
                posture_state = "TURTLE_WARNING"
                turtle_neck_count += 1

            if posture_state == "TURTLE_WARNING":
                posture_signal_msg = "Posture Signal: TURTLE_NECK_ON"
            else:
                posture_signal_msg = "Posture Signal: WAITING..."

        else:
            good_posture_time += delta_time

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

    if face_detected:
        eye_detected = True

        for face_landmarks in face_result.multi_face_landmarks:
            landmarks = face_landmarks.landmark

            left_ear_value = get_ear(landmarks, LEFT_EYE)
            right_ear_value = get_ear(landmarks, RIGHT_EYE)

            current_ear = (left_ear_value + right_ear_value) / 2.0

            if current_ear < blink_threshold:
                blink_frames += 1
            else:
                if blink_frames >= blink_frame_limit:
                    blink_count += 1
                blink_frames = 0

            if current_ear < EYE_CLOSED_THRESHOLD:
                is_eye_closed = True
            else:
                is_eye_closed = False

    if eye_detected:
        if is_eye_closed:
            if eye_closed_start_time is None:
                eye_closed_start_time = current_time

            eye_closed_elapsed = current_time - eye_closed_start_time

            if eye_closed_elapsed >= EYE_CLOSED_HOLD_SECONDS and eye_state != "CLOSED_WARNING":
                send_warning_signal("DROWSINESS_EYE_CLOSED")
                eye_state = "CLOSED_WARNING"
                drowsy_count += 1

            if eye_state == "CLOSED_WARNING":
                eye_signal_msg = "Eye Signal: DROWSINESS_ON"
                drowsy_time += delta_time
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
    # 3. 점수 계산
    # =========================
    total_study_time = current_time - start_time
    pure_study_time = max(0, total_study_time - away_time - drowsy_time)

    posture_score, focus_score, drowsy_score, total_score = calculate_scores(
        total_study_time,
        good_posture_time,
        away_time,
        drowsy_time,
        turtle_neck_count,
        drowsy_count
    )

    avg_head_angle = 0
    if neck_angle_sample_count > 0:
        avg_head_angle = total_neck_angle / neck_angle_sample_count

    # =========================
    # 4. 화면 표시
    # =========================
    cv2.putText(frame, f"Blink Count: {blink_count}", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.putText(frame, f"Turtle Count: {turtle_neck_count}", (30, 430),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Away Count: {away_count}", (30, 465),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Drowsy Count: {drowsy_count}", (30, 500),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Pure Study: {seconds_to_hms(pure_study_time)}", (30, 535),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Total Score: {total_score}", (30, 570),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    cv2.imshow("Smart Posture & Drowsiness Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# =========================
# 종료 후 Flutter로 넘길 최종 결과
# =========================
end_time = time.time()
total_study_time = end_time - start_time
pure_study_time = max(0, total_study_time - away_time - drowsy_time)

avg_head_angle = 0
if neck_angle_sample_count > 0:
    avg_head_angle = total_neck_angle / neck_angle_sample_count

posture_score, focus_score, drowsy_score, total_score = calculate_scores(
    total_study_time,
    good_posture_time,
    away_time,
    drowsy_time,
    turtle_neck_count,
    drowsy_count
)

result_data = {
    "study_date": study_date,

    "turtle_neck_count": turtle_neck_count,
    "avg_head_angle": round(avg_head_angle, 2),
    "good_posture_time": int(good_posture_time),

    "total_study_time": int(total_study_time),
    "pure_study_time": int(pure_study_time),
    "away_count": away_count,
    "away_time": int(away_time),

    "drowsy_count": drowsy_count,
    "drowsy_time": int(drowsy_time),

    "posture_score": posture_score,
    "focus_score": focus_score,
    "drowsy_score": drowsy_score,
    "total_score": total_score
}

print("\n========== 최종 학습 결과 ==========")
print(json.dumps(result_data, ensure_ascii=False, indent=4))

cap.release()
cv2.destroyAllWindows()

face_mesh.close()
pose.close()