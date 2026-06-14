import numpy as np
from typing import Dict, Tuple
from fsn.constants import MEAN_MOTION_N, SAT_B_START_POS, SAT_C_START_POS

class ReconfigController:
    """
    Simulates the Formation Reconfiguration Controller.
    Actively maneuvers satellites back to their target nominal positions.
    """

    def __init__(self):
        # High performance gains for the demo to ensure visible recovery
        self.kp = 0.15
        self.kd = 0.4
        
        # Nominal target positions in the Hill Frame
        self.nominal_targets = {
            "SAT_A": np.array([0.0, 0.0, 0.0]),
            "SAT_B": np.array(SAT_B_START_POS),
            "SAT_C": np.array(SAT_C_START_POS)
        }

    def get_actions(self, sat_states: Dict[str, np.ndarray], recovery_active: bool) -> Dict[str, np.ndarray]:
        """
        Calculates DV commands for all satellites to return to nominal formation.
        """
        actions = {}
        if not recovery_active:
            return actions

        for sat_name, state in sat_states.items():
            # Sat-A stays in safe mode — no maneuvers commanded on the blind satellite
            if sat_name == "SAT_A":
                continue

            pos = state[:3]
            vel = state[3:]
            
            target_pos = self.nominal_targets[sat_name]
            # In Hill frame, natural motion at target means relative velocity should be zero
            # (assuming x=0 for chief and deputies follow bounded motion)
            target_vel = np.zeros(3)
            
            # Position and Velocity Errors
            pos_error = target_pos - pos
            vel_error = target_vel - vel 
            
            # Control Law: u = Kp*e + Kd*edot
            accel = self.kp * pos_error + self.kd * vel_error
            
            # Clip DV to maintain physical realism (max 0.3 m/s per tick)
            dv_mag = np.linalg.norm(accel)
            if dv_mag > 0.3:
                accel = (accel / dv_mag) * 0.3
                
            actions[sat_name] = accel

        return actions
