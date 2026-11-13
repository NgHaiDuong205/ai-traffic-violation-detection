# AI Traffic Violation Detection

Hệ thống phát hiện vi phạm giao thông bằng AI, gồm hai loại vi phạm:

- **Không đội mũ bảo hiểm**: phát hiện trên ảnh và video.
- **Vượt đèn đỏ**: phát hiện trên video, dựa trên vạch dừng do người dùng tự vẽ và đèn giao thông mô phỏng (xanh/đỏ luân phiên).

Dự án gồm backend **FastAPI** chạy mô hình **YOLO (Ultralytics)** và frontend **React** để upload, xem kết quả theo thời gian thực qua WebSocket và xuất danh sách vi phạm ra CSV.

> Tài liệu thiết kế chi tiết (kiến trúc, luồng dữ liệu, thuật toán): [THIET_KE_HE_THONG.md](THIET_KE_HE_THONG.md)

---

## Tính năng

- Upload **ảnh** → nhận ảnh đã đánh dấu và danh sách người không đội mũ bảo hiểm.
- Upload **video** → vẽ vạch dừng trên khung hình đầu tiên → xử lý video, kết quả được stream về trình duyệt theo từng lô khung hình.
- Theo dõi đối tượng (tracking) qua các khung hình, dùng **điểm vi phạm tích lũy** để giảm báo nhầm khi phát hiện mũ bảo hiểm.
- **Loại bỏ vi phạm trùng lặp** khi tracker đổi ID hoặc các box chồng lấn nhau (theo IoU, khoảng cách tâm và cửa sổ thời gian).
- Đếm phương tiện theo loại (ô tô, xe buýt, xe tải, xe máy, xe đạp).
- Bảng ghi nhận vi phạm, tải về file **CSV** (UTF-8, mở được bằng Excel).

## Kiến trúc

```
┌───────────────────────┐   HTTP / WebSocket   ┌────────────────────────┐
│  React (web/)         │ ───────────────────▶ │  FastAPI (backend/)    │
│  - Upload ảnh/video   │                      │  - REST + WebSocket    │
│  - Vẽ vạch dừng       │ ◀─────────────────── │  - Tracking, dedupe    │
│  - Hiển thị vi phạm   │  frame_batch, kết quả│  - Mô phỏng đèn đỏ     │
└───────────────────────┘                      └───────────┬────────────┘
                                                           │
                                               ┌───────────▼────────────┐
                                               │  YOLO (ai_modules/)    │
                                               │  - best3.pt  (mũ BH)   │
                                               │  - best_v6.pt (xe)     │
                                               └────────────────────────┘
```

## Cấu trúc thư mục

```
ai-traffic-violation-detection/
├── ai_modules/
│   ├── helmet_detect/
│   │   ├── training/            # Notebook huấn luyện + data.yaml.example
│   │   └── weights/best3.pt     # Mô hình phát hiện mũ bảo hiểm
│   └── vehicle_detect/
│       ├── training/            # Notebook huấn luyện + data.yaml.example
│       └── weights/best_v6.pt   # Mô hình phát hiện phương tiện
├── backend/
│   ├── main.py                  # FastAPI app, các endpoint, vòng xử lý video
│   ├── config.py                # Cấu hình (đọc từ biến môi trường)
│   ├── red_light_service.py     # Service phát hiện vượt đèn đỏ
│   ├── red_light_utils.py       # Kiểm tra cắt vạch, mô phỏng đèn giao thông
│   ├── dedupe_utils.py          # Loại bỏ vi phạm trùng lặp
│   ├── requirements.txt
│   └── temp_videos/             # Video upload tạm (tự xoá sau khi xử lý)
├── web/
│   └── src/
│       ├── components/          # UploadSection, DetectionViewer, LineDrawerOverlay, ViolationPanel
│       ├── hooks/               # useVideoDetectionBackend, useDetectionLogs
│       ├── config.js            # URL API / WebSocket
│       └── App.js
└── THIET_KE_HE_THONG.md         # Tài liệu thiết kế hệ thống
```

## Yêu cầu

- Python 3.9+
- Node.js 18+ và npm
- (Tuỳ chọn) GPU NVIDIA + CUDA để suy luận nhanh hơn; không có GPU vẫn chạy được trên CPU nhưng chậm hơn.

## Cài đặt và chạy

### 1. Clone

```bash
git clone https://github.com/NgHaiDuong205/ai-traffic-violation-detection.git
cd ai-traffic-violation-detection
```

Các file trọng số `best3.pt` và `best_v6.pt` đã có sẵn trong repo.

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Lệnh `uvicorn` phải chạy **trong thư mục `backend/`** vì `main.py` import trực tiếp các module cùng thư mục.

Kiểm tra: mở http://localhost:8000 (health check) hoặc http://localhost:8000/docs (Swagger UI).

### 3. Frontend

Mở một terminal khác:

```bash
cd web
npm install
npm start
```

Ứng dụng chạy tại http://localhost:3000.

Nếu backend không chạy ở `localhost:8000`, tạo file `web/.env`:

```env
REACT_APP_API_BASE_URL=http://<host>:8000
REACT_APP_WS_BASE_URL=ws://<host>:8000
```

## Cách sử dụng

1. Mở http://localhost:3000.
2. **Ảnh**: chọn file ảnh → hệ thống trả về ảnh đã đánh dấu và danh sách vi phạm không đội mũ bảo hiểm.
3. **Video**:
   1. Chọn file video (`.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, tối đa 500 MB).
   2. Vẽ vạch dừng trên khung hình đầu tiên.
   3. Bắt đầu xử lý: thanh tiến trình, bounding box và trạng thái đèn được cập nhật theo thời gian thực.
4. Xem danh sách trong bảng **Ghi nhận vi phạm** và bấm tải CSV nếu cần.

## API

| Phương thức | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/api/detect` | Phát hiện không đội mũ bảo hiểm trên ảnh (`multipart/form-data`, field `file`) |
| `POST` | `/api/upload_video` | Upload video, trả về tên file đã lưu tạm |
| `GET` | `/api/video_first_frame/{filename}` | Lấy khung hình đầu tiên để vẽ vạch dừng |
| `WS` | `/api/ws/video/{filename}?line_coords=...` | Xử lý video và stream kết quả |

Các message WebSocket gửi về client:

```jsonc
{ "status": "processing", "progress": 42 }                       // tiến trình
{ "status": "frame_batch", "frames": [ { "time_sec": 1.2, "light_state": "red", "bboxes": [...] } ] }
{ "status": "completed", "result": { "violations": [...], "stats": {...} } }
{ "error": "..." }                                                // lỗi
```

## Cấu hình

Mọi tham số trong [backend/config.py](backend/config.py) đều có thể ghi đè bằng biến môi trường. Một số tham số thường dùng:

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `HELMET_MODEL_PATH` | `ai_modules/helmet_detect/weights/best3.pt` | Đường dẫn mô hình mũ bảo hiểm |
| `VEHICLE_MODEL_PATH` | `ai_modules/vehicle_detect/weights/best_v6.pt` | Đường dẫn mô hình phương tiện |
| `FRAME_SKIP` | `2` | Xử lý 1 trên N khung hình (tăng để chạy nhanh hơn) |
| `HELMET_VIOLATION_SCORE_THRESHOLD` | `10` | Ngưỡng điểm để xác nhận vi phạm mũ bảo hiểm |
| `VIOLATION_DEDUPE_TIME_WINDOW_SEC` | `1.5` | Cửa sổ thời gian gộp vi phạm trùng |
| `TRAFFIC_LIGHT_GREEN_DURATION_SEC` / `TRAFFIC_LIGHT_RED_DURATION_SEC` | xem `config.py` | Thời lượng đèn xanh / đỏ mô phỏng |
| `MAX_VIDEO_UPLOAD_BYTES` | `500 MB` | Dung lượng video tối đa |
| `MODEL_EXECUTOR_MAX_WORKERS` | `2` | Số luồng chạy suy luận |

Ví dụ (PowerShell):

```powershell
$env:FRAME_SKIP = "3"; uvicorn main:app --port 8000
```

## Huấn luyện lại mô hình

Notebook huấn luyện nằm tại:

- [ai_modules/helmet_detect/training/train_model.ipynb](ai_modules/helmet_detect/training/train_model.ipynb)
- [ai_modules/vehicle_detect/training/train_model.ipynb](ai_modules/vehicle_detect/training/train_model.ipynb)

Sao chép `data.yaml.example` thành `data.yaml`, chỉnh đường dẫn dataset rồi chạy notebook. Dataset, `data.yaml` và thư mục `runs/` không được đưa lên git. Sau khi huấn luyện, đặt file trọng số mới vào thư mục `weights/` hoặc trỏ tới bằng `HELMET_MODEL_PATH` / `VEHICLE_MODEL_PATH`.

## Hạn chế

- Đèn giao thông là **mô phỏng theo chu kỳ thời gian**, chưa nhận diện trạng thái đèn thật trong video.
- Chưa nhận diện biển số xe.
- Kết quả chỉ lưu phía trình duyệt (xuất CSV), chưa có cơ sở dữ liệu.

## Công nghệ

FastAPI · Uvicorn · Ultralytics YOLO · OpenCV · NumPy · React 19 · WebSocket
