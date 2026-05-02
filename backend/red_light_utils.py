import time
import cv2
import numpy as np
from collections import defaultdict

class RedLightViolationDetector:
    def __init__(self):
        self.vehicle_states = defaultdict(lambda: {"crossed": False, "last_side": None})
        self.violations = []
        self.violated_ids = set()  
        self.line_start = None
        self.line_end = None
        self.class_names = {
            0: 'car',
            1: 'bus',
            2: 'truck',
            3: 'motorcycle',
            4: 'bicycle'
        }
    
    def set_detection_line(self, start_point, end_point):
        """Set coordinates for the detection line"""
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
        # Cross product to determine which side of the line the point is on
        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)
        return cross
    
    def check_line_crossing(self, vehicle_id, bbox, frame_id, class_id, traffic_light_state):
        center = self.get_vehicle_center(bbox)
        position = self.point_position_relative_to_line(center)
        
        # Determine side based on sign of cross product
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
                        "type": self.class_names.get(class_id, "unknown")
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

class TrafficLightSimulation:
    def __init__(self):
        self.states = ["green", "red"]
        self.durations = [10, 10]
        self.current_state_idx = 0
        self.start_time = 0.0

    def get_current_light(self, current_time):
        elapsed = current_time - self.start_time
        if elapsed > self.durations[self.current_state_idx]:
            self.current_state_idx = (self.current_state_idx + 1) % len(self.states)
            self.start_time = current_time
            elapsed = 0
        return self.states[self.current_state_idx], int(self.durations[self.current_state_idx] - elapsed)
