import time

class traffic_light:

    def __init__(self):
        self.states = ["green", "red"]
        self.durations = [10, 10]
        self.current_state_idx = 0
        self.start_time = time.time()
    def get_current_light(self):

        elapsed = time.time() - self.start_time
        
        if elapsed > self.durations[self.current_state_idx]:
            self.current_state_idx = (self.current_state_idx + 1) % len(self.states)
            self.start_time = time.time()
            
        return self.states[self.current_state_idx], int(self.durations[self.current_state_idx] - elapsed)