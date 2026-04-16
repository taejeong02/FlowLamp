import cv2
import mediapipe as mp
import math

# --- 초기화 ---
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
# min_detection_confidence를 조금 높여 정확도를 확보합니다.
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5, min_tracking_confidence=0.5)
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5, min_tracking_confidence=0.5)

def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def get_ear(landmarks, eye_indices):
    try:
        vertical1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
        vertical2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
        horizontal = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
        return (vertical1 + vertical2) / (2.0 * horizontal)
    except:
        return 0.3 # 에러 발생 시 기본값

def calculate_angle(shoulder, ear):
    angle = math.degrees(math.atan2(abs(ear.x - shoulder.x), abs(ear.y - shoulder.y)))
    return angle

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

blink_count = 0
blink_threshold = 0.20
blink_frames = 0
blink_frame_limit = 2
TURTLE_NECK_THRESHOLD = 7

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 인식 처리
    face_result = face_mesh.process(rgb)
    pose_result = pose.process(rgb)

    # 1. 거북목 감지
    if pose_result.pose_landmarks:
        p_landmarks = pose_result.pose_landmarks.landmark
        ear_p = p_landmarks[7]
        shoulder_p = p_landmarks[11]
        
        neck_angle = calculate_angle(shoulder_p, ear_p)
        color = (0, 255, 0)
        status_msg = "Good Posture"

        if neck_angle <= TURTLE_NECK_THRESHOLD:
            color = (0, 0, 255)
            status_msg = "TURTLE NECK!!"

        cv2.putText(frame, f"Neck Angle: {int(neck_angle)} deg", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, status_msg, (30, 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

    # 2. 눈 깜빡임 감지
    if face_result.multi_face_landmarks:
        for face_landmarks in face_result.multi_face_landmarks:
            landmarks = face_landmarks.landmark
            left_ear = get_ear(landmarks, LEFT_EYE)
            right_ear = get_ear(landmarks, RIGHT_EYE)
            ear = (left_ear + right_ear) / 2.0

            if ear < blink_threshold:
                blink_frames += 1
            else:
                if blink_frames >= blink_frame_limit:
                    blink_count += 1
                blink_frames = 0

    cv2.putText(frame, f"Blink Count: {blink_count}", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Smart Posture Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
# 리소스 명시적 해제
face_mesh.close()
pose.close()