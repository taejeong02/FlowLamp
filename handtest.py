import cv2
import mediapipe as mp
import math
import time

# --- 설정 ---
BLINK_THRESHOLD = 0.20    # 눈 감김 판단 기준 (필요시 0.18~0.22 사이 조정)
DROWSY_TIME_LIMIT = 5.0   # 5초 동안 감으면 졸음으로 판단

# --- MediaPipe 초기화 ---
mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# --- 유틸리티 함수 ---
def dist(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def get_ear(landmarks, eye_indices):
    vertical1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
    vertical2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
    horizontal = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
    return (vertical1 + vertical2) / (2.0 * horizontal)

def is_v_gesture(hand_landmarks):
    """검지, 중지가 펴지고 약지, 새끼가 접혔는지 확인"""
    landmarks = hand_landmarks.landmark
    
    # 손가락 끝(Tip)과 마디(MCP) Y좌표 비교 (Y값이 작을수록 화면 위쪽 = 펴짐)
    index_up = landmarks[8].y < landmarks[6].y
    middle_up = landmarks[12].y < landmarks[10].y
    ring_down = landmarks[16].y > landmarks[14].y
    pinky_down = landmarks[20].y > landmarks[18].y

    return index_up and middle_up and ring_down and pinky_down

# --- 눈 랜드마크 인덱스 ---
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# --- 상태 변수 ---
eyes_closed_start_time = 0
drowsy_detected = False

# --- 카메라 실행 ---
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1) # 거울 모드
    h, w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 1. 얼굴 인식 및 졸음 체크
    face_result = face_mesh.process(rgb_frame)
    if face_result.multi_face_landmarks:
        for face_landmarks in face_result.multi_face_landmarks:
            ear = get_ear(face_landmarks.landmark, LEFT_EYE + RIGHT_EYE) # 양안 평균
            
            if ear < BLINK_THRESHOLD:
                if eyes_closed_start_time == 0:
                    eyes_closed_start_time = time.time()
                elif time.time() - eyes_closed_start_time >= DROWSY_TIME_LIMIT:
                    drowsy_detected = True
            else:
                eyes_closed_start_time = 0
                drowsy_detected = False
            
            # EAR 값 화면 표시 (디버깅용)
            cv2.putText(frame, f"EAR: {ear:.2f}", (w-150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # 2. 손 인식 및 V자 체크
    hand_result = hands.process(rgb_frame)
    v_detected = False
    if hand_result.multi_hand_landmarks:
        for hand_landmarks in hand_result.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            if is_v_gesture(hand_landmarks):
                v_detected = True

    # 3. 화면 메시지 출력
    # 졸음 감지 시 빨간색 메시지
    if drowsy_detected:
        cv2.putText(frame, "sleeping!", (50, 100), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)
    
    # V자 인식 시 초록색 메시지
    if v_detected:
        cv2.putText(frame, "V hand!", (50, 180), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)

    cv2.imshow('Safety Monitor', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()