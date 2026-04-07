import cv2
import mediapipe as mp
import math

# --- 초기화 ---
mp_face_mesh = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
pose = mp_pose.Pose(static_image_mode=False, min_detection_confidence=0.5)

def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

# 눈 깜빡임 EAR 계산 함수
def get_ear(landmarks, eye_indices):
    vertical1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
    vertical2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
    horizontal = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
    return (vertical1 + vertical2) / (2.0 * horizontal)

# 귀와 어깨 사이의 각도 계산 함수
def calculate_angle(shoulder, ear):
    # 어깨와 귀의 상대적 위치를 이용해 각도 계산
    # 사용자 테스트 결과에 따라 고개가 앞으로 나갈수록(거북목) 각도가 작아지는 구조
    angle = math.degrees(math.atan2(abs(ear.x - shoulder.x), abs(ear.y - shoulder.y)))
    return angle

# 랜드마크 인덱스 설정
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# 설정 변수
blink_count = 0
blink_threshold = 0.20
blink_frames = 0
blink_frame_limit = 2

# 거북목 기준 (사용자 피드백 반영: 12도 정상, 4도 거북목)
# 안전하게 6~7도 정도로 잡으면 좋습니다.
TURTLE_NECK_THRESHOLD = 7

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1) # 좌우 반전
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Mediapipe 처리
    face_result = face_mesh.process(rgb)
    pose_result = pose.process(rgb)

    # 1. 거북목 감지 (Pose)
    if pose_result.pose_landmarks:
        p_landmarks = pose_result.pose_landmarks.landmark
        
        # 왼쪽 귀(7)와 왼쪽 어깨(11) 추출
        ear_p = p_landmarks[7]
        shoulder_p = p_landmarks[11]

        # 각도 계산
        neck_angle = calculate_angle(shoulder_p, ear_p)

        # 상태 판별 및 출력
        color = (0, 255, 0) # 기본 녹색
        status_msg = "Good Posture"

        if neck_angle <= TURTLE_NECK_THRESHOLD:
            color = (0, 0, 255) # 거북목 시 빨간색
            status_msg = "TURTLE NECK DETECTED!"

        # 화면에 정보 표시
        cv2.putText(frame, f"Neck Angle: {int(neck_angle)} deg", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, status_msg, (30, 170),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        
        # 어깨와 귀 위치 시각화 (디버깅용)
        s_x, s_y = int(shoulder_p.x * w), int(shoulder_p.y * h)
        e_x, e_y = int(ear_p.x * w), int(ear_p.y * h)
        cv2.line(frame, (s_x, s_y), (e_x, e_y), color, 2)
        cv2.circle(frame, (s_x, s_y), 5, (255, 0, 0), -1)
        cv2.circle(frame, (e_x, e_y), 5, (255, 255, 0), -1)

    # 2. 눈 깜빡임 감지 (FaceMesh)
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

            # 눈 랜드마크 시각화
            for idx in LEFT_EYE + RIGHT_EYE:
                x = int(landmarks[idx].x * w)
                y = int(landmarks[idx].y * h)
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

    # 통합 정보 출력
    cv2.putText(frame, f"Blink Count: {blink_count}", (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    cv2.imshow("Smart Posture Monitor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()