import os
import cv2
import numpy as np
import base64
import asyncio
import uuid
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from red_light_utils import RedLightViolationDetector, TrafficLightSimulation
import json
from collections import Counter

# Thread pool for blocking model inference
model_executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="AI Traffic Violation API")

# Setup CORS to allow React Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model paths (relative to project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HELMET_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "ai_modules", "helmet_detect", "weights", "best3.pt"
)
VEHICLE_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "ai_modules", "vehicle_detect", "weights", "best_v6.pt"
)

print(f"Loading helmet model from: {HELMET_MODEL_PATH}")
helmet_model = YOLO(HELMET_MODEL_PATH) if os.path.exists(HELMET_MODEL_PATH) else None

print(f"Loading vehicle model from: {VEHICLE_MODEL_PATH}")
vehicle_model = YOLO(VEHICLE_MODEL_PATH) if os.path.exists(VEHICLE_MODEL_PATH) else None

# For backward compatibility with existing code
model = helmet_model

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

@app.get("/api/video_first_frame/{filename}")
async def get_video_first_frame(filename: str):
    filepath = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Video not found")
    
    cap = cv2.VideoCapture(filepath)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(status_code=500, detail="Could not read video")
        
    _, buffer = cv2.imencode('.jpg', frame)
    base64_img = base64.b64encode(buffer).decode('utf-8')
    return {"frame": f"data:image/jpeg;base64,{base64_img}"}

@app.websocket("/api/ws/video/{filename}")
async def websocket_video_endpoint(websocket: WebSocket, filename: str, line_coords: str = None):
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
        
    names = helmet_model.names if helmet_model else {}
    vehicle_names = vehicle_model.names if vehicle_model else {}

    # Initialize Red Light Detector if coordinates are provided
    red_light_detector = None
    traffic_light_sim = None
    if line_coords and vehicle_model:
        try:
            coords = json.loads(line_coords)
            red_light_detector = RedLightViolationDetector()
            red_light_detector.set_detection_line((coords['x1'], coords['y1']), (coords['x2'], coords['y2']))
            traffic_light_sim = TrafficLightSimulation()
        except Exception as e:
            print(f"Error parsing line_coords: {e}")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30 # fallback
        
        print(f"[WS] Starting processing: {filename}, total_frames={total_frames}, fps={fps}")
        
        frame_skip = 1 # process every frame
        frame_count = 0
        reported_ids = set()
        helmet_violation_scores = {} # Track score to prevent flickering / false positives
        
        all_frames_data = []
        all_violations = []

        loop = asyncio.get_event_loop()
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % frame_skip != 0:
                continue

            frame_bboxes = []
            light_state = "unknown"
            time_left = 0

            if helmet_model or vehicle_model:
                # 1. Helmet Detection - run in thread pool to avoid blocking event loop
                if helmet_model:
                    helmet_results = await loop.run_in_executor(
                        model_executor,
                        lambda f=frame: helmet_model.track(f, persist=True, verbose=False)
                    )
                    
                    if helmet_results[0].boxes.id is not None:
                        h_boxes = helmet_results[0].boxes.xyxy.cpu().numpy()
                        h_ids = helmet_results[0].boxes.id.cpu().numpy().astype(int)
                        h_classes = helmet_results[0].boxes.cls.cpu().numpy().astype(int)
                        h_confs = helmet_results[0].boxes.conf.cpu().numpy()

                        for bbox, obj_id, cls_id, conf in zip(h_boxes, h_ids, h_classes, h_confs):
                            x1, y1, x2, y2 = map(int, bbox)
                            class_name = names.get(cls_id, "unknown")
                            
                            is_helmet_violation = "helmet" not in class_name.lower() or "no" in class_name.lower() or class_name.lower() == "without_helmet"
                            
                            # Debounce mechanism: +2 points for violation, -1 point for normal, max 30 points
                            if is_helmet_violation:
                                helmet_violation_scores[obj_id] = min(30, helmet_violation_scores.get(obj_id, 0) + 2)
                            else:
                                helmet_violation_scores[obj_id] = max(0, helmet_violation_scores.get(obj_id, 0) - 1)
                                
                            # Ngưỡng xác nhận vi phạm (vd: khoảng 5-10 frame liên tiếp)
                            has_consistent_violation = helmet_violation_scores[obj_id] >= 10
                            
                            if has_consistent_violation:
                                if obj_id not in reported_ids:
                                    reported_ids.add(obj_id)
                                    title_text = f"Không đội mũ: {class_name} ({(conf*100):.1f}%) - ID #{obj_id}"
                                    all_violations.append({
                                        "time_sec": frame_count / fps,
                                        "severity": "high", 
                                        "icon": "⚠️",
                                        "title": title_text, 
                                        "source": "YOLO Helmet",
                                        "vehicle_type": "no_helmet"
                                    })
                            
                            frame_bboxes.append({
                                "id": int(obj_id),
                                "bbox": [x1, y1, x2, y2],
                                "class_name": class_name,
                                "conf": float(conf),
                                "is_violation": bool(has_consistent_violation),
                                "type": "helmet"
                            })

                # 2. Red Light Detection - run in thread pool
                if red_light_detector and traffic_light_sim and vehicle_model:
                    current_video_time = frame_count / fps
                    light_state, time_left = traffic_light_sim.get_current_light(current_video_time)
                    
                    # Track vehicles on the original clean frame
                    vehicle_results = await loop.run_in_executor(
                        model_executor,
                        lambda f=frame: vehicle_model.track(f, persist=True, verbose=False, classes=[0, 1, 2, 3, 4])
                    )
                    
                    if vehicle_results[0].boxes.id is not None:
                        v_boxes = vehicle_results[0].boxes.xyxy.cpu().numpy()
                        v_ids = vehicle_results[0].boxes.id.cpu().numpy().astype(int)
                        v_classes = vehicle_results[0].boxes.cls.cpu().numpy().astype(int)
                        v_confs = vehicle_results[0].boxes.conf.cpu().numpy()
                        
                        for bbox, track_id, class_id, conf in zip(v_boxes, v_ids, v_classes, v_confs):
                            x1, y1, x2, y2 = map(int, bbox)
                            
                            is_rl_violation = red_light_detector.check_line_crossing(
                                vehicle_id=track_id,
                                bbox=(x1, y1, x2, y2),
                                frame_id=frame_count,
                                class_id=class_id,
                                traffic_light_state=light_state
                            )
                            
                            if is_rl_violation:
                                vehicle_type = vehicle_names.get(class_id, "vehicle")
                                all_violations.append({
                                    "time_sec": frame_count / fps,
                                    "severity": "critical",
                                    "icon": "🔴",
                                    "title": f"Vượt đèn đỏ: {vehicle_type} #{track_id}",
                                    "source": "YOLO Traffic",
                                    "vehicle_type": vehicle_type
                                })
                            
                            is_already_violated = track_id in red_light_detector.violated_ids
                            
                            frame_bboxes.append({
                                "id": int(track_id),
                                "bbox": [x1, y1, x2, y2],
                                "class_name": f"V:{track_id}",
                                "conf": float(conf),
                                "is_violation": bool(is_already_violated),
                                "just_violated": bool(is_rl_violation),
                                "type": "vehicle"
                            })
            
            # Save frame data
            all_frames_data.append({
                "time_sec": frame_count / fps,
                "light_state": light_state,
                "time_left": time_left,
                "bboxes": frame_bboxes
            })
            
            # Send progress report every 5 frames to keep WS alive
            if frame_count % 5 == 0:
                progress = min(int((frame_count / total_frames) * 100), 99) if total_frames > 0 else 50
                try:
                    await websocket.send_json({"status": "processing", "progress": progress})
                except Exception:
                    print(f"[WS] Client disconnected during processing at frame {frame_count}")
                    return
                await asyncio.sleep(0.01)

        # Compute final stats
        total_red_light = len(red_light_detector.violations) if red_light_detector else 0
        no_helmet = len(reported_ids)
        total_violations = total_red_light + no_helmet
        vehicle_counts = dict(Counter(v["type"] for v in red_light_detector.violations)) if red_light_detector else {}

        stats_data = {
            "total_violations": total_violations,
            "no_helmet_count": no_helmet,
            "vehicle_counts": vehicle_counts
        }

        # Send final completed data
        await websocket.send_json({
            "status": "completed",
            "result": {
                "frames": all_frames_data,
                "violations": all_violations,
                "stats": stats_data
            }
        })
            
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected for video {filename}")
    except Exception as e:
        print(f"[WS] Error processing {filename}: {e}")
        traceback.print_exc()
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
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
