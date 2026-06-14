import numpy as np
from typing import List, Dict, Any
from fsn.constants import MEAN_MOTION_N, NOMINAL_ATTITUDE_NOISE_DEG

class OrbitalModel:
    """
    Implements the Clohessy-Wiltshire (CW) equations for Hill's frame propagation.
    The Hill frame (RSW) coordinates:
    x: Radial (outward)
    y: Along-track (velocity direction)
    z: Cross-track (normal to orbital plane)
    """

    def __init__(self, n: float = MEAN_MOTION_N):
        self.n = n

    def get_phi_matrix(self, dt: float) -> np.ndarray:
        """
        Calculates the state transition matrix (Phi) for time step dt.
        State vector: [x, y, z, vx, vy, vz]
        """
        n = self.n
        nt = n * dt
        cos_nt = np.cos(nt)
        sin_nt = np.sin(nt)

        # 6x6 State Transition Matrix
        phi = np.zeros((6, 6))

        # Position from Position
        phi[0, 0] = 4 - 3 * cos_nt
        phi[0, 1] = 0
        phi[0, 2] = 0
        phi[1, 0] = 6 * (sin_nt - nt)
        phi[1, 1] = 1
        phi[1, 2] = 0
        phi[2, 0] = 0
        phi[2, 1] = 0
        phi[2, 2] = cos_nt

        # Position from Velocity
        phi[0, 3] = (1 / n) * sin_nt
        phi[0, 4] = (2 / n) * (1 - cos_nt)
        phi[0, 5] = 0
        phi[1, 3] = (2 / n) * (cos_nt - 1)
        phi[1, 4] = (1 / n) * (4 * sin_nt - 3 * nt)
        phi[1, 5] = 0
        phi[2, 3] = 0
        phi[2, 4] = 0
        phi[2, 5] = (1 / n) * sin_nt

        # Velocity from Position
        phi[3, 0] = 3 * n * sin_nt
        phi[3, 1] = 0
        phi[3, 2] = 0
        phi[4, 0] = 6 * n * (cos_nt - 1)
        phi[4, 1] = 0
        phi[4, 2] = 0
        phi[5, 0] = 0
        phi[5, 1] = 0
        phi[5, 2] = -n * sin_nt

        # Velocity from Velocity
        phi[3, 3] = cos_nt
        phi[3, 4] = 2 * sin_nt
        phi[3, 5] = 0
        phi[4, 3] = -2 * sin_nt
        phi[4, 4] = 4 * cos_nt - 3
        phi[4, 5] = 0
        phi[5, 3] = 0
        phi[5, 4] = 0
        phi[5, 5] = cos_nt

        return phi

    def propagate(self, state: np.ndarray, dt: float, dv: np.ndarray = None) -> np.ndarray:
        """
        Propagates the state [x, y, z, vx, vy, vz] for dt seconds.
        Optionally applies a Delta-V maneuver [dvx, dvy, dvz] at the START of the step.
        """
        if dv is not None:
            state[3:] += dv

        phi = self.get_phi_matrix(dt)
        return phi @ state

class Satellite:
    def __init__(self, name: str, initial_state: np.ndarray, role: str):
        self.name = name
        self.state = initial_state.copy()  # [x, y, z, vx, vy, vz]
        self.role = role
        self.fuel_remaining = 50.0  # m/s
        self.attitude_error = 0.003
        self.raw_attitude_error = NOMINAL_ATTITUDE_NOISE_DEG
        self.attitude_knowledge_error = NOMINAL_ATTITUDE_NOISE_DEG
        self.sensor_source = "PHYSICAL"
        self.fault_active = False

    def step(self, model: OrbitalModel, dt: float, dv: np.ndarray = None):
        if dv is not None:
            dv_mag = np.linalg.norm(dv)
            if self.fuel_remaining >= dv_mag:
                self.fuel_remaining -= dv_mag
            else:
                # Scaled DV if low on fuel (simplified)
                dv = dv * (self.fuel_remaining / dv_mag)
                self.fuel_remaining = 0

        self.state = model.propagate(self.state, dt, dv)
