from ultralytics import YOLO
import cv2

# Load model
model = YOLO("D:/Thuc_tap_co_so/best3.pt")

# Mở webcam
cap = cv2.VideoCapture(0)  # 0 là webcam mặc định

if not cap.isOpened():
    print("Không mở được webcam!")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Resize để tăng tốc
    frame = cv2.resize(frame, (640, 480))

    # Predict (mỗi frame)
    results = model(frame, conf=0.25, imgsz=320)  # imgsz nhỏ → nhanh hơn

    # Vẽ box lên frame
    annotated_frame = results[0].plot()

    # Hiển thị
    cv2.imshow("Helmet Detection - Webcam", annotated_frame)

    # Nhấn 'q' để thoát
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()