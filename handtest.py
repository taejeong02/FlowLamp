import cv2
import mediapipe as mp
import math
import time

# --- 설정 ---
BLINK_THRESHOLD = 0.20
DROWSY_TIME_LIMIT = 5.0
DEAD_ZONE = 40  # 중앙 기준 허용 오차(px)

mp_face_mesh = mp.solutions.face_mesh
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
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

# 손바닥 펼침 인식
def is_open_palm(hand_landmarks):
    lm = hand_landmarks.landmark

    index_up = lm[8].y < lm[6].y
    middle_up = lm[12].y < lm[10].y
    ring_up = lm[16].y < lm[14].y
    pinky_up = lm[20].y < lm[18].y

    return index_up and middle_up and ring_up and pinky_up

# 화면 중앙 기준 이동 명령 계산
def get_tracking_command(error_x, error_y):
    move_x = "STOP"
    move_y = "STOP"

    if error_x > DEAD_ZONE:
        move_x = f"RIGHT {abs(error_x)}px"
    elif error_x < -DEAD_ZONE:
        move_x = f"LEFT {abs(error_x)}px"

    if error_y > DEAD_ZONE:
        move_y = f"DOWN {abs(error_y)}px"
    elif error_y < -DEAD_ZONE:
        move_y = f"UP {abs(error_y)}px"

    return move_x, move_y

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

eyes_closed_start_time = 0
drowsy_detected = False

cap = cv2.VideoCapture(0)

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

    if hand_result.multi_hand_landmarks:
        for hand_landmarks in hand_result.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            lm = hand_landmarks.landmark

            # V 제스처 체크
            if is_v_gesture(hand_landmarks):
                v_detected = True

            # 손바닥 펼침 체크
            if is_open_palm(hand_landmarks):
                palm_detected = True

                # 손바닥 중심 좌표: 9번 랜드마크 사용
                hand_x = int(lm[9].x * frame_w)
                hand_y = int(lm[9].y * frame_h)

                error_x = hand_x - center_x
                error_y = hand_y - center_y

                move_x, move_y = get_tracking_command(error_x, error_y)

                # 손 중심점 표시
                cv2.circle(frame, (hand_x, hand_y), 10, (255, 0, 0), -1)

                # 중앙점과 손 중심점 연결선
                cv2.line(frame, (center_x, center_y), (hand_x, hand_y), (255, 255, 0), 2)

                cv2.putText(frame, "OPEN PALM TRACKING", (50, 180),
                            cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 0), 2)

                cv2.putText(frame, f"Hand Center: ({hand_x}, {hand_y})", (50, 220),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.putText(frame, f"Screen Center: ({center_x}, {center_y})", (50, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.putText(frame, f"Error X: {error_x}px", (50, 290),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                cv2.putText(frame, f"Error Y: {error_y}px", (50, 320),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                cv2.putText(frame, f"Motor X: {move_x}", (50, 365),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)

                cv2.putText(frame, f"Motor Y: {move_y}", (50, 400),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 255), 2)

    # 3. 출력
    if drowsy_detected:
        cv2.putText(frame, "SLEEPING ALERT!", (50, 100),
                    cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)

    if v_detected:
        cv2.putText(frame, "V GESTURE!", (50, 140),
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