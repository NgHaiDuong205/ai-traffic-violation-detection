import os
import cv2
import numpy as np
import base64
import asyncio
import uuid
import shutil
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO

app = FastAPI(title="AI Traffic Violation API")

# Setup CORS to allow React Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the model
# Adjust the path to best3.pt
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ai_modules", "helmet_detect", "weights", "best3.pt")

print(f"Loading model from: {MODEL_PATH}")
if os.path.exists(MODEL_PATH):
    model = YOLO(MODEL_PATH)
else:
    print("Model file not found. Inference will fail")
    model = None

@app.post("/api/detect")
async def detect_image(file: UploadFile = File(...)):
    if not model:
        return {"error": "Model not loaded"}

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"error": "Invalid image file provided"}

    # Run YOLO inference
    results = model(img)

    res = results[0]
    
    violations = []

    annotated_img = res.plot()
    

    names = model.names
    valid_boxes = []
    
    for box in res.boxes:
        cls_id = int(box.cls[0])
        class_name = names[cls_id]
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        
        # Lọc các khung hình trùng lặp trên cùng 1 người
        is_duplicate = False
        for v_box in valid_boxes:
            if v_box["class_name"] == class_name:
                vx1, vy1, vx2, vy2 = v_box["coords"]
                
                # Tính diện tích phần giao nhau
                x_left = max(x1, vx1)
                y_top = max(y1, vy1)
                x_right = min(x2, vx2)
                y_bottom = min(y2, vy2)
                
                if x_right > x_left and y_bottom > y_top:
                    intersection_area = (x_right - x_left) * (y_bottom - y_top)
                    area1 = (x2 - x1) * (y2 - y1)
                    area2 = (vx2 - vx1) * (vy2 - vy1)
                    
                    # Nếu diện tích chồng chéo > 40% box nhỏ hơn => Là cùng 1 người
                    if (intersection_area / min(area1, area2)) > 0.4:
                        is_duplicate = True
                        break
                        
        if is_duplicate:
            continue
            
        valid_boxes.append({
            "class_name": class_name,
            "coords": (x1, y1, x2, y2)
        })
        
        # Append logic
        if "helmet" not in class_name.lower() or "no" in class_name.lower() or class_name.lower() == "without_helmet":
            violations.append({
                "severity": "high", 
                "icon": "⚠️", 
                "title": f"Phát hiện: {class_name} ({(conf*100):.1f}%)", 
                "source": "Camera AI"
            })
        else:
            violations.append({
                "severity": "info",
                "title": f"Phát hiện: {class_name} ({(conf*100):.1f}%)", 
                "source": "Camera AI"
            })

    # Convert annotated image to base64
    _, buffer = cv2.imencode('.jpg', annotated_img)
    base64_img = base64.b64encode(buffer).decode('utf-8')
    mime_type = "image/jpeg"
    base64_url = f"data:{mime_type};base64,{base64_img}"

    return {
        "success": True,
        "violations": violations,
        "annotated_image": base64_url
    }

@app.get("/")
def read_root():
    return {"message": "AI Traffic Violation API is running"}

# --- VIDEO STREAMING LOGIC ---

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp_videos")
os.makedirs(TEMP_DIR, exist_ok=True)

@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    # Generate unique filename to avoid collision
    ext = os.path.splitext(file.filename)[1]
    filename = f"video_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(TEMP_DIR, filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"success": True, "filename": filename}

@app.websocket("/api/ws/video/{filename}")
async def websocket_video_endpoint(websocket: WebSocket, filename: str):
    await websocket.accept()
    
    filepath = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(filepath):
        await websocket.send_json({"error": "Video file not found"})
        await websocket.close()
        return

    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        await websocket.send_json({"error": "Failed to open video file"})
        await websocket.close()
        return
        
    names = model.names if model else {}

    try:
        frame_skip = 2 # process every 3rd frame to ensure real-time speeds
        frame_count = 0
        reported_ids = set()
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            violations = []
            
            if model:
                # Resize frame to speed up if it's too large (optional)
                # frame = cv2.resize(frame, (640, 480))
                
                # Dùng thuộc tính track để cấp ID cho các đối tượng qua các frame
                results = model.track(frame, persist=True, verbose=False)
                res = results[0]
                annotated_img = res.plot()
                
                # Extract logs
                for box in res.boxes:
                    cls_id = int(box.cls[0])
                    class_name = names[cls_id]
                    conf = float(box.conf[0])
                    
                    if "helmet" not in class_name.lower() or "no" in class_name.lower() or class_name.lower() == "without_helmet":
                        # Lấy ID đối tượng nếu YOLO gán ID thành công
                        obj_id = int(box.id[0]) if box.id is not None else None
                        
                        if obj_id is not None:
                            # Nếu ID này đã được báo trước đó rồi thì bỏ qua
                            if obj_id in reported_ids:
                                continue
                            reported_ids.add(obj_id)
                            
                        # Thêm ID vào log để nhận biết người nào
                        title_text = f"Phát hiện: {class_name} ({(conf*100):.1f}%)"
                        if obj_id is not None:
                            title_text += f" - Khách #{obj_id}"

                        violations.append({
                            "severity": "high", 
                            "title": title_text, 
                            "source": "Camera AI"
                        })
            else:
                annotated_img = frame
                
            # Compress heavily to make websocket streaming fast
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
            _, buffer = cv2.imencode('.jpg', annotated_img, encode_param)
            base64_img = base64.b64encode(buffer).decode('utf-8')
            
            payload = {
                "frame": f"data:image/jpeg;base64,{base64_img}",
                "violations": violations
            }
            
            await websocket.send_json(payload)
            # Give back control to event loop to actually send data and not block completely
            await asyncio.sleep(0.01)

        await websocket.send_json({"status": "completed"})
            
    except WebSocketDisconnect:
        print(f"Client disconnected for video {filename}")
    except Exception as e:
        print(f"WS Error: {e}")
    finally:
        cap.release()
        # Optionally clean up the file
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        try:
            await websocket.close()
        except:
            pass
