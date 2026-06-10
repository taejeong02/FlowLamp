from pathlib import Path

import cv2
import numpy as np

AI_DIR = Path(__file__).resolve().parent
MODEL_PATH = AI_DIR / "keras_model.h5"
LABEL_PATH = AI_DIR / "labels.txt"
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


def to_display_label(label):
    l = label.lower()

    if "open" in l:
        return "Open Book"
    elif "closed" in l:
        return "Closed Book"
    elif "no" in l:
        return "No Book"
    else:
        return label


class BookClassifier:
    def __init__(
        self,
        model_path=MODEL_PATH,
        label_path=LABEL_PATH,
        confidence_threshold=CONFIDENCE_THRESHOLD,
    ):
        import tf_keras

        class CompatibleDepthwiseConv2D(tf_keras.layers.DepthwiseConv2D):
            def __init__(self, *args, groups=None, **kwargs):
                super().__init__(*args, **kwargs)

        print("Book AI model loading...")
        self.model = tf_keras.models.load_model(
            model_path,
            compile=False,
            custom_objects={
                "DepthwiseConv2D": CompatibleDepthwiseConv2D,
            },
        )
        self.labels = [
            clean_label(label)
            for label in load_labels(label_path)
        ]
        self.confidence_threshold = confidence_threshold
        print("Book AI model loaded:", self.labels)

    def classify(self, frame):
        h, w, _ = frame.shape
        box_size = min(300, h, w)
        x1 = w // 2 - box_size // 2
        y1 = h // 2 - box_size // 2
        x2 = x1 + box_size
        y2 = y1 + box_size
        roi = frame[y1:y2, x1:x2]

        input_data = preprocess_image(roi)
        prediction = self.model.predict(input_data, verbose=0)[0]
        class_idx = int(np.argmax(prediction))
        confidence = float(prediction[class_idx])
        raw_label = self.labels[class_idx]
        result_label = to_display_label(raw_label)

        if confidence < self.confidence_threshold:
            result_label = "Detecting..."

        return {
            "label": result_label,
            "confidence": confidence,
            "prediction": prediction,
            "box": (x1, y1, x2, y2),
        }

    def draw_result(self, frame, result, origin=(20, 40)):
        x1, y1, x2, y2 = result["box"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 0), 2)

        text_x, text_y = origin
        main_text = f"{result['label']} ({result['confidence'] * 100:.1f}%)"
        cv2.putText(
            frame,
            main_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
        )

        for index, probability in enumerate(result["prediction"]):
            text_y += 30
            line = (
                f"{to_display_label(self.labels[index])}: "
                f"{probability * 100:.1f}%"
            )
            cv2.putText(
                frame,
                line,
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )


def main():
    classifier = BookClassifier()

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

        result = classifier.classify(frame)
        classifier.draw_result(frame, result)
        cv2.imshow("AI Book Classification", frame)

        if result["label"] != last_state:
            print(
                f"현재 상태: {result['label']}, "
                f"신뢰도: {result['confidence'] * 100:.1f}%"
            )
            last_state = result["label"]

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
