from fastapi import HTTPException

from dedupe_utils import ViolationDeduper
from red_light_utils import RedLightViolationDetector, TrafficLightSimulation


class RedLightService:
    def __init__(
        self,
        vehicle_model,
        vehicle_names,
        vehicle_detect_classes,
        model_executor,
        green_duration_sec,
        red_duration_sec,
        dedupe_iou_threshold=0.4,
        dedupe_time_window_sec=8.0,
        dedupe_center_distance_px=100,
    ):
        self.vehicle_model = vehicle_model
        self.vehicle_names = vehicle_names or {}
        self.vehicle_detect_classes = vehicle_detect_classes
        self.model_executor = model_executor
        self.green_duration_sec = green_duration_sec
        self.red_duration_sec = red_duration_sec
        self.detector = None
        self.traffic_light = None
        self.violations = []
        self.deduper = ViolationDeduper(
            iou_threshold=dedupe_iou_threshold,
            time_window_sec=dedupe_time_window_sec,
            center_distance_px=dedupe_center_distance_px,
        )

    def configure_detection_line(self, line_coords):
        if not line_coords or not self.vehicle_model:
            self.detector = None
            self.traffic_light = None
            return
        self.detector = RedLightViolationDetector()
        self.detector.set_detection_line(
            (line_coords["x1"], line_coords["y1"]),
            (line_coords["x2"], line_coords["y2"]),
        )
        self.traffic_light = TrafficLightSimulation(
            green_duration=self.green_duration_sec,
            red_duration=self.red_duration_sec,
        )

    async def process_frame(self, loop, frame, frame_count, fps):
        frame_bboxes = []
        if not (self.detector and self.traffic_light and self.vehicle_model):
            return frame_bboxes, "unknown", 0, []

        current_video_time = frame_count / fps
        light_state, time_left = self.traffic_light.get_current_light(current_video_time)

        try:
            vehicle_results = await loop.run_in_executor(
                self.model_executor,
                lambda f=frame: self.vehicle_model.track(
                    f,
                    persist=True,
                    verbose=False,
                    classes=self.vehicle_detect_classes,
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Vehicle tracking failed") from exc

        if vehicle_results[0].boxes.id is None:
            return frame_bboxes, light_state, time_left, []

        v_boxes = vehicle_results[0].boxes.xyxy.cpu().numpy()
        v_ids = vehicle_results[0].boxes.id.cpu().numpy().astype(int)
        v_classes = vehicle_results[0].boxes.cls.cpu().numpy().astype(int)
        v_confs = vehicle_results[0].boxes.conf.cpu().numpy()

        new_violations = []
        for bbox, track_id, class_id, conf in zip(v_boxes, v_ids, v_classes, v_confs):
            x1, y1, x2, y2 = map(int, bbox)

            bbox = (x1, y1, x2, y2)
            time_sec = frame_count / fps

            is_rl_violation = self.detector.check_line_crossing(
                vehicle_id=track_id,
                bbox=bbox,
                frame_id=frame_count,
                class_id=class_id,
                traffic_light_state=light_state,
            )

            should_report = is_rl_violation and self.deduper.should_report(
                track_id, bbox, time_sec
            )
            if should_report:
                self.deduper.record(track_id, bbox, time_sec)
                vehicle_type = self.vehicle_names.get(class_id, "vehicle")
                violation = {
                    "time_sec": time_sec,
                    "severity": "critical",
                    "icon": "🔴",
                    "title": f"Vượt đèn đỏ: {vehicle_type} #{track_id}",
                    "source": "YOLO Traffic",
                    "vehicle_type": vehicle_type,
                }
                self.violations.append(violation)
                new_violations.append(violation)

            is_already_violated = (
                track_id in self.detector.violated_ids
                or track_id in self.deduper.reported_ids
            )
            frame_bboxes.append(
                {
                    "id": int(track_id),
                    "bbox": [x1, y1, x2, y2],
                    "class_name": f"V:{track_id}",
                    "conf": float(conf),
                    "is_violation": bool(is_already_violated),
                    "just_violated": bool(should_report),
                    "type": "vehicle",
                }
            )

        return frame_bboxes, light_state, time_left, new_violations

    def violation_count(self):
        return self.deduper.count()

