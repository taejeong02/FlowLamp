import cv2
import numpy as np

def main():
    cap = cv2.VideoCapture(0)
    
    # 카메라가 대각선일 때 에지가 잘 끊기므로 해상도를 적절히 유지합니다.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("대각선 각도 & 펼친 책 인식 모드 실행 중...")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. 전처리: 그레이스케일 -> 강한 블러 (노이즈 제거)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (11, 11), 0)

        # 2. 에지 검출 후 '팽창(Dilate)' 처리
        # 대각선 각도에서는 선이 가늘게 보이므로, 선을 굵게 만들어 하나로 합칩니다.
        edged = cv2.Canny(blurred, 30, 150)
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(edged, kernel, iterations=2)

        # 3. 윤곽선 찾기
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        target_contour = None
        max_area = 0

        for c in contours:
            area = cv2.contourArea(c)
            # 화면의 최소 10% 이상은 차지해야 책으로 간주 (오인식 방지)
            if area < 20000: continue 

            # 4. [핵심] Convex Hull (볼록 선체) 적용
            # 펼친 책의 굴곡진 부분을 무시하고 전체를 감싸는 외곽선을 만듭니다.
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            
            # 5. 밀도(Solidity) 및 가로세로비 체크
            # 대각선에서 봐도 책은 덩어리감이 있어야 함
            solidity = float(area) / hull_area if hull_area > 0 else 0
            
            if solidity > 0.6: # 60% 이상 채워진 덩어리라면
                if area > max_area:
                    max_area = area
                    target_contour = hull

        # 6. 최종 결과 표시
        if target_contour is not None:
            # 인식된 덩어리 그리기
            cv2.drawContours(frame, [target_contour], -1, (255, 0, 0), 3)
            
            # 중심점 계산하여 메세지 표시
            M = cv2.moments(target_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                
                cv2.putText(frame, "Book Detected!", (cx-50, cy), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                # 터미널 출력
                print("책인식!")

        # 디버깅용: 컴퓨터가 보고 있는 '선'의 상태 확인
        cv2.imshow("Original", frame)
        cv2.imshow("Process(Dilated)", dilated) 

        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()