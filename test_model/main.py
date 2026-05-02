from typing import Counter

from ultralytics import YOLO
import cv2
import numpy as np
from red_light_violations_detector import RedLightViolationDetector
from red_light_violations_detector import LineDrawer
from traffic_light_simulation import traffic_light



def main():
    model = YOLO("best_v6.pt")
    
    detector = RedLightViolationDetector()
    
    cap = cv2.VideoCapture("D:\\cntt\\Năm_3\\Thuc_Tap_Co_So\\ảnh_test\\video_stopline_2.mp4")
    
    ret, first_frame = cap.read()
    if ret:
        drawer = LineDrawer(first_frame)
        line_start, line_end = drawer.draw()
        detector.set_detection_line(line_start, line_end)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    frame_id = 0

    traffic_light_sim = traffic_light()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model.track(frame, persist=True, classes=[0, 1, 2, 3, 4]) 
        
        traffic_light_state, time_remaining = traffic_light_sim.get_current_light()

        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            classes_id = results[0].boxes.cls.cpu().numpy().astype(int)
            
            for bbox, track_id, class_id in zip(boxes, track_ids, classes_id):
                x1, y1, x2, y2 = map(int, bbox)
                
                is_violation = detector.check_line_crossing(
                    vehicle_id=track_id,
                    bbox=(x1, y1, x2, y2),
                    frame_id=frame_id,
                    class_id=class_id,
                    traffic_light_state=traffic_light_state
                )
                
                color = (0, 0, 255) if track_id in detector.violated_ids else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"ID:{track_id}", (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                if is_violation:
                    cv2.putText(frame, "VIOLATION!", (x1, y2+20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        detector.draw_detection_zone(frame, traffic_light_state)
        
        cv2.putText(frame, f"Violations: {len(detector.violations)}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f'state light: {traffic_light_state} {time_remaining}s',
                   (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        counter = Counter(v["type"] for v in detector.violations)
        y_offset = 100
        for vehicle_type, count in counter.items():
            cv2.putText(frame, f"{vehicle_type}: {count}",
                        (10, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2)
            y_offset += 30
        
        cv2.imshow("Red Light Violation Detection", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        frame_id += 1
    
    cap.release()
    cv2.destroyAllWindows()
    
    print(f"\nTổng số vi phạm: {len(detector.violations)}")
    for v in detector.violations:
        print(f"  - Vehicle ID {v['vehicle_id']} tại frame {v['frame_id']}")

if __name__ == "__main__":
    main() 