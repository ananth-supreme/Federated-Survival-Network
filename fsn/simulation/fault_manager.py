import numpy as np
from typing import List, Optional
from fsn.constants import FAULT_THRESHOLD_DEG

class FaultManager:
    """
    Manages fault injection and detection for the satellite formation.
    Uses a simple CUSUM-like detector for attitude error spikes.
    """

    def __init__(self, window_size: int = 15):
        self.window_size = window_size
        self.history = []
        self.fault_active = False
        self.fault_detected = False

    def check_fault(self, attitude_error: float) -> bool:
        """
        Monitors attitude error and returns True if a fault is detected.
        """
        self.history.append(attitude_error)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        if len(self.history) < self.window_size:
            return False

        # Simple threshold-based detection for the demo
        # A more complex CUSUM could be used here with ruptures
        avg_error = np.mean(self.history)
        if avg_error > FAULT_THRESHOLD_DEG and not self.fault_detected:
            self.fault_detected = True
            return True

        return False

    def inject_fault(self):
        self.fault_active = True

    def reset(self):
        self.history = []
        self.fault_active = False
        self.fault_detected = False
