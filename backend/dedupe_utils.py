"""Shared helpers to avoid duplicate violation alerts for the same object."""


def bbox_iou(box_a, box_b):
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    x_left = max(ax1, bx1)
    y_top = max(ay1, by1)
    x_right = min(ax2, bx2)
    y_bottom = min(ay2, by2)
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0
    intersection = (x_right - x_left) * (y_bottom - y_top)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    if area_a <= 0 or area_b <= 0:
        return 0.0
    return intersection / min(area_a, area_b)


def bbox_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def center_distance(box_a, box_b):
    ax, ay = bbox_center(box_a)
    bx, by = bbox_center(box_b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def is_overlapping_bbox(bbox, existing_bboxes, iou_threshold, center_distance_px=None):
    for existing in existing_bboxes:
        if bbox_iou(bbox, existing) > iou_threshold:
            return True
        if center_distance_px is not None and center_distance(bbox, existing) < center_distance_px:
            return True
    return False


class ViolationDeduper:
    """Track reported object IDs and recent spatial regions to suppress duplicates."""

    def __init__(self, iou_threshold, time_window_sec, center_distance_px=None, enable_spatial=True):
        self.iou_threshold = iou_threshold
        self.time_window_sec = time_window_sec
        self.center_distance_px = center_distance_px
        self.enable_spatial = enable_spatial
        self.reported_ids = set()
        self._recent = []

    def _prune(self, current_time_sec):
        cutoff = current_time_sec - self.time_window_sec
        self._recent = [entry for entry in self._recent if entry["time_sec"] >= cutoff]

    def is_spatial_duplicate(self, bbox, time_sec):
        self._prune(time_sec)
        recent_bboxes = [entry["bbox"] for entry in self._recent]
        return is_overlapping_bbox(
            bbox,
            recent_bboxes,
            self.iou_threshold,
            self.center_distance_px,
        )

    def should_report(self, obj_id, bbox, time_sec):
        if obj_id in self.reported_ids:
            return False
        if self.enable_spatial and self.is_spatial_duplicate(bbox, time_sec):
            return False
        return True

    def record(self, obj_id, bbox, time_sec):
        self.reported_ids.add(obj_id)
        self._prune(time_sec)
        self._recent.append(
            {
                "id": obj_id,
                "bbox": [int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])],
                "time_sec": time_sec,
            }
        )

    def count(self):
        return len(self.reported_ids)
