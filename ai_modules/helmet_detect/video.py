from ultralytics import YOLO
import cv2
from tkinter import filedialog
import tkinter as tk

# Load model
model = YOLO("D:/Thuc_tap_co_so/best3.pt")

# Chọn video
root = tk.Tk()
root.withdraw()

video_path = filedialog.askopenfilename(
    title="Chọn video",
    filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
)

if video_path:
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Không mở được video!")
        exit()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize cho nhanh hơn
        frame = cv2.resize(frame, (640, 480))

        # Predict (cách nhanh)
        results = model(frame, conf=0.25, imgsz=320)

        # Vẽ box
        annotated_frame = results[0].plot()

        # Hiển thị
        cv2.imshow("Helmet Detection - Video", annotated_frame)

        # Nhấn 'q' để thoát
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

else:
    print("Chưa chọn video!")