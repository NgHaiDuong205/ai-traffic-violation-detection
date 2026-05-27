import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


def _path_from_env(env_key: str, default_relative: str) -> Path:
    override = os.getenv(env_key)
    if override:
        return Path(override)
    return PROJECT_ROOT / default_relative


# --- Model paths ---
HELMET_MODEL_PATH = _path_from_env(
    "HELMET_MODEL_PATH",
    "ai_modules/helmet_detect/weights/best3.pt",
)
VEHICLE_MODEL_PATH = _path_from_env(
    "VEHICLE_MODEL_PATH",
    "ai_modules/vehicle_detect/weights/best_v6.pt",
)

# --- Runtime dirs ---
TEMP_DIR = BACKEND_DIR / "temp_videos"

# --- Inference ---
MODEL_EXECUTOR_MAX_WORKERS = int(os.getenv("MODEL_EXECUTOR_MAX_WORKERS", "2"))
VEHICLE_DETECT_CLASSES = [0, 1, 2, 3, 4]
DEFAULT_FPS = int(os.getenv("DEFAULT_FPS", "30"))

# --- Image detection ---
DUPLICATE_BOX_IOU_THRESHOLD = float(os.getenv("DUPLICATE_BOX_IOU_THRESHOLD", "0.4"))

# --- Violation deduplication (video: ID swap / spatial overlap) ---
VIOLATION_DEDUPE_IOU_THRESHOLD = float(
    os.getenv("VIOLATION_DEDUPE_IOU_THRESHOLD", str(DUPLICATE_BOX_IOU_THRESHOLD))
)
VIOLATION_DEDUPE_TIME_WINDOW_SEC = float(os.getenv("VIOLATION_DEDUPE_TIME_WINDOW_SEC", "8.0"))
VIOLATION_DEDUPE_CENTER_DISTANCE_PX = int(os.getenv("VIOLATION_DEDUPE_CENTER_DISTANCE_PX", "100"))

# --- Helmet violation scoring (temporal smoothing) ---
HELMET_VIOLATION_SCORE_INCREMENT = int(os.getenv("HELMET_VIOLATION_SCORE_INCREMENT", "2"))
HELMET_COMPLIANCE_SCORE_DECREMENT = int(os.getenv("HELMET_COMPLIANCE_SCORE_DECREMENT", "1"))
HELMET_VIOLATION_SCORE_THRESHOLD = int(os.getenv("HELMET_VIOLATION_SCORE_THRESHOLD", "10"))
HELMET_VIOLATION_SCORE_MAX = int(os.getenv("HELMET_VIOLATION_SCORE_MAX", "30"))

# --- Video processing ---
FRAME_SKIP = int(os.getenv("FRAME_SKIP", "1"))
# Min seconds between stored overlay frames (sparse sampling)
FRAME_STORAGE_INTERVAL_SEC = float(os.getenv("FRAME_STORAGE_INTERVAL_SEC", "0.5"))
# Flush stored frames to client in batches (backend does not hold entire video)
FRAME_STREAM_BATCH_SIZE = int(os.getenv("FRAME_STREAM_BATCH_SIZE", "4"))
WS_PROGRESS_FRAME_INTERVAL = int(os.getenv("WS_PROGRESS_FRAME_INTERVAL", "5"))
WS_PROGRESS_SLEEP_SEC = float(os.getenv("WS_PROGRESS_SLEEP_SEC", "0.01"))

# --- Upload safety limits ---
MAX_IMAGE_UPLOAD_BYTES = int(os.getenv("MAX_IMAGE_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_VIDEO_UPLOAD_BYTES = int(os.getenv("MAX_VIDEO_UPLOAD_BYTES", str(500 * 1024 * 1024)))
UPLOAD_CHUNK_SIZE = int(os.getenv("UPLOAD_CHUNK_SIZE", str(1024 * 1024)))
ALLOWED_VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
}

# --- Traffic light simulation ---
TRAFFIC_LIGHT_GREEN_DURATION_SEC = int(os.getenv("TRAFFIC_LIGHT_GREEN_DURATION_SEC", "10"))
TRAFFIC_LIGHT_RED_DURATION_SEC = int(os.getenv("TRAFFIC_LIGHT_RED_DURATION_SEC", "10"))
