from ultralytics import YOLO
import cv2

model = YOLO("best_v1m.pt")

cap = cv2.VideoCapture("D:\\cntt\\Năm_3\\Thuc_Tap_Co_So\\ảnh_test\\video_stopline_2.mp4")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    results = model.track(frame, persist=True)

    annotated_frame = results[0].plot()
    annotated_frame = cv2.resize(annotated_frame, (1200, 900))

    cv2.imshow("Tracking", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()