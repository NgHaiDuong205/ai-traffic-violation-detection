import cv2
import numpy as np
from collections import defaultdict

classNames={
    0: 'car',
    1: 'bus',
    2: 'truck',
    3: 'motorcycle',
    4: 'bicycle'
}
class RedLightViolationDetector:
    def __init__(self):
        self.vehicle_states = defaultdict(lambda: {"crossed": False, "last_side": None})
        
        self.violations = []
        self.violated_ids = set()  
        
        self.line_start = None
        self.line_end = None
        
    
    def set_detection_line(self, start_point, end_point):
        """Đặt tọa độ vạch kẻ"""
        self.line_start = start_point
        self.line_end = end_point
    
    def get_vehicle_center(self, bbox):
        x1, y1, x2, y2 = bbox
        center_x = (x1 + x2) // 2
        bottom_y = y2
        return (center_x, bottom_y)
    
    def point_position_relative_to_line(self, point):
       
        if self.line_start is None or self.line_end is None:
            return 0
        
        x, y = point
        x1, y1 = self.line_start
        x2, y2 = self.line_end
        
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        return cross
    
    def check_line_crossing(self, vehicle_id, bbox, frame_id, class_id, traffic_light_state):
    
        center = self.get_vehicle_center(bbox)
        position = self.point_position_relative_to_line(center)
        
        current_side = "before" if position >= 0 else "after"
        
        state = self.vehicle_states[vehicle_id]
        previous_side = state["last_side"]
        
        state["last_side"] = current_side
        
        if previous_side == "before" and current_side == "after":
            if not state["crossed"]:
                state["crossed"] = True
                
                if traffic_light_state == "red":
                    violation_info = {
                        "vehicle_id": vehicle_id,
                        "frame_id": frame_id,
                        "position": center,
                        "bbox": bbox,
                        "type": classNames.get(class_id, "unknown")
                    }
                    self.violations.append(violation_info)
                    self.violated_ids.add(vehicle_id)
                    return True
        
        return False
    
    def draw_detection_zone(self, frame, traffic_light_state):
        if self.line_start is None or self.line_end is None:
            return frame
        
        color = (0, 0, 255) if traffic_light_state == "red" else (255, 255, 255)
        cv2.line(frame, self.line_start, self.line_end, color, 3)
        
        return frame


class LineDrawer:
    
    def __init__(self, frame):
        self.frame = frame.copy()
        self.original = frame.copy()
        self.points = []
        self.drawing = False
    
    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.points.append((x, y))
            cv2.circle(self.frame, (x, y), 5, (0, 255, 0), -1)
            
            if len(self.points) == 2:
                cv2.line(self.frame, self.points[0], self.points[1], (255, 255, 255), 2)
    
    def draw(self):
        cv2.namedWindow("Draw Detection Line")
        cv2.setMouseCallback("Draw Detection Line", self.mouse_callback)
        
        print("Click 2 điểm để vẽ vạch kẻ. Nhấn 'q' để xác nhận, 'r' để reset.")
        
        while True:
            cv2.imshow("Draw Detection Line", self.frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q') and len(self.points) == 2:
                break
            elif key == ord('r'):
                self.frame = self.original.copy()
                self.points = []
        
        cv2.destroyAllWindows()
        return self.points[0], self.points[1] if len(self.points) == 2 else (None, None)
