from ultralytics import YOLO
import cv2

model_vehicle = YOLO("D:/ai-traffic-violation-detection/ai_modules/best_v6.pt")
model_helmet  = YOLO("D:/ai-traffic-violation-detection/ai_modules/helmet_detect/weights/best3.pt")


VEHICLE_COLOR = (0, 255, 0)
HELMET_COLOR  = (0, 0, 255)
HELMET_OK     = (255, 128, 0)

def detect_combined(source):
    cap = cv2.VideoCapture(source)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results_vehicle = model_vehicle(frame, conf=0.4, verbose=False)[0]
        results_helmet  = model_helmet(frame,  conf=0.4, verbose=False)[0]
        for box in results_vehicle.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = f"{model_vehicle.names[cls_id]} {conf:.2f}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), VEHICLE_COLOR, 2)
            cv2.putText(frame, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, VEHICLE_COLOR, 2)

        for box in results_helmet.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls_id = int(box.cls[0])
            conf   = float(box.conf[0])
            label  = f"{model_helmet.names[cls_id]} {conf:.2f}"
            # Màu khác nhau tuỳ có/không có mũ
            color = HELMET_OK if model_helmet.names[cls_id] == "helmet" else HELMET_COLOR
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        cv2.imshow("Vehicle + Helmet Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


detect_combined("D:/Thuc_tap_co_so/videoplayback.mp4")