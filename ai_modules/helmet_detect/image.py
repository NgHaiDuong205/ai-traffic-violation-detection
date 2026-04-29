from ultralytics import YOLO
import cv2
from tkinter import filedialog
import tkinter as tk
model = YOLO("D:/Thuc_tap_co_so/best3.pt")
root = tk.Tk()
root.withdraw()

image_path = filedialog.askopenfilename(
    title="Chọn ảnh",
    filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
)

if image_path:
    img = cv2.imread(image_path)

    if img is None:
        exit()

    # Predict
    results = model(img, conf=0.1)

    # Vẽ bounding box
    annotated_img = results[0].plot()
    annotated_img = cv2.resize(annotated_img, (800, 600))

    cv2.imshow("Helmet Detection", annotated_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    for box in results[0].boxes:
        cls  = int(box.cls)
        conf = float(box.conf)
        name = model.names[cls]
        print(f"Phát hiện: {name}  Độ tin cậy: {conf:.2f}")
