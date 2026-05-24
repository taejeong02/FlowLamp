import cv2
import numpy as np
import tensorflow as tf

MODEL_PATH = "keras_model.h5"
LABEL_PATH = "labels.txt"
IMG_SIZE = 224
CONFIDENCE_THRESHOLD = 0.70


def load_labels(label_path):
    labels = []
    with open(label_path, "r", encoding="utf-8") as f:
        for line in f:
            label = line.strip()
            if label:
                labels.append(label)
    return labels


def clean_label(label):
    parts = label.split()
    if len(parts) >= 2 and parts[0].isdigit():
        return " ".join(parts[1:])
    return label


def preprocess_image(frame):
    resized = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
    image = resized.astype(np.float32)
    image = (image / 127.5) - 1.0
    image = np.expand_dims(image, axis=0)
    return image


def to_korean(label):
    l = label.lower()

    if "open" in l:
        return "펴진 책"
    elif "closed" in l:
        return "덮힌 책"
    elif "no" in l:
        return "책 없음"
    else:
        return label


def main():
    print("1. AI 모델 로딩 시작")
    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    print("2. AI 모델 로딩 완료")

    labels = load_labels(LABEL_PATH)
    labels = [clean_label(label) for label in labels]
    print("3. 라벨 로딩 완료:", labels)

    print("4. 카메라 열기 시도")
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    print("5. 카메라 열기 성공")
    print("실시간 책 상태 인식 시작")
    print("종료하려면 q 키를 누르세요.")

    last_state = ""

    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break

        frame = cv2.flip(frame, 1)

        h, w, _ = frame.shape

        box_size = 300
        x1 = w // 2 - box_size // 2
        y1 = h // 2 - box_size // 2
        x2 = x1 + box_size
        y2 = y1 + box_size

        roi = frame[y1:y2, x1:x2]

        input_data = preprocess_image(roi)
        prediction = model.predict(input_data, verbose=0)[0]

        class_idx = int(np.argmax(prediction))
        confidence = float(prediction[class_idx])

        raw_label = labels[class_idx]
        result_label = to_korean(raw_label)

        if confidence < CONFIDENCE_THRESHOLD:
            result_label = "판별 중..."

        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

        main_text = f"{result_label} ({confidence * 100:.1f}%)"
        cv2.putText(
            frame,
            main_text,
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2
        )

        y_text = 80
        for i, prob in enumerate(prediction):
            label_text = to_korean(labels[i])
            line = f"{label_text}: {prob * 100:.1f}%"
            cv2.putText(
                frame,
                line,
                (20, y_text),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )
            y_text += 30

        cv2.imshow("ROI", roi)
        cv2.imshow("AI Book Classification", frame)

        if result_label != last_state:
            print(f"현재 상태: {result_label}, 신뢰도: {confidence * 100:.1f}%")
            last_state = result_label

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()