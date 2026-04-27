from ultralytics import YOLO
import cv2
from tkinter import filedialog
import tkinter as tk

model = YOLO("D:/ai-traffic-violation-detection/ai_modules/helmet_detect/weights/best3.pt")
root = tk.Tk()
root.withdraw()

video_path = filedialog.askopenfilename(
    title="Chọn video",
    filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
)

if video_path:
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        exit()
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.resize(frame, (640, 480))
        results = model(frame, conf=0.25, imgsz=320)
        annotated_frame = results[0].plot()
        cv2.imshow("Helmet Detection - Video", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()