from ultralytics import YOLO
import cv2

# 1. Load model của bạn
model = YOLO('best_v4.pt')

# 2. Chạy dự đoán trên một ảnh
#results = model.predict(source='D:\\cntt\\Năm_3\\Thuc_Tap_Co_So\\anh5.jpg', 
#                        conf=0.1,  # Ngưỡng tin cậy
 #                       )
results = model('D:\\cntt\\Năm_3\\Thuc_Tap_Co_So\\anh5.jpg')
# 3. Hiển thị kết quả
for r in results:
    im_array = r.plot()  # Vẽ bounding box lên ảnh
    im_array = cv2.resize(im_array, (1200, 800))
    cv2.imshow('YOLO Result', im_array)
    cv2.waitKey(0) # Nhấn phím bất kỳ để đóng

cv2.destroyAllWindows()