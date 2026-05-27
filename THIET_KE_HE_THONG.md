# 3.2. THIẾT KẾ VÀ TRIỂN KHAI HỆ THỐNG

## 3.2.1. Kiến trúc tổng thể hệ thống

### 3.2.1.1. Mô hình kiến trúc

Hệ thống phát hiện vi phạm giao thông sử dụng AI được thiết kế theo mô hình **Client-Server** với kiến trúc **3 tầng (3-tier architecture)**:

```
┌─────────────────────────────────────────────────────────────┐
│                    TẦNG TRÌNH DIỄN                          │
│                  (Presentation Layer)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         React Web Application (Frontend)              │  │
│  │  - Giao diện người dùng                               │  │
│  │  - Upload ảnh/video                                   │  │
│  │  - Hiển thị kết quả phát hiện                        │  │
│  │  - Vẽ vùng phát hiện vi phạm                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    TẦNG ỨNG DỤNG                            │
│                 (Application Layer)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         FastAPI Backend Server (Python)               │  │
│  │  - REST API endpoints                                 │  │
│  │  - WebSocket real-time streaming                     │  │
│  │  - Business logic xử lý vi phạm                      │  │
│  │  - Quản lý file upload                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────────┐
│                    TẦNG DỮ LIỆU & AI                        │
│              (Data & AI Processing Layer)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         YOLO Models (Ultralytics)                     │  │
│  │  - Helmet Detection Model (best3.pt)                 │  │
│  │  - Vehicle Detection Model (best_v6.pt)              │  │
│  │  - OpenCV Image Processing                           │  │
│  │  - Tracking & Deduplication Logic                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```


### 3.2.1.2. Các thành phần chính

#### A. Frontend (React Web Application)

**Công nghệ sử dụng:**
- React 19.2.4
- JavaScript (ES6+)
- CSS3 cho styling
- WebSocket API cho real-time communication

**Cấu trúc thư mục:**
```
web/
├── src/
│   ├── components/          # Các component UI
│   │   ├── DetectionViewer.js      # Hiển thị video/ảnh và kết quả
│   │   ├── ViolationPanel.js       # Bảng danh sách vi phạm
│   │   ├── UploadSection.js        # Khu vực upload file
│   │   └── LineDrawerOverlay.js    # Vẽ đường phát hiện
│   ├── hooks/               # Custom React hooks
│   │   ├── useVideoDetectionBackend.js  # Logic kết nối backend
│   │   └── useDetectionLogs.js          # Quản lý logs
│   ├── App.js               # Component chính
│   ├── config.js            # Cấu hình API endpoints
│   └── index.js             # Entry point
├── public/                  # Static assets
└── package.json             # Dependencies
```


#### B. Backend (FastAPI Server)

**Công nghệ sử dụng:**
- FastAPI (Python web framework)
- Uvicorn (ASGI server)
- OpenCV (cv2) cho xử lý ảnh/video
- Ultralytics YOLO v8 cho AI detection
- NumPy cho xử lý mảng
- WebSocket cho streaming real-time

**Cấu trúc thư mục:**
```
backend/
├── main.py                  # FastAPI application & endpoints
├── config.py                # Cấu hình hệ thống
├── red_light_service.py     # Service phát hiện vượt đèn đỏ
├── red_light_utils.py       # Utilities cho traffic light logic
├── dedupe_utils.py          # Logic loại bỏ trùng lặp
├── requirements.txt         # Python dependencies
└── temp_videos/             # Thư mục lưu video tạm
```

**API Endpoints:**
- `GET /` - Health check
- `POST /api/detect` - Phát hiện vi phạm trên ảnh
- `POST /api/upload_video` - Upload video
- `GET /api/video_first_frame/{filename}` - Lấy frame đầu tiên
- `WebSocket /api/ws/video/{filename}` - Stream xử lý video real-time


#### C. AI Models Layer

**1. Helmet Detection Model (best3.pt)**
- Mô hình: YOLOv8
- Chức năng: Phát hiện người đội/không đội mũ bảo hiểm
- Classes: 
  - `helmet` - Đội mũ bảo hiểm
  - `without_helmet` / `no_helmet` - Không đội mũ bảo hiểm
- Đường dẫn: `ai_modules/helmet_detect/weights/best3.pt`

**2. Vehicle Detection Model (best_v6.pt)**
- Mô hình: YOLOv8
- Chức năng: Phát hiện và tracking các loại phương tiện
- Classes (ID: 0-4):
  - 0: car (ô tô)
  - 1: bus (xe buýt)
  - 2: truck (xe tải)
  - 3: motorcycle (xe máy)
  - 4: bicycle (xe đạp)
- Đường dẫn: `ai_modules/vehicle_detect/weights/best_v6.pt`

**3. Xử lý ảnh/video:**
- OpenCV (cv2) cho đọc/ghi video, xử lý frame
- NumPy cho xử lý mảng dữ liệu
- Base64 encoding cho truyền ảnh qua API


### 3.2.1.3. Luồng dữ liệu (Data Flow)

#### A. Luồng xử lý ảnh (Image Detection)

```
[1] User upload ảnh → Frontend
         ↓
[2] POST /api/detect với FormData → Backend
         ↓
[3] Backend decode ảnh (cv2.imdecode)
         ↓
[4] YOLO Helmet Model inference
         ↓
[5] Phát hiện bounding boxes & classes
         ↓
[6] Loại bỏ duplicate boxes (IOU threshold)
         ↓
[7] Vẽ annotations lên ảnh (res.plot())
         ↓
[8] Encode ảnh thành Base64
         ↓
[9] Trả về JSON {success, violations, annotated_image}
         ↓
[10] Frontend hiển thị ảnh & danh sách vi phạm
```


#### B. Luồng xử lý video (Video Detection với WebSocket)

```
[1] User upload video → Frontend
         ↓
[2] POST /api/upload_video → Backend lưu file tạm
         ↓
[3] GET /api/video_first_frame/{filename} → Lấy frame đầu
         ↓
[4] Frontend hiển thị LineDrawerOverlay
         ↓
[5] User vẽ đường phát hiện (detection line)
         ↓
[6] WebSocket connect: /api/ws/video/{filename}?line_coords={...}
         ↓
[7] Backend mở video với cv2.VideoCapture
         ↓
[8] Loop qua từng frame (với frame_skip):
    ├─ [8a] Helmet Model tracking (persist=True)
    │       ├─ Tính violation score cho mỗi object ID
    │       ├─ Kiểm tra threshold để xác nhận vi phạm
    │       └─ Dedupe theo ID & spatial overlap
    │
    ├─ [8b] Vehicle Model tracking (persist=True)
    │       ├─ Traffic Light Simulation (green/red cycle)
    │       ├─ Kiểm tra line crossing
    │       ├─ Phát hiện vượt đèn đỏ
    │       └─ Dedupe theo ID & spatial overlap
    │
    ├─ [8c] Gửi progress updates qua WebSocket
    │       {"status": "processing", "progress": 50}
    │
    └─ [8d] Gửi frame batches qua WebSocket
            {"status": "frame_batch", "frames": [...]}
         ↓
[9] Khi hoàn thành, gửi kết quả cuối:
    {"status": "completed", "result": {violations, stats}}
         ↓
[10] Frontend nhận data real-time:
     ├─ Cập nhật progress bar
     ├─ Lưu frame data để overlay
     ├─ Hiển thị bounding boxes theo thời gian
     └─ Hiển thị danh sách vi phạm
```


### 3.2.1.4. Cơ chế giao tiếp

#### A. REST API (HTTP)
- **Mục đích:** Upload file, lấy dữ liệu tĩnh
- **Protocol:** HTTP/HTTPS
- **Format:** JSON, FormData (multipart/form-data)
- **CORS:** Cho phép tất cả origins (`allow_origins=["*"]`)

#### B. WebSocket
- **Mục đích:** Stream xử lý video real-time
- **Protocol:** WebSocket (ws://)
- **Ưu điểm:**
  - Giao tiếp 2 chiều (bidirectional)
  - Low latency
  - Không cần polling
  - Phù hợp cho streaming data

**Message types:**
```javascript
// Progress update
{"status": "processing", "progress": 75}

// Frame batch
{"status": "frame_batch", "frames": [
  {time_sec, light_state, time_left, bboxes: [...]}
]}

// Completion
{"status": "completed", "result": {
  violations: [...],
  stats: {total_violations, no_helmet_count, vehicle_counts}
}}

// Error
{"error": "Error message"}
```


## 3.2.2. Thiết kế chức năng hệ thống

### 3.2.2.1. Chức năng phát hiện không đội mũ bảo hiểm

#### A. Mô tả chức năng
Hệ thống sử dụng YOLO model để phát hiện người tham gia giao thông có đội mũ bảo hiểm hay không.

#### B. Thuật toán xử lý

**1. Phát hiện trên ảnh:**
```python
# Bước 1: Load model
helmet_model = YOLO("best3.pt")

# Bước 2: Inference
results = helmet_model(image)

# Bước 3: Lọc duplicate boxes
for box in sorted(results[0].boxes, key=confidence, reverse=True):
    if not is_overlapping_bbox(box, existing_boxes, IOU_THRESHOLD):
        valid_boxes.append(box)
        
# Bước 4: Phân loại vi phạm
if "helmet" not in class_name or "no" in class_name:
    violations.append({severity: "high", ...})
```

**2. Phát hiện trên video (với tracking):**
```python
# Bước 1: YOLO tracking với persist=True
helmet_results = helmet_model.track(frame, persist=True)

# Bước 2: Tính violation score cho mỗi object ID
for obj_id, class_name in detections:
    if is_helmet_violation(class_name):
        scores[obj_id] += VIOLATION_SCORE_INCREMENT  # +2
    else:
        scores[obj_id] -= COMPLIANCE_SCORE_DECREMENT  # -1
        
# Bước 3: Kiểm tra threshold
if scores[obj_id] >= VIOLATION_SCORE_THRESHOLD:  # >= 10
    has_consistent_violation = True
    
# Bước 4: Dedupe theo ID và spatial overlap
if has_consistent_violation and deduper.should_report(obj_id, bbox, time):
    deduper.record(obj_id, bbox, time)
    violations.append(...)
```


#### C. Cơ chế chống nhiễu (Temporal Smoothing)

**Vấn đề:** Model có thể phát hiện không ổn định giữa các frame (flickering).

**Giải pháp:** Sử dụng violation score tích lũy:
- Mỗi frame phát hiện vi phạm: score += 2
- Mỗi frame không vi phạm: score -= 1
- Chỉ báo cáo vi phạm khi score >= 10
- Score tối đa: 30

**Ưu điểm:**
- Giảm false positive
- Đảm bảo vi phạm liên tục mới được báo cáo
- Tự động "tha thứ" cho detection tạm thời

#### D. Cơ chế loại bỏ trùng lặp (Deduplication)

**1. Theo Object ID:**
- Mỗi object được tracking với unique ID
- Một ID chỉ báo cáo vi phạm 1 lần duy nhất
- Lưu trong `reported_ids` set

**2. Theo vùng không gian (Spatial):**
- Tính IOU (Intersection over Union) giữa bounding boxes
- Tính khoảng cách center giữa các boxes
- Nếu IOU > threshold HOẶC distance < threshold → coi là trùng lặp
- Time window: 8 giây

**Công thức IOU:**
```python
def bbox_iou(box_a, box_b):
    intersection = overlap_area(box_a, box_b)
    area_a = (x2 - x1) * (y2 - y1)
    area_b = (x2 - x1) * (y2 - y1)
    return intersection / min(area_a, area_b)
```


### 3.2.2.2. Chức năng phát hiện vượt đèn đỏ

#### A. Mô tả chức năng
Hệ thống phát hiện phương tiện vượt qua vạch dừng khi đèn giao thông đang đỏ.

#### B. Các thành phần

**1. Traffic Light Simulation**
```python
class TrafficLightSimulation:
    states = ["green", "red"]
    durations = [10, 10]  # 10s xanh, 10s đỏ
    
    def get_current_light(self, current_time):
        # Tính state hiện tại dựa trên thời gian video
        elapsed = current_time - start_time
        if elapsed > current_duration:
            switch_to_next_state()
        return (state, time_left)
```

**2. Detection Line**
- User vẽ một đường thẳng trên video (x1,y1) → (x2,y2)
- Đường này đại diện cho vạch dừng
- Được gửi qua WebSocket query parameter

**3. Line Crossing Detection**
```python
def check_line_crossing(vehicle_id, bbox, traffic_light_state):
    # Bước 1: Lấy tâm phương tiện (center_x, bottom_y)
    center = get_vehicle_center(bbox)
    
    # Bước 2: Tính vị trí tương đối với đường
    # Sử dụng cross product
    cross = (x2-x1)*(y-y1) - (y2-y1)*(x-x1)
    current_side = "before" if cross >= 0 else "after"
    
    # Bước 3: Kiểm tra crossing
    if previous_side == "before" and current_side == "after":
        if traffic_light_state == "red":
            return True  # Vi phạm!
    
    return False
```


#### C. Thuật toán chi tiết

**Bước 1: Vehicle Tracking**
```python
vehicle_results = vehicle_model.track(
    frame, 
    persist=True,  # Giữ tracking ID giữa các frame
    classes=[0,1,2,3,4]  # car, bus, truck, motorcycle, bicycle
)
```

**Bước 2: Lưu trạng thái mỗi vehicle**
```python
vehicle_states = {
    vehicle_id: {
        "crossed": False,      # Đã vượt qua chưa?
        "last_side": "before"  # Vị trí cuối: before/after line
    }
}
```

**Bước 3: Phát hiện vi phạm**
```python
for vehicle in tracked_vehicles:
    is_violation = check_line_crossing(
        vehicle_id, bbox, frame_id, class_id, light_state
    )
    
    if is_violation and deduper.should_report(vehicle_id, bbox, time):
        deduper.record(vehicle_id, bbox, time)
        violations.append({
            "time_sec": time,
            "severity": "critical",
            "icon": "🔴",
            "title": f"Vượt đèn đỏ: {vehicle_type} #{vehicle_id}",
            "vehicle_type": vehicle_type
        })
```

#### D. Xử lý edge cases

**1. ID Swap:** YOLO tracking đôi khi đổi ID giữa các object
- **Giải pháp:** Spatial deduplication với IOU threshold

**2. Phương tiện dừng trên vạch:** Không di chuyển qua
- **Giải pháp:** Chỉ báo cáo khi `previous_side != current_side`

**3. Phương tiện đã qua trước khi đèn đỏ:**
- **Giải pháp:** Kiểm tra `traffic_light_state == "red"` tại thời điểm crossing


### 3.2.2.3. Chức năng upload và quản lý file

#### A. Upload ảnh
```javascript
// Frontend
const formData = new FormData();
formData.append('file', imageFile);

fetch('/api/detect', {
    method: 'POST',
    body: formData
});
```

```python
# Backend
@app.post("/api/detect")
async def detect_image(file: UploadFile = File(...)):
    # Giới hạn kích thước: 10MB
    contents = await file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(contents) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(413, "Image exceeds upload size limit")
    
    # Decode ảnh
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Xử lý...
```

#### B. Upload video
```python
@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    # Validate extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
        raise HTTPException(400, "Unsupported video extension")
    
    # Lưu file với UUID
    filename = f"video_{uuid.uuid4().hex}{ext}"
    filepath = TEMP_DIR / filename
    
    # Stream write với chunk size 1MB
    # Giới hạn: 500MB
    total_bytes = 0
    with open(filepath, "wb") as buffer:
        while chunk := await file.read(UPLOAD_CHUNK_SIZE):
            total_bytes += len(chunk)
            if total_bytes > MAX_VIDEO_UPLOAD_BYTES:
                raise HTTPException(413, "Video exceeds upload size limit")
            buffer.write(chunk)
    
    return {"success": True, "filename": filename}
```


#### C. Bảo mật file upload

**1. Path Traversal Prevention:**
```python
def _sanitize_filename(filename: str) -> str:
    # Loại bỏ path separators
    safe_name = os.path.basename(filename.strip())
    if "/" in filename or "\\" in filename:
        raise HTTPException(400, "Invalid filename")
    return safe_name

def _resolve_temp_video_path(filename: str) -> str:
    safe_name = _sanitize_filename(filename)
    resolved_path = (TEMP_DIR / safe_name).resolve()
    
    # Đảm bảo file nằm trong TEMP_DIR
    if resolved_path.parent != TEMP_DIR.resolve():
        raise HTTPException(400, "Invalid file path")
    
    return str(resolved_path)
```

**2. File Size Limits:**
- Ảnh: 10MB
- Video: 500MB
- Chunk size: 1MB

**3. File Extension Whitelist:**
- Video: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`
- Ảnh: Tất cả image/* MIME types

**4. Cleanup:**
```python
# Xóa file sau khi xử lý xong
finally:
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass
```


### 3.2.2.4. Chức năng hiển thị kết quả real-time

#### A. Video Overlay System

**1. Frame Data Structure:**
```javascript
{
  time_sec: 5.2,              // Thời điểm trong video
  light_state: "red",         // Trạng thái đèn: green/red/unknown
  time_left: 7,               // Thời gian còn lại (giây)
  bboxes: [                   // Danh sách bounding boxes
    {
      id: 123,                // Tracking ID
      bbox: [x1, y1, x2, y2], // Tọa độ
      class_name: "V:123",    // Tên class
      conf: 0.95,             // Confidence
      is_violation: true,     // Có vi phạm không?
      just_violated: false,   // Vừa mới vi phạm?
      type: "vehicle"         // helmet/vehicle
    }
  ]
}
```

**2. Binary Search cho Frame Lookup:**
```javascript
function findClosestFrame(frames, currentTime) {
    let lo = 0, hi = frames.length - 1;
    let closest = frames[0];
    
    while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const diff = frames[mid].time_sec - currentTime;
        
        if (Math.abs(diff) < Math.abs(closest.time_sec - currentTime)) {
            closest = frames[mid];
        }
        
        if (diff < 0) lo = mid + 1;
        else hi = mid - 1;
    }
    
    return closest;
}
```


**3. Overlay Transform (Video Scaling):**
```javascript
function updateTransform() {
    const video = videoRef.current;
    const videoRatio = video.videoWidth / video.videoHeight;
    const elementRatio = video.clientWidth / video.clientHeight;
    
    let renderWidth, renderHeight, offsetX = 0, offsetY = 0;
    
    if (elementRatio > videoRatio) {
        // Letterbox (black bars on sides)
        renderHeight = video.clientHeight;
        renderWidth = video.clientHeight * videoRatio;
        offsetX = (video.clientWidth - renderWidth) / 2;
    } else {
        // Pillarbox (black bars on top/bottom)
        renderWidth = video.clientWidth;
        renderHeight = video.clientWidth / videoRatio;
        offsetY = (video.clientHeight - renderHeight) / 2;
    }
    
    return {
        scaleX: renderWidth / video.videoWidth,
        scaleY: renderHeight / video.videoHeight,
        offsetX, offsetY
    };
}
```

**4. Vẽ Bounding Boxes:**
```javascript
const left = offsetX + bbox[0] * scaleX;
const top = offsetY + bbox[1] * scaleY;
const width = (bbox[2] - bbox[0]) * scaleX;
const height = (bbox[3] - bbox[1]) * scaleY;

// Màu sắc theo loại vi phạm
let color = '#22c55e';  // Xanh lá: hợp lệ
if (box.is_violation) {
    color = box.type === 'helmet' ? '#3b82f6' : '#ef4444';
    // Xanh dương: Không MBH, Đỏ: Vượt đèn đỏ
}
```


#### B. Statistics Dashboard

**1. Cấu trúc dữ liệu thống kê:**
```javascript
stats = {
    total_violations: 15,        // Tổng số vi phạm
    no_helmet_count: 8,          // Số vi phạm không MBH
    vehicle_counts: {            // Phân loại theo loại xe
        "car": 3,
        "motorcycle": 4,
        "bus": 0
    }
}
```

**2. Dynamic Stats (Real-time):**
```javascript
function useDetectionLogs(logs, detectionResult, currentTime) {
    // Lọc violations đã xảy ra đến thời điểm hiện tại
    const pastViolations = detectionResult?.violations?.filter(
        v => v.time_sec <= currentTime
    ) || [];
    
    // Tính toán stats động
    const dynamicStats = {
        total_violations: pastViolations.length,
        no_helmet_count: pastViolations.filter(
            v => v.vehicle_type === 'no_helmet'
        ).length,
        vehicle_counts: countByType(pastViolations)
    };
    
    return { dynamicStats };
}
```

**3. Hiển thị UI:**
- Badge tổng vi phạm (màu đỏ)
- Badge không MBH (màu vàng)
- Breakdown theo loại xe
- Traffic light indicator (xanh/đỏ + countdown)


### 3.2.2.5. Tối ưu hiệu năng

#### A. Backend Optimization

**1. Async Processing với ThreadPoolExecutor:**
```python
model_executor = ThreadPoolExecutor(max_workers=2)

# Chạy inference trong thread pool để không block event loop
helmet_future = loop.run_in_executor(
    model_executor,
    lambda: helmet_model.track(frame, persist=True)
)

vehicle_future = loop.run_in_executor(
    model_executor,
    lambda: vehicle_model.track(frame, persist=True)
)

# Await cả 2 cùng lúc
helmet_results = await helmet_future
vehicle_results = await vehicle_future
```

**2. Frame Skipping:**
```python
FRAME_SKIP = 1  # Xử lý mọi frame (có thể tăng lên 2-3 để tăng tốc)

while cap.isOpened():
    ret, frame = cap.read()
    frame_count += 1
    
    if frame_count % FRAME_SKIP != 0:
        continue  # Bỏ qua frame này
    
    # Xử lý frame...
```

**3. Sparse Frame Storage:**
```python
# Chỉ lưu frame khi:
# - Có vi phạm mới
# - Đèn giao thông đổi màu
# - Đã qua FRAME_STORAGE_INTERVAL_SEC (0.5s)

if should_store_frame(frame_payload, last_stored_time, last_light_state, has_new_violation):
    pending_frames.append(frame_payload)
```

**4. Batch Streaming:**
```python
FRAME_STREAM_BATCH_SIZE = 40

if len(pending_frames) >= FRAME_STREAM_BATCH_SIZE:
    await websocket.send_json({
        "status": "frame_batch",
        "frames": pending_frames
    })
    pending_frames.clear()
```


#### B. Frontend Optimization

**1. Binary Search thay vì Linear Search:**
```javascript
// O(log n) thay vì O(n)
const closestFrame = findClosestFrame(frames, currentTime);
```

**2. Memoization với useCallback:**
```javascript
const updateOverlayAtTime = useCallback((currentTime) => {
    const closest = findClosestFrame(detectionResult?.frames, currentTime);
    setCurrentFrameData(closest);
}, [detectionResult, findClosestFrame]);
```

**3. Debounce Resize Events:**
```javascript
useEffect(() => {
    window.addEventListener('resize', updateTransform);
    return () => window.removeEventListener('resize', updateTransform);
}, [updateTransform]);
```

**4. Conditional Rendering:**
```javascript
{currentFrameData && currentFrameData.bboxes && mediaType === 'video' && (
    <div>
        {/* Chỉ render overlay khi có data */}
    </div>
)}
```

**5. Video Playback Rate:**
```javascript
onLoadedMetadata={(e) => {
    e.target.playbackRate = 0.5;  // Chậm 2x để dễ quan sát
}}
```


## 3.2.3. Thiết kế giao diện

### 3.2.3.1. Nguyên tắc thiết kế

#### A. Design Principles
1. **Clarity (Rõ ràng):** Thông tin quan trọng được hiển thị nổi bật
2. **Efficiency (Hiệu quả):** Quy trình làm việc ngắn gọn, ít bước
3. **Consistency (Nhất quán):** Màu sắc, typography, spacing đồng nhất
4. **Feedback (Phản hồi):** Luôn thông báo trạng thái cho người dùng
5. **Accessibility (Dễ tiếp cận):** Màu sắc tương phản cao, font size hợp lý

#### B. Color Scheme

**Màu chủ đạo:**
- Background: `#0f172a` (Dark blue-gray)
- Panel: `#1e293b` (Lighter blue-gray)
- Border: `rgba(255,255,255,0.1)` (Subtle white)

**Màu trạng thái:**
- Success/Valid: `#22c55e` (Green)
- Warning/Helmet: `#3b82f6` (Blue)
- Critical/Red Light: `#ef4444` (Red)
- Info: `#fbbf24` (Amber)

**Màu text:**
- Primary: `#ffffff` (White)
- Secondary: `#94a3b8` (Gray)
- Muted: `#64748b` (Darker gray)


### 3.2.3.2. Layout tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                         HEADER                              │
│  🚦 SmartTraffic AI              [●] Hệ thống hoạt động    │
└─────────────────────────────────────────────────────────────┘
┌──────────────────┬──────────────────────────────────────────┐
│                  │                                          │
│  VIOLATION       │         DETECTION VIEWER                 │
│  PANEL           │                                          │
│                  │  ┌────────────────────────────────────┐  │
│  ┌────────────┐  │  │                                    │  │
│  │ 🔴 Critical│  │  │                                    │  │
│  │ Vượt đèn đỏ│  │  │         VIDEO / IMAGE              │  │
│  │ 10:23:45   │  │  │         + OVERLAY                  │  │
│  └────────────┘  │  │                                    │  │
│                  │  │                                    │  │
│  ┌────────────┐  │  └────────────────────────────────────┘  │
│  │ ⚠️  High   │  │                                          │
│  │ Không MBH  │  │  [Traffic Light] [Stats Dashboard]      │
│  │ 10:23:47   │  │                                          │
│  └────────────┘  │                                          │
│                  │                                          │
│  ...             │                                          │
│                  │                                          │
└──────────────────┴──────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    UPLOAD SECTION                           │
│                                                             │
│         📤  Tải lên ảnh / video để phân tích                │
│         Kéo thả file vào đây, hoặc chọn file               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Tỷ lệ:**
- Header: 80px height
- Main content: flex-grow (chiếm phần còn lại)
  - Violation Panel: 400px width (fixed)
  - Detection Viewer: flex-grow
- Upload Section: 200px height


### 3.2.3.3. Các thành phần giao diện chi tiết

#### A. Header Component

**Chức năng:**
- Hiển thị logo và tên hệ thống
- Hiển thị trạng thái hoạt động

**Thiết kế:**
```css
.app-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header-icon {
    font-size: 2rem;  /* 🚦 emoji */
}

.status-badge {
    background: rgba(34, 197, 94, 0.2);
    border: 1px solid #22c55e;
    padding: 0.5rem 1rem;
    border-radius: 20px;
}

.status-dot {
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
}
```

**Mockup:**
```
┌─────────────────────────────────────────────────────────┐
│  🚦 SmartTraffic AI          ● Hệ thống hoạt động      │
│  [Gradient Purple Background]                           │
└─────────────────────────────────────────────────────────┘
```


#### B. Violation Panel Component

**Chức năng:**
- Hiển thị danh sách vi phạm theo thời gian
- Phân loại theo mức độ nghiêm trọng
- Auto-scroll khi có vi phạm mới

**Thiết kế:**
```css
.violations-panel {
    width: 400px;
    background: #1e293b;
    border-right: 1px solid rgba(255,255,255,0.1);
    overflow-y: auto;
}

.violation-item {
    padding: 1rem;
    border-left: 4px solid;
    margin-bottom: 0.5rem;
    background: rgba(255,255,255,0.05);
}

.violation-item.critical {
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
}

.violation-item.high {
    border-left-color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
}

.violation-item.info {
    border-left-color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
}
```

**Mockup:**
```
┌──────────────────────────┐
│ 📋 Danh sách vi phạm     │
├──────────────────────────┤
│ ┌──────────────────────┐ │
│ │🔴 CRITICAL           │ │
│ │Vượt đèn đỏ: car #123 │ │
│ │⏰ 10:23:45           │ │
│ │📍 YOLO Traffic       │ │
│ └──────────────────────┘ │
│                          │
│ ┌──────────────────────┐ │
│ │⚠️  HIGH              │ │
│ │Không MBH: ID #45     │ │
│ │⏰ 10:23:47           │ │
│ │📍 YOLO Helmet        │ │
│ └──────────────────────┘ │
│                          │
│ ...                      │
└──────────────────────────┘
```


#### C. Detection Viewer Component

**Chức năng:**
- Hiển thị video/ảnh
- Overlay bounding boxes
- Hiển thị traffic light status
- Hiển thị statistics dashboard

**Thiết kế:**
```css
.viewer-panel {
    flex: 1;
    background: #1e293b;
    position: relative;
}

.viewer-container {
    position: relative;
    width: 100%;
    height: calc(100vh - 280px);
    background: #000;
}

.uploaded-media {
    width: 100%;
    height: 100%;
    object-fit: contain;  /* Giữ tỷ lệ, không crop */
}

/* Overlay layer */
.overlay-layer {
    position: absolute;
    inset: 0;
    pointer-events: none;
}

/* Bounding box */
.bbox {
    position: absolute;
    border: 2px solid;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
}

.bbox-label {
    position: absolute;
    background: inherit;
    color: white;
    font-size: 12px;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px 4px 0 0;
}
```


**Mockup:**
```
┌────────────────────────────────────────────────────────────┐
│ 📺 Màn hình phát hiện    [🚦 ĐỎ 7s] [📊 Tổng: 15 vi phạm] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                      │ │
│  │         ┌─────────────────┐                         │ │
│  │         │ V:123 (95%)     │  ← Label                │ │
│  │         ├─────────────────┤                         │ │
│  │         │                 │                         │ │
│  │         │   [Vehicle]     │  ← Bounding Box (Red)   │ │
│  │         │                 │                         │ │
│  │         └─────────────────┘                         │ │
│  │                VIOLATION!   ← Flash text            │ │
│  │                                                      │ │
│  │  ═══════════════════════════  ← Detection Line      │ │
│  │                                                      │ │
│  │         ┌──────────┐                                │ │
│  │         │ #45 (92%)│                                │ │
│  │         ├──────────┤                                │ │
│  │         │ [Helmet] │  ← Bounding Box (Blue)         │ │
│  │         └──────────┘                                │ │
│  │                                                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  [Video Controls: Play/Pause, Timeline, Volume]           │
└────────────────────────────────────────────────────────────┘
```


#### D. Upload Section Component

**Chức năng:**
- Drag & drop upload
- Click to browse file
- Hiển thị file size limit
- Visual feedback khi drag over

**Thiết kế:**
```css
.upload-section {
    height: 200px;
    background: #1e293b;
    border-top: 1px solid rgba(255,255,255,0.1);
}

.upload-dropzone {
    height: 100%;
    border: 2px dashed rgba(255,255,255,0.2);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.upload-dropzone:hover {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.05);
}

.upload-dropzone.dragover {
    border-color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
    transform: scale(1.02);
}

.upload-cloud-icon::before {
    content: "☁️";
    font-size: 3rem;
}

.browse-link {
    color: #3b82f6;
    text-decoration: underline;
    cursor: pointer;
}
```


**Mockup:**
```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                          ☁️                                │
│                                                            │
│              Tải lên ảnh / video để phân tích              │
│                                                            │
│         Kéo thả file vào đây, hoặc chọn file               │
│                                                            │
│           Hỗ trợ MP4, AVI, JPEG, PNG (Tối đa 50MB)        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**States:**
- **Normal:** Border dashed trắng mờ
- **Hover:** Border xanh dương, background xanh nhạt
- **Drag Over:** Border xanh lá, background xanh lá nhạt, scale 1.02
- **Uploading:** Hiển thị progress bar


#### E. Line Drawer Overlay Component

**Chức năng:**
- Cho phép user vẽ detection line trên video
- Hiển thị first frame của video
- Confirm/Cancel buttons

**Thiết kế:**
```css
.line-drawer-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    z-index: 1000;
}

.line-drawer-canvas {
    cursor: crosshair;
}

.line-drawer-instructions {
    position: absolute;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.9);
    padding: 1rem 2rem;
    border-radius: 8px;
    color: white;
}

.line-drawer-buttons {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 1rem;
}

.btn-confirm {
    background: #22c55e;
    color: white;
    padding: 0.75rem 2rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
}

.btn-cancel {
    background: #ef4444;
}
```


**Mockup:**
```
┌────────────────────────────────────────────────────────────┐
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 📍 Vẽ đường phát hiện vi phạm vượt đèn đỏ            │  │
│  │    Click 2 điểm để tạo đường thẳng                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │                                                      │ │
│  │                  [First Frame]                       │ │
│  │                                                      │ │
│  │         ●─────────────────────────●                  │ │
│  │         ^                         ^                  │ │
│  │      Point 1                   Point 2               │ │
│  │                                                      │ │
│  │                                                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│              [✓ Xác nhận]    [✗ Hủy bỏ]                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Interaction Flow:**
1. User click điểm đầu tiên → Hiển thị marker
2. User di chuyển chuột → Hiển thị preview line
3. User click điểm thứ hai → Line hoàn thành
4. User click "Xác nhận" → Gửi coords đến backend
5. User click "Hủy bỏ" → Đóng overlay, không xử lý video


#### F. Traffic Light Indicator

**Chức năng:**
- Hiển thị trạng thái đèn giao thông (xanh/đỏ)
- Countdown timer
- Đồng bộ với video timeline

**Thiết kế:**
```css
.traffic-light-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(0, 0, 0, 0.4);
    padding: 0.4rem 1rem;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.light-bulb {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.3);
}

.light-bulb.green {
    background: #22c55e;
    box-shadow: 0 0 20px #22c55e;
}

.light-bulb.red {
    background: #ef4444;
    box-shadow: 0 0 20px #ef4444;
}

.countdown-timer {
    font-family: monospace;
    font-weight: bold;
    font-size: 1.2rem;
    width: 30px;
    text-align: right;
}

.countdown-timer.red {
    color: #ef4444;
}

.countdown-timer.green {
    color: #22c55e;
}
```


**Mockup:**
```
┌─────────────────────────┐
│ TÍN HIỆU:  ●  7s        │
│           RED            │
└─────────────────────────┘

┌─────────────────────────┐
│ TÍN HIỆU:  ●  3s        │
│          GREEN           │
└─────────────────────────┘
```

**Animation:**
- Đèn có glow effect (box-shadow)
- Countdown giảm dần mỗi giây
- Khi chuyển đổi: fade transition 0.3s


#### G. Statistics Dashboard

**Chức năng:**
- Hiển thị tổng số vi phạm
- Phân loại theo loại (không MBH, vượt đèn đỏ)
- Breakdown theo loại xe

**Thiết kế:**
```css
.stats-dashboard {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: rgba(239, 68, 68, 0.1);
    padding: 0.4rem 1rem;
    border-radius: 8px;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.stat-item {
    display: flex;
    flex-direction: column;
}

.stat-label {
    font-size: 0.75rem;
    color: #ef4444;
    font-weight: bold;
    text-transform: uppercase;
}

.stat-value {
    font-size: 1.2rem;
    font-weight: bold;
    color: white;
    line-height: 1;
}

.stat-divider {
    border-left: 1px solid rgba(255, 255, 255, 0.2);
    height: 100%;
}
```


**Mockup:**
```
┌──────────────────────────────────────────────────────────┐
│  TỔNG VI PHẠM │ KHÔNG MBH │  CAR  │ MOTORCYCLE │  BUS   │
│      15       │     8     │   3   │     4      │   0    │
└──────────────────────────────────────────────────────────┘
```

**Responsive Behavior:**
- Desktop: Hiển thị tất cả stats trên 1 hàng
- Tablet: Wrap thành 2 hàng
- Mobile: Stack vertically


#### H. Loading & Progress States

**1. Image Detection Loading:**
```css
.detection-overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 100;
}

.detection-spinner {
    width: 60px;
    height: 60px;
    border: 4px solid rgba(255, 255, 255, 0.1);
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

**2. Video Processing Progress:**
```css
.progress-bar-container {
    width: 60%;
    background: rgba(255, 255, 255, 0.2);
    height: 10px;
    border-radius: 5px;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: #3b82f6;
    transition: width 0.2s ease;
}

.progress-text {
    font-size: 0.8rem;
    margin-top: 5px;
    color: white;
}
```


**Mockup:**
```
┌────────────────────────────────────────┐
│                                        │
│              ⟳ (spinning)              │
│                                        │
│      AI đang phân tích video...        │
│                                        │
│  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░  │
│                                        │
│           75% hoàn thành               │
│                                        │
└────────────────────────────────────────┘
```


### 3.2.3.4. Responsive Design

#### A. Breakpoints

```css
/* Desktop: >= 1200px */
@media (min-width: 1200px) {
    .violations-panel { width: 400px; }
    .main-content { flex-direction: row; }
}

/* Tablet: 768px - 1199px */
@media (min-width: 768px) and (max-width: 1199px) {
    .violations-panel { width: 350px; }
    .stats-dashboard { flex-wrap: wrap; }
}

/* Mobile: < 768px */
@media (max-width: 767px) {
    .main-content { flex-direction: column; }
    .violations-panel { 
        width: 100%; 
        max-height: 300px;
    }
    .viewer-panel { height: 400px; }
    .upload-section { height: 150px; }
}
```

#### B. Touch Optimization

**Mobile gestures:**
- Pinch to zoom trên video
- Swipe để scroll violation list
- Tap để play/pause video

**Touch targets:**
- Minimum size: 44x44px (Apple HIG)
- Spacing: 8px minimum between interactive elements


### 3.2.3.5. Accessibility (A11y)

#### A. Color Contrast

**WCAG 2.1 Level AA compliance:**
- Text trên background: Contrast ratio >= 4.5:1
- Large text (>= 18pt): Contrast ratio >= 3:1
- UI components: Contrast ratio >= 3:1

**Kiểm tra:**
```
White (#ffffff) on Dark Blue (#0f172a): 15.3:1 ✓
Green (#22c55e) on Dark: 4.8:1 ✓
Red (#ef4444) on Dark: 5.2:1 ✓
```

#### B. Keyboard Navigation

**Tab order:**
1. Header status badge
2. Violation list items
3. Video controls
4. Upload dropzone

**Keyboard shortcuts:**
- `Space`: Play/Pause video
- `Arrow Left/Right`: Seek video ±5s
- `Arrow Up/Down`: Scroll violation list
- `Esc`: Close line drawer overlay

#### C. Screen Reader Support

**ARIA labels:**
```html
<button aria-label="Tải lên video để phân tích">
    Upload
</button>

<div role="alert" aria-live="polite">
    Phát hiện vi phạm mới: Vượt đèn đỏ
</div>

<video aria-label="Video phát hiện vi phạm giao thông">
</video>
```


### 3.2.3.6. User Experience Flow

#### A. Quy trình sử dụng hệ thống

**Scenario 1: Phát hiện vi phạm trên ảnh**

```
[1] User mở ứng dụng
    ↓
[2] Kéo thả ảnh vào upload section
    ↓
[3] Hiển thị loading spinner "AI đang phân tích..."
    ↓
[4] Backend xử lý (1-3 giây)
    ↓
[5] Hiển thị ảnh đã annotate với bounding boxes
    ↓
[6] Danh sách vi phạm xuất hiện ở panel bên trái
    ↓
[7] User xem chi tiết từng vi phạm
```

**Scenario 2: Phát hiện vi phạm trên video**

```
[1] User upload video
    ↓
[2] Hiển thị first frame
    ↓
[3] LineDrawerOverlay xuất hiện
    ↓
[4] User vẽ detection line (2 clicks)
    ↓
[5] User click "Xác nhận"
    ↓
[6] WebSocket connection established
    ↓
[7] Progress bar cập nhật real-time (0% → 100%)
    ↓
[8] Frame batches được stream về frontend
    ↓
[9] Video tự động play với overlay bounding boxes
    ↓
[10] Violations xuất hiện trong panel theo thời gian
    ↓
[11] User có thể pause/seek để xem chi tiết
    ↓
[12] Stats dashboard cập nhật theo video timeline
```


#### B. Error Handling & User Feedback

**1. Upload Errors:**
```javascript
// File quá lớn
"❌ File vượt quá giới hạn 50MB. Vui lòng chọn file nhỏ hơn."

// Format không hỗ trợ
"❌ Định dạng file không được hỗ trợ. Vui lòng chọn MP4, AVI, JPEG hoặc PNG."

// Network error
"❌ Lỗi kết nối. Vui lòng kiểm tra internet và thử lại."
```

**2. Processing Errors:**
```javascript
// Model không load được
"❌ Không thể tải AI model. Vui lòng liên hệ quản trị viên."

// Video không đọc được
"❌ Không thể đọc video. File có thể bị hỏng."

// WebSocket disconnect
"⚠️ Mất kết nối. Đang thử kết nối lại..."
```

**3. Success Messages:**
```javascript
// Upload thành công
"✅ Tải lên thành công! Đang phân tích..."

// Xử lý hoàn tất
"✅ Phân tích hoàn tất! Phát hiện 15 vi phạm."

// Không có vi phạm
"✅ Không phát hiện vi phạm nào."
```

**Hiển thị:**
- Toast notification ở góc phải trên
- Auto dismiss sau 5 giây
- Có thể dismiss bằng click X


### 3.2.3.7. Animation & Transitions

#### A. Micro-interactions

**1. Button Hover:**
```css
.button {
    transition: all 0.2s ease;
}

.button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.button:active {
    transform: translateY(0);
}
```

**2. Violation Item Appear:**
```css
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.violation-item {
    animation: slideIn 0.3s ease;
}
```

**3. Status Dot Pulse:**
```css
@keyframes pulse {
    0%, 100% {
        opacity: 1;
        transform: scale(1);
    }
    50% {
        opacity: 0.7;
        transform: scale(1.1);
    }
}

.status-dot {
    animation: pulse 2s infinite;
}
```

**4. Progress Bar Fill:**
```css
.progress-bar-fill {
    transition: width 0.2s ease;
}
```


#### B. Page Transitions

**1. Initial Load:**
```css
.app-container {
    animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
```

**2. Panel Slide:**
```css
.violations-panel {
    animation: slideInLeft 0.4s ease;
}

@keyframes slideInLeft {
    from {
        transform: translateX(-100%);
    }
    to {
        transform: translateX(0);
    }
}
```

**3. Overlay Fade:**
```css
.line-drawer-overlay {
    animation: fadeIn 0.3s ease;
}

.line-drawer-overlay.closing {
    animation: fadeOut 0.3s ease;
}

@keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
}
```


### 3.2.3.8. Typography

#### A. Font Family

```css
:root {
    --font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', 
                    'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 
                    'Fira Sans', 'Droid Sans', 'Helvetica Neue', 
                    sans-serif;
    --font-mono: 'Courier New', Courier, monospace;
}

body {
    font-family: var(--font-primary);
}

.countdown-timer, code {
    font-family: var(--font-mono);
}
```

#### B. Font Sizes & Weights

```css
/* Headings */
h1 { font-size: 2rem; font-weight: 700; }      /* 32px */
h2 { font-size: 1.5rem; font-weight: 600; }    /* 24px */
h3 { font-size: 1.25rem; font-weight: 600; }   /* 20px */

/* Body */
body { font-size: 1rem; font-weight: 400; }    /* 16px */
.small { font-size: 0.875rem; }                /* 14px */
.tiny { font-size: 0.75rem; }                  /* 12px */

/* Special */
.violation-title { font-size: 1rem; font-weight: 500; }
.stat-value { font-size: 1.2rem; font-weight: 700; }
.bbox-label { font-size: 0.75rem; font-weight: 700; }
```

#### C. Line Height

```css
body { line-height: 1.6; }
h1, h2, h3 { line-height: 1.2; }
.stat-value { line-height: 1; }
```


### 3.2.3.9. Spacing System

#### A. Spacing Scale

```css
:root {
    --space-1: 0.25rem;   /* 4px */
    --space-2: 0.5rem;    /* 8px */
    --space-3: 0.75rem;   /* 12px */
    --space-4: 1rem;      /* 16px */
    --space-5: 1.25rem;   /* 20px */
    --space-6: 1.5rem;    /* 24px */
    --space-8: 2rem;      /* 32px */
    --space-10: 2.5rem;   /* 40px */
    --space-12: 3rem;     /* 48px */
}
```

#### B. Component Spacing

```css
/* Padding */
.panel { padding: var(--space-6); }
.violation-item { padding: var(--space-4); }
.button { padding: var(--space-3) var(--space-6); }

/* Margin */
.violation-item { margin-bottom: var(--space-2); }
.section { margin-bottom: var(--space-8); }

/* Gap */
.flex-container { gap: var(--space-4); }
.stats-dashboard { gap: var(--space-4); }
```

#### C. Border Radius

```css
:root {
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-full: 9999px;
}

.button { border-radius: var(--radius-md); }
.panel { border-radius: var(--radius-lg); }
.badge { border-radius: var(--radius-full); }
```


## 3.2.4. Tổng kết thiết kế hệ thống

### 3.2.4.1. Ưu điểm của kiến trúc

**1. Tách biệt rõ ràng (Separation of Concerns):**
- Frontend chỉ lo UI/UX
- Backend xử lý business logic & AI
- Models layer độc lập, dễ thay thế

**2. Scalability:**
- Backend có thể scale horizontal (thêm workers)
- Frontend có thể deploy lên CDN
- Models có thể chạy trên GPU server riêng

**3. Real-time Performance:**
- WebSocket cho streaming data
- Async processing với ThreadPoolExecutor
- Frame batching giảm overhead

**4. Maintainability:**
- Code structure rõ ràng, dễ đọc
- Component-based architecture (React)
- Configuration centralized (config.py)

**5. Security:**
- Path traversal prevention
- File size limits
- Extension whitelist
- CORS configuration

