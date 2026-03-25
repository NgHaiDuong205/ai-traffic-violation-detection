from ultralytics import YOLO
import cv2
from tkinter import filedialog
import tkinter as tk

# Load model
model = YOLO("D:/Thuc_tap_co_so/best3.pt")

# Chọn ảnh
root = tk.Tk()
root.withdraw()

image_path = filedialog.askopenfilename(
    title="Chọn ảnh",
    filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
)

if image_path:
    # Đọc ảnh bằng OpenCV
    img = cv2.imread(image_path)

    if img is None:
        print("Không đọc được ảnh!")
        exit()

    # Predict
    results = model(img, conf=0.25)

    # Vẽ bounding box
    annotated_img = results[0].plot()

    # Resize cho vừa màn hình (tránh ảnh quá to)
    annotated_img = cv2.resize(annotated_img, (800, 600))

    # Hiển thị ảnh
    cv2.imshow("Helmet Detection", annotated_img)

    # Nhấn phím bất kỳ để thoát
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # In kết quả ra console
    for box in results[0].boxes:
        cls  = int(box.cls)
        conf = float(box.conf)
        name = model.names[cls]
        print(f"Phát hiện: {name} - Độ tin cậy: {conf:.2f}")

else:
    print("Chưa chọn ảnh!")