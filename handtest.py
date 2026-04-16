import cv2
import mediapipe as mp
import math
import time

# --- 설정 ---
BLINK_THRESHOLD = 0.20
DROWSY_TIME_LIMIT = 5.0

mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# 텐서플로우 2.15와 혼선 방지를 위한 설정
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1, # 2개에서 1개로 줄여 성능 확보
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
    # V자: 검지(8)와 중지(12)는 펴지고, 약지(16)와 새끼(20)는 접힘
    # y값 비교 (작을수록 위쪽)
    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_down = lm[16].y > lm[14].y
    pinky_down = lm[20].y > lm[18].y
    return index_up and middle_up and ring_down and pinky_down

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

eyes_closed_start_time = 0
drowsy_detected = False

cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

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
            
            cv2.putText(frame, f"EAR: {ear:.2f}", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    # 2. 손 V자 체크
    hand_result = hands.process(rgb_frame)
    v_detected = False
    if hand_result.multi_hand_landmarks:
        for hand_landmarks in hand_result.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            if is_v_gesture(hand_landmarks):
                v_detected = True

    # 3. 출력
    if drowsy_detected:
        cv2.putText(frame, "SLEEPING ALERT!", (50, 100), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)
    if v_detected:
        cv2.putText(frame, "V GESTURE!", (50, 180), cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 255, 0), 3)

    cv2.imshow('Safety Monitor', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
face_mesh.close()
hands.close()