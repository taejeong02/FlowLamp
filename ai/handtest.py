import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flowlamp_rpi.devices.motor import MotorController
from ai.booktest import BookClassifier

# --- 설정 ---
BLINK_THRESHOLD = 0.20
DROWSY_TIME_LIMIT = 5.0

DEAD_ZONE_XY = 40
DEAD_ZONE_Z = 25
MOTOR_ENABLED = os.environ.get("HAND_MOTOR_ENABLED", "1") != "0"
MOTOR_MAX_SPEED = int(os.environ.get("HAND_MOTOR_MAX_SPEED", "10"))
MOTOR_SPEED = min(int(os.environ.get("HAND_MOTOR_SPEED", "8")), MOTOR_MAX_SPEED)
MOTOR_COMMAND_INTERVAL = float(os.environ.get("HAND_MOTOR_COMMAND_INTERVAL", "0.14"))
MOTOR_AXIS_CHANGE_THRESHOLD = float(os.environ.get("HAND_MOTOR_AXIS_CHANGE_THRESHOLD", "0.05"))
MOTOR_Z_DEAD_ZONE_RATIO = float(os.environ.get("HAND_MOTOR_Z_DEAD_ZONE_RATIO", "0.08"))
MOTOR_Z_SENSITIVITY = float(os.environ.get("HAND_MOTOR_Z_SENSITIVITY", "3.0"))
MOTOR_Z_INVERT = os.environ.get("HAND_MOTOR_Z_INVERT", "0") == "1"
FLOWLAMP_API_URL = os.environ.get("FLOWLAMP_API_URL", "http://127.0.0.1:8000")
FLOWLAMP_API_TIMEOUT = float(os.environ.get("FLOWLAMP_API_TIMEOUT", "0.25"))

BRIGHTNESS_MIN = 0
BRIGHTNESS_MAX = 100
BRIGHTNESS_LEVEL = 50
ROTATION_BRIGHTNESS_THRESHOLD = 12
ROTATION_BRIGHTNESS_STEP = 10
ROTATION_HISTORY_SIZE = 6
ROTATION_STABLE_FRAMES = 4
FIST_SCORE_THRESHOLD = 1.00
FINGER_STRAIGHT_ANGLE = 150.0
FINGER_EXTENSION_RATIO = 1.05
CAMERA_INDEX = os.environ.get("CAMERA_INDEX", "0")
CAMERA_WIDTH = int(os.environ.get("CAMERA_WIDTH", "640"))
CAMERA_HEIGHT = int(os.environ.get("CAMERA_HEIGHT", "480"))
CAMERA_FPS = int(os.environ.get("CAMERA_FPS", "15"))
BOOK_DETECTION_ENABLED = os.environ.get("BOOK_DETECTION_ENABLED", "1") != "0"
BOOK_ACTIVATION_DELAY = float(os.environ.get("BOOK_ACTIVATION_DELAY", "0.5"))
BOOK_INFERENCE_INTERVAL = float(os.environ.get("BOOK_INFERENCE_INTERVAL", "0.3"))

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

def dist_3d(p1, p2):
    return math.sqrt(
        (p1.x - p2.x) ** 2
        + (p1.y - p2.y) ** 2
        + (p1.z - p2.z) ** 2
    )

def joint_angle_3d(p1, vertex, p2):
    v1 = (p1.x - vertex.x, p1.y - vertex.y, p1.z - vertex.z)
    v2 = (p2.x - vertex.x, p2.y - vertex.y, p2.z - vertex.z)
    norm1 = math.sqrt(sum(value * value for value in v1))
    norm2 = math.sqrt(sum(value * value for value in v2))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    cosine = sum(a * b for a, b in zip(v1, v2)) / (norm1 * norm2)
    return math.degrees(math.acos(clamp(cosine)))

def is_finger_extended(lm, mcp_idx, pip_idx, dip_idx, tip_idx):
    pip_angle = joint_angle_3d(lm[mcp_idx], lm[pip_idx], lm[dip_idx])
    dip_angle = joint_angle_3d(lm[pip_idx], lm[dip_idx], lm[tip_idx])
    tip_distance = dist_3d(lm[0], lm[tip_idx])
    pip_distance = dist_3d(lm[0], lm[pip_idx])

    return (
        pip_angle >= FINGER_STRAIGHT_ANGLE
        and dip_angle >= FINGER_STRAIGHT_ANGLE
        and tip_distance >= pip_distance * FINGER_EXTENSION_RATIO
    )

def get_finger_states(hand_landmarks):
    lm = hand_landmarks.landmark
    return {
        "index": is_finger_extended(lm, 5, 6, 7, 8),
        "middle": is_finger_extended(lm, 9, 10, 11, 12),
        "ring": is_finger_extended(lm, 13, 14, 15, 16),
        "pinky": is_finger_extended(lm, 17, 18, 19, 20),
    }

def get_ear(landmarks, eye_indices):
    try:
        v1 = dist(landmarks[eye_indices[1]], landmarks[eye_indices[5]])
        v2 = dist(landmarks[eye_indices[2]], landmarks[eye_indices[4]])
        h = dist(landmarks[eye_indices[0]], landmarks[eye_indices[3]])
        return (v1 + v2) / (2.0 * h)
    except:
        return 0.3

def is_v_gesture(hand_landmarks):
    fingers = get_finger_states(hand_landmarks)
    return (
        fingers["index"]
        and fingers["middle"]
        and not fingers["ring"]
        and not fingers["pinky"]
    )

def is_open_palm(hand_landmarks):
    return all(get_finger_states(hand_landmarks).values())

def get_palm_center(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark
    palm_indices = [0, 5, 9, 13, 17]
    center_x = sum(lm[index].x for index in palm_indices) / len(palm_indices)
    center_y = sum(lm[index].y for index in palm_indices) / len(palm_indices)
    return int(center_x * frame_w), int(center_y * frame_h)

def get_hand_size(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark
    scale = (frame_w + frame_h) / 2
    palm_lengths = [
        dist_3d(lm[0], lm[9]) * scale,
        dist_3d(lm[5], lm[17]) * scale,
    ]
    return sum(palm_lengths) / len(palm_lengths)

def get_fist_score(hand_landmarks, frame_w, frame_h):
    lm = hand_landmarks.landmark

    palm_x = (lm[0].x + lm[5].x + lm[9].x + lm[13].x + lm[17].x) / 5 * frame_w
    palm_y = (lm[0].y + lm[5].y + lm[9].y + lm[13].y + lm[17].y) / 5 * frame_h
    hand_size = max(get_hand_size(hand_landmarks, frame_w, frame_h), 1)

    tip_distances = []
    for tip_idx in [8, 12, 16, 20]:
        tip_x = lm[tip_idx].x * frame_w
        tip_y = lm[tip_idx].y * frame_h
        tip_distances.append(math.hypot(tip_x - palm_x, tip_y - palm_y))

    return sum(tip_distances) / len(tip_distances) / hand_size

def is_closed_fist(hand_landmarks, frame_w, frame_h):
    return get_fist_score(hand_landmarks, frame_w, frame_h) < FIST_SCORE_THRESHOLD

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

    index_base = lm[5]
    pinky_base = lm[17]

    dx = pinky_base.x - index_base.x
    dy = pinky_base.y - index_base.y

    angle = math.degrees(math.atan2(dy, dx))

    if angle > 90:
        angle -= 180
    elif angle < -90:
        angle += 180

    return angle

def clamp(value, min_value=-1.0, max_value=1.0):
    return max(min_value, min(max_value, value))

def error_to_axis(error, dead_zone, max_error):
    if abs(error) <= dead_zone:
        return 0.0

    usable_range = max(max_error - dead_zone, 1)
    direction = 1.0 if error > 0 else -1.0
    magnitude = (abs(error) - dead_zone) / usable_range
    return clamp(direction * magnitude)

def hand_size_to_z_axis(hand_size, base_size):
    if base_size <= 0:
        return 0.0

    ratio_delta = (hand_size - base_size) / base_size
    if abs(ratio_delta) <= MOTOR_Z_DEAD_ZONE_RATIO:
        return 0.0

    direction = -1.0 if MOTOR_Z_INVERT else 1.0
    return clamp(direction * ratio_delta * MOTOR_Z_SENSITIVITY)

def should_send_motor_command(current, previous, last_sent_time):
    if previous is None:
        return True

    if time.time() - last_sent_time < MOTOR_COMMAND_INTERVAL:
        return False

    return any(
        abs(current_value - previous_value) >= MOTOR_AXIS_CHANGE_THRESHOLD
        for current_value, previous_value in zip(current, previous)
    )

def send_brightness_gesture(gesture):
    global last_api_error_time

    payload = json.dumps({"gesture": gesture}).encode("utf-8")
    request = urllib.request.Request(
        f"{FLOWLAMP_API_URL}/vision/gesture",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=FLOWLAMP_API_TIMEOUT) as response:
            body = response.read().decode("utf-8")
            return json.loads(body).get("brightness")
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        now = time.time()
        if now - last_api_error_time >= 3:
            print(f"FlowLamp API gesture send failed: {exc}")
            last_api_error_time = now
        return None

LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

eyes_closed_start_time = 0
drowsy_detected = False

base_hand_size = 0
fist_rotation_history = []
fist_rotation_reference = None
last_motor_vector = None
last_motor_command_time = 0.0
last_api_error_time = 0.0
motor_controller = MotorController() if MOTOR_ENABLED else None
book_classifier = None
book_result = None
last_book_inference_time = 0.0
no_hand_start_time = None
last_book_state = None

class PrefetchedCapture:
    def __init__(self, cap, first_frame):
        self.cap = cap
        self.first_frame = first_frame

    def isOpened(self):
        return self.cap.isOpened()

    def read(self):
        if self.first_frame is not None:
            frame = self.first_frame
            self.first_frame = None
            return True, frame
        return self.cap.read()

    def release(self):
        self.cap.release()


def get_video_indices():
    if CAMERA_INDEX.lower() != "auto":
        return [int(CAMERA_INDEX)]

    if not os.path.isdir("/dev"):
        return [1]

    indices = []
    for name in os.listdir("/dev"):
        if name.startswith("video") and name[5:].isdigit():
            indices.append(int(name[5:]))
    return sorted(indices)


def try_open_v4l2_camera(index):
    cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            return PrefetchedCapture(cap, frame)

    cap.release()
    return None


def open_camera():
    working_cameras = []

    for index in get_video_indices():
        cap = try_open_v4l2_camera(index)
        if cap is not None:
            working_cameras.append((index, cap))

    if working_cameras:
        selected_index, selected_cap = working_cameras[-1]
        if CAMERA_INDEX.lower() == "auto" and len(working_cameras) >= 2:
            selected_index, selected_cap = working_cameras[1]

        for index, cap in working_cameras:
            if cap is not selected_cap:
                cap.release()

        print(f"Camera opened: index={selected_index}, backend=V4L2")
        return selected_cap

    video_devices = [f"/dev/video{index}" for index in get_video_indices()]

    print("ERROR: V4L2 카메라를 열 수 없습니다.")
    if video_devices:
        print("감지된 video 장치:", ", ".join(video_devices))
        print("직접 지정하려면 예: CAMERA_INDEX=2 python ai/handtest.py")
        print("자동 탐색하려면 예: CAMERA_INDEX=auto python ai/handtest.py")
    else:
        print("/dev/video* 장치가 없습니다. 카메라 연결을 확인하세요.")
    raise SystemExit(1)


cap = open_camera()

try:
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        frame_h, frame_w, _ = frame.shape

        center_x = frame_w // 2
        center_y = frame_h // 2

        cv2.circle(frame, (center_x, center_y), 8, (0, 255, 255), -1)
        cv2.line(frame, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 255), 2)
        cv2.line(frame, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 255), 2)

        face_result = face_mesh.process(rgb_frame)

        if face_result.multi_face_landmarks:
            for face_landmarks in face_result.multi_face_landmarks:
                left_ear = get_ear(face_landmarks.landmark, LEFT_EYE)
                right_ear = get_ear(face_landmarks.landmark, RIGHT_EYE)
                ear = (left_ear + right_ear) / 2.0

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

        hand_result = hands.process(rgb_frame)
        hand_detected = bool(hand_result.multi_hand_landmarks)

        v_detected = False
        palm_detected = False
        fist_detected = False

        if hand_detected:
            no_hand_start_time = None
            book_result = None

            for hand_landmarks in hand_result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                lm = hand_landmarks.landmark

                if is_v_gesture(hand_landmarks):
                    v_detected = True

                rotation_angle = get_hand_rotation(hand_landmarks)

                fist_score = get_fist_score(hand_landmarks, frame_w, frame_h)
                current_fist_detected = fist_score < FIST_SCORE_THRESHOLD

                cv2.putText(frame, f"Fist score: {fist_score:.2f} / {FIST_SCORE_THRESHOLD:.2f}", (20, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)

                if current_fist_detected:
                    fist_detected = True
                    fist_rotation_history.append(rotation_angle)

                    if len(fist_rotation_history) > ROTATION_HISTORY_SIZE:
                        fist_rotation_history.pop(0)
                else:
                    fist_rotation_history.clear()
                    fist_rotation_reference = None

                if not current_fist_detected and is_open_palm(hand_landmarks):
                    palm_detected = True

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
                        brightness_msg = f"RIGHT TURN: BRIGHTNESS UP {int(delta_angle)} deg"
                    elif delta_angle < -ROTATION_BRIGHTNESS_THRESHOLD:
                        brightness_msg = f"LEFT TURN: BRIGHTNESS DOWN {int(abs(delta_angle))} deg"
                    else:
                        brightness_msg = "BRIGHTNESS HOLD"

                if palm_detected:
                    hand_x, hand_y = get_palm_center(
                        hand_landmarks,
                        frame_w,
                        frame_h,
                    )

                    error_x = hand_x - center_x
                    error_y = hand_y - center_y

                    move_x, move_y = get_tracking_command(error_x, error_y)

                    hand_size = get_hand_size(hand_landmarks, frame_w, frame_h)

                    if base_hand_size == 0:
                        base_hand_size = hand_size

                    error_z = hand_size - base_hand_size
                    move_z = get_depth_command(error_z)

                    motor_x = error_to_axis(error_x, DEAD_ZONE_XY, frame_w / 2)
                    motor_y = -error_to_axis(-error_y, DEAD_ZONE_XY, frame_h / 2)
                    motor_z = hand_size_to_z_axis(hand_size, base_hand_size)
                    motor_vector = (motor_x, motor_y, motor_z)
                    motor_3_velocity = round(motor_z * MOTOR_SPEED)

                    if motor_controller and should_send_motor_command(
                        motor_vector,
                        last_motor_vector,
                        last_motor_command_time,
                    ):
                        motor_controller.move_xyz(
                            x=motor_x,
                            y=motor_y,
                            z=motor_z,
                            speed=MOTOR_SPEED,
                        )
                        last_motor_vector = motor_vector
                        last_motor_command_time = time.time()

                    cv2.circle(frame, (hand_x, hand_y), 10, (255, 0, 0), -1)
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

                    cv2.putText(frame, f"XYZ: {motor_x:.2f}, {motor_y:.2f}, {motor_z:.2f}", (50, 595),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

                    cv2.putText(frame, f"Motor 3 velocity: {motor_3_velocity}", (50, 630),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

                if fist_detected and fist_rotation_reference is not None and len(fist_rotation_history) >= ROTATION_STABLE_FRAMES:
                    delta_angle = smooth_rotation - fist_rotation_reference

                    if delta_angle > ROTATION_BRIGHTNESS_THRESHOLD:
                        delta = ROTATION_BRIGHTNESS_STEP
                        if BRIGHTNESS_LEVEL < BRIGHTNESS_MAX:
                            api_brightness = send_brightness_gesture("brightness_up")
                            if api_brightness is None:
                                BRIGHTNESS_LEVEL = min(BRIGHTNESS_MAX, BRIGHTNESS_LEVEL + delta)
                            else:
                                BRIGHTNESS_LEVEL = min(BRIGHTNESS_MAX, api_brightness)
                        fist_rotation_reference = smooth_rotation

                    elif delta_angle < -ROTATION_BRIGHTNESS_THRESHOLD:
                        delta = ROTATION_BRIGHTNESS_STEP
                        if BRIGHTNESS_LEVEL > BRIGHTNESS_MIN:
                            api_brightness = send_brightness_gesture("brightness_down")
                            if api_brightness is None:
                                BRIGHTNESS_LEVEL = max(BRIGHTNESS_MIN, BRIGHTNESS_LEVEL - delta)
                            else:
                                BRIGHTNESS_LEVEL = max(BRIGHTNESS_MIN, api_brightness)
                        fist_rotation_reference = smooth_rotation

                if fist_detected:
                    if fist_rotation_reference is not None:
                        delta_angle = smooth_rotation - fist_rotation_reference

                        cv2.putText(frame, "FIST DETECTED", (50, 160),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

                        cv2.putText(frame, f"Rotation Delta: {int(delta_angle)} deg", (50, 195),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

                        cv2.putText(frame, f"Reference Angle: {int(fist_rotation_reference)} deg", (50, 230),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 200, 0), 2)

                        y_offset = 265
                    else:
                        y_offset = 195
                        cv2.putText(frame, "FIST DETECTED", (50, 160),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

                    cv2.putText(frame, brightness_msg, (50, y_offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)

                    cv2.putText(frame, f"Brightness: {BRIGHTNESS_LEVEL}%", (50, y_offset + 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
        elif BOOK_DETECTION_ENABLED:
            if no_hand_start_time is None:
                no_hand_start_time = time.time()

            no_hand_elapsed = time.time() - no_hand_start_time
            if no_hand_elapsed >= BOOK_ACTIVATION_DELAY:
                if book_classifier is None:
                    try:
                        book_classifier = BookClassifier()
                    except Exception as exc:
                        print(f"Book AI initialization failed: {exc}")
                        BOOK_DETECTION_ENABLED = False

                now = time.time()
                if (
                    book_classifier is not None
                    and now - last_book_inference_time >= BOOK_INFERENCE_INTERVAL
                ):
                    try:
                        book_result = book_classifier.classify(frame)
                        last_book_inference_time = now
                    except Exception as exc:
                        print(f"Book AI inference failed: {exc}")
                        BOOK_DETECTION_ENABLED = False
                        book_result = None

                    if (
                        book_result is not None
                        and book_result["label"] != last_book_state
                    ):
                        print(
                            f"Book state: {book_result['label']}, "
                            f"confidence: {book_result['confidence'] * 100:.1f}%"
                        )
                        last_book_state = book_result["label"]

                if book_classifier is not None and book_result is not None:
                    book_classifier.draw_result(frame, book_result)
                    cv2.putText(
                        frame,
                        "BOOK DETECTION MODE",
                        (20, frame_h - 20),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.8,
                        (255, 255, 0),
                        2,
                    )
            else:
                cv2.putText(
                    frame,
                    "Waiting for hand...",
                    (50, 180),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 200),
                    2,
                )

        if not palm_detected:
            base_hand_size = 0
            if motor_controller and last_motor_vector != (0.0, 0.0, 0.0):
                motor_controller.stop()
                last_motor_vector = (0.0, 0.0, 0.0)
                last_motor_command_time = time.time()

        if drowsy_detected:
            cv2.putText(frame, "SLEEPING ALERT!", (50, 100),
                        cv2.FONT_HERSHEY_DUPLEX, 1.2, (0, 0, 255), 3)

        if v_detected:
            cv2.putText(frame, "V GESTURE!", (50, 130),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 2)

        if hand_detected and not palm_detected and not fist_detected:
            cv2.putText(frame, "Show Open Palm to Track / Fist to Control Brightness", (50, 180),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        cv2.imshow("Safety Monitor", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    if motor_controller:
        try:
            motor_controller.stop()
        except RuntimeError as exc:
            print(f"모터 정지 실패: {exc}")
        motor_controller.close()

    cap.release()
    cv2.destroyAllWindows()
    face_mesh.close()
    hands.close()
