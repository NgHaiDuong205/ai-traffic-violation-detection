import os
import cv2
import numpy as np
import base64
import asyncio
import uuid
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
from red_light_service import RedLightService
from dedupe_utils import ViolationDeduper, is_overlapping_bbox
import json
from collections import Counter

from config import (
    HELMET_MODEL_PATH,
    VEHICLE_MODEL_PATH,
    TEMP_DIR,
    MODEL_EXECUTOR_MAX_WORKERS,
    DUPLICATE_BOX_IOU_THRESHOLD,
    VIOLATION_DEDUPE_IOU_THRESHOLD,
    VIOLATION_DEDUPE_TIME_WINDOW_SEC,
    VIOLATION_DEDUPE_CENTER_DISTANCE_PX,
    HELMET_VIOLATION_SCORE_INCREMENT,
    HELMET_COMPLIANCE_SCORE_DECREMENT,
    HELMET_VIOLATION_SCORE_THRESHOLD,
    HELMET_VIOLATION_SCORE_MAX,
    VEHICLE_DETECT_CLASSES,
    DEFAULT_FPS,
    FRAME_SKIP,
    FRAME_STORAGE_INTERVAL_SEC,
    FRAME_STREAM_BATCH_SIZE,
    WS_PROGRESS_FRAME_INTERVAL,
    WS_PROGRESS_SLEEP_SEC,
    TRAFFIC_LIGHT_GREEN_DURATION_SEC,
    TRAFFIC_LIGHT_RED_DURATION_SEC,
    MAX_IMAGE_UPLOAD_BYTES,
    MAX_VIDEO_UPLOAD_BYTES,
    UPLOAD_CHUNK_SIZE,
    ALLOWED_VIDEO_EXTENSIONS,
)

# Thread pool for blocking model inference
model_executor = ThreadPoolExecutor(max_workers=MODEL_EXECUTOR_MAX_WORKERS)
logger = logging.getLogger("ai_traffic_api")

app = FastAPI(title="AI Traffic Violation API")

# Setup CORS to allow React Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"Loading helmet model from: {HELMET_MODEL_PATH}")
helmet_model = YOLO(str(HELMET_MODEL_PATH)) if HELMET_MODEL_PATH.exists() else None

print(f"Loading vehicle model from: {VEHICLE_MODEL_PATH}")
vehicle_model = YOLO(str(VEHICLE_MODEL_PATH)) if VEHICLE_MODEL_PATH.exists() else None

# For backward compatibility with existing code
model = helmet_model


def _sanitize_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    normalized = filename.strip()
    safe_name = os.path.basename(normalized)
    if safe_name != normalized or "/" in normalized or "\\" in normalized:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return safe_name


def _resolve_temp_video_path(filename: str) -> str:
    safe_name = _sanitize_filename(filename)
    resolved_path = (TEMP_DIR / safe_name).resolve()
    temp_root = TEMP_DIR.resolve()
    if resolved_path.parent != temp_root:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return str(resolved_path)

@app.post("/api/detect")
async def detect_image(file: UploadFile = File(...)):
    if not model:
        raise HTTPException(status_code=503, detail="Helmet model not loaded")

    contents = await file.read(MAX_IMAGE_UPLOAD_BYTES + 1)
    if len(contents) > MAX_IMAGE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds upload size limit")
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file provided")

    try:
        results = model(img)
    except Exception:
        logger.exception("Helmet inference failed")
        raise HTTPException(status_code=500, detail="Image inference failed")

    res = results[0]
    
    violations = []

    annotated_img = res.plot()
    

    names = model.names
    valid_boxes = []
    existing_coords = []

    # Higher confidence boxes first so overlapping duplicates keep the best detection.
    detections = sorted(
        res.boxes,
        key=lambda b: float(b.conf[0]),
        reverse=True,
    )

    for box in detections:
        cls_id = int(box.cls[0])
        class_name = names[cls_id]
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        coords = (x1, y1, x2, y2)

        if is_overlapping_bbox(
            coords,
            existing_coords,
            DUPLICATE_BOX_IOU_THRESHOLD,
            VIOLATION_DEDUPE_CENTER_DISTANCE_PX,
        ):
            continue

        existing_coords.append(coords)
        valid_boxes.append({
            "class_name": class_name,
            "coords": coords,
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

    try:
        ok, buffer = cv2.imencode('.jpg', annotated_img)
        if not ok:
            raise ValueError("cv2.imencode returned false")
    except Exception:
        logger.exception("Failed encoding detection image")
        raise HTTPException(status_code=500, detail="Failed to encode detection image")

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

TEMP_DIR.mkdir(parents=True, exist_ok=True)


def process_frame_helmet(
    loop,
    frame,
):
    if not helmet_model:
        return None

    return loop.run_in_executor(
        model_executor,
        lambda f=frame: helmet_model.track(f, persist=True, verbose=False, tracker="bytetrack.yaml")
    )


async def process_helmet_result(
    helmet_results_future,
    frame_count,
    fps,
    names,
    helmet_deduper,
    helmet_violation_scores,
    violations,
):
    frame_bboxes = []
    try:
        helmet_results = await helmet_results_future
    except Exception:
        logger.exception("Helmet tracking failed")
        raise HTTPException(status_code=500, detail="Helmet tracking failed")

    if helmet_results[0].boxes.id is None:
        return frame_bboxes

    h_boxes = helmet_results[0].boxes.xyxy.cpu().numpy()
    h_ids = helmet_results[0].boxes.id.cpu().numpy().astype(int)
    h_classes = helmet_results[0].boxes.cls.cpu().numpy().astype(int)
    h_confs = helmet_results[0].boxes.conf.cpu().numpy()

    for bbox, obj_id, cls_id, conf in zip(h_boxes, h_ids, h_classes, h_confs):
        x1, y1, x2, y2 = map(int, bbox)
        class_name = names.get(cls_id, "unknown")

        is_helmet_violation = (
            "helmet" not in class_name.lower()
            or "no" in class_name.lower()
            or class_name.lower() == "without_helmet"
        )

        if is_helmet_violation:
            helmet_violation_scores[obj_id] = min(
                HELMET_VIOLATION_SCORE_MAX,
                helmet_violation_scores.get(obj_id, 0) + HELMET_VIOLATION_SCORE_INCREMENT,
            )
        else:
            helmet_violation_scores[obj_id] = max(
                0,
                helmet_violation_scores.get(obj_id, 0) - HELMET_COMPLIANCE_SCORE_DECREMENT,
            )

        has_consistent_violation = helmet_violation_scores[obj_id] >= HELMET_VIOLATION_SCORE_THRESHOLD
        time_sec = frame_count / fps
        bbox = (x1, y1, x2, y2)

        if has_consistent_violation and helmet_deduper.should_report(obj_id, bbox, time_sec):
            helmet_deduper.record(obj_id, bbox, time_sec)
            title_text = f"Không đội mũ: {class_name} ({(conf*100):.1f}%) - ID #{obj_id}"
            violations.append({
                "time_sec": time_sec,
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

    return frame_bboxes


def build_frame_payload(frame_count, fps, light_state, time_left, frame_bboxes):
    return {
        "time_sec": frame_count / fps,
        "light_state": light_state,
        "time_left": time_left,
        "bboxes": frame_bboxes
    }


def should_store_frame(frame_payload, last_stored_time_sec, last_light_state, has_new_violation):
    time_sec = frame_payload["time_sec"]
    if last_stored_time_sec is None:
        return True
    if has_new_violation:
        return True
    if frame_payload.get("bboxes") and any(b.get("just_violated") for b in frame_payload["bboxes"]):
        return True
    light_state = frame_payload["light_state"]
    if light_state != "unknown" and light_state != last_light_state:
        return True
    if time_sec - last_stored_time_sec >= FRAME_STORAGE_INTERVAL_SEC:
        return True
    return False


async def flush_frame_batch(websocket, batch, current_violations=None):
    if not batch:
        return
    payload = {"status": "frame_batch", "frames": batch}
    if current_violations is not None:
        payload["violations"] = current_violations
    await websocket.send_json(payload)
    batch.clear()


def build_stats_payload(red_light_service, helmet_deduper):
    total_red_light = red_light_service.violation_count() if red_light_service else 0
    no_helmet = helmet_deduper.count() if helmet_deduper else 0
    total_violations = total_red_light + no_helmet
    vehicle_counts = (
        dict(Counter(v["vehicle_type"] for v in red_light_service.violations))
        if red_light_service else {}
    )

    return {
        "total_violations": total_violations,
        "no_helmet_count": no_helmet,
        "vehicle_counts": vehicle_counts
    }

@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)):
    original_name = _sanitize_filename(file.filename or "")
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video extension: {ext or 'none'}",
        )

    filename = f"video_{uuid.uuid4().hex}{ext}"
    filepath = _resolve_temp_video_path(filename)
    total_bytes = 0

    try:
        with open(filepath, "wb") as buffer:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_VIDEO_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Video exceeds upload size limit")
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    except Exception:
        logger.exception("Failed to store uploaded video")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise HTTPException(status_code=500, detail="Failed to save uploaded video")
    finally:
        await file.close()

    return {"success": True, "filename": filename}

@app.get("/api/video_first_frame/{filename}")
async def get_video_first_frame(filename: str):
    filepath = _resolve_temp_video_path(filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Video not found")
    
    cap = cv2.VideoCapture(filepath)
    if not cap.isOpened():
        cap.release()
        raise HTTPException(status_code=500, detail="Could not open video")

    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        raise HTTPException(status_code=500, detail="Could not read video")
        
    ok, buffer = cv2.imencode('.jpg', frame)
    if not ok:
        raise HTTPException(status_code=500, detail="Could not encode video frame")

    base64_img = base64.b64encode(buffer).decode('utf-8')
    return {"frame": f"data:image/jpeg;base64,{base64_img}"}

@app.websocket("/api/ws/video/{filename}")
async def websocket_video_endpoint(websocket: WebSocket, filename: str, line_coords: str = None):
    await websocket.accept()

    try:
        filepath = _resolve_temp_video_path(filename)
    except HTTPException as exc:
        await websocket.send_json({"error": exc.detail})
        await websocket.close()
        return

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

    red_light_service = RedLightService(
        vehicle_model=vehicle_model,
        vehicle_names=vehicle_names,
        vehicle_detect_classes=VEHICLE_DETECT_CLASSES,
        model_executor=model_executor,
        green_duration_sec=TRAFFIC_LIGHT_GREEN_DURATION_SEC,
        red_duration_sec=TRAFFIC_LIGHT_RED_DURATION_SEC,
        dedupe_iou_threshold=VIOLATION_DEDUPE_IOU_THRESHOLD,
        dedupe_time_window_sec=VIOLATION_DEDUPE_TIME_WINDOW_SEC,
        dedupe_center_distance_px=VIOLATION_DEDUPE_CENTER_DISTANCE_PX,
    )
    if line_coords and vehicle_model:
        try:
            coords = json.loads(line_coords)
            red_light_service.configure_detection_line(coords)
        except Exception as e:
            print(f"Error parsing line_coords: {e}")

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = DEFAULT_FPS
        
        print(f"[WS] Starting processing: {filename}, total_frames={total_frames}, fps={fps}")
        
        frame_skip = FRAME_SKIP
        frame_count = 0
        helmet_deduper = ViolationDeduper(
            iou_threshold=VIOLATION_DEDUPE_IOU_THRESHOLD,
            time_window_sec=VIOLATION_DEDUPE_TIME_WINDOW_SEC,
            center_distance_px=VIOLATION_DEDUPE_CENTER_DISTANCE_PX,
        )
        helmet_violation_scores = {} # Track score to prevent flickering / false positives

        all_violations = []
        pending_frames = []
        last_stored_time_sec = None
        last_light_state = None

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
            violations_before = len(all_violations)

            if helmet_model:
                helmet_future = process_frame_helmet(
                    loop=loop,
                    frame=frame,
                )
                if helmet_future:
                    frame_bboxes.extend(await process_helmet_result(
                        helmet_results_future=helmet_future,
                        frame_count=frame_count,
                        fps=fps,
                        names=names,
                        helmet_deduper=helmet_deduper,
                        helmet_violation_scores=helmet_violation_scores,
                        violations=all_violations,
                    ))

            (
                vehicle_bboxes,
                light_state,
                time_left,
                new_rl_violations,
            ) = await red_light_service.process_frame(
                loop=loop,
                frame=frame,
                frame_count=frame_count,
                fps=fps,
            )
            all_violations.extend(new_rl_violations)
            frame_bboxes.extend(vehicle_bboxes)

            frame_payload = build_frame_payload(
                frame_count=frame_count,
                fps=fps,
                light_state=light_state,
                time_left=time_left,
                frame_bboxes=frame_bboxes,
            )
            has_new_violation = len(all_violations) > violations_before

            if should_store_frame(
                frame_payload,
                last_stored_time_sec,
                last_light_state,
                has_new_violation,
            ):
                pending_frames.append(frame_payload)
                last_stored_time_sec = frame_payload["time_sec"]
                last_light_state = light_state

                if len(pending_frames) >= FRAME_STREAM_BATCH_SIZE:
                    try:
                        await flush_frame_batch(websocket, pending_frames, current_violations=all_violations)
                    except Exception:
                        print(f"[WS] Client disconnected during processing at frame {frame_count}")
                        return
            
            if frame_count % WS_PROGRESS_FRAME_INTERVAL == 0:
                progress = min(int((frame_count / total_frames) * 100), 99) if total_frames > 0 else 50
                try:
                    await websocket.send_json({"status": "processing", "progress": progress})
                except Exception:
                    print(f"[WS] Client disconnected during processing at frame {frame_count}")
                    return
                await asyncio.sleep(WS_PROGRESS_SLEEP_SEC)

        await flush_frame_batch(websocket, pending_frames)

        stats_data = build_stats_payload(
            red_light_service=red_light_service,
            helmet_deduper=helmet_deduper,
        )

        await websocket.send_json({
            "status": "completed",
            "result": {
                "violations": all_violations,
                "stats": stats_data,
            }
        })
            
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected for video {filename}")
    except HTTPException as e:
        logger.exception("WebSocket video processing failed")
        try:
            await websocket.send_json({"error": e.detail})
        except Exception:
            pass
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
