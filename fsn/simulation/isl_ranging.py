import numpy as np
from typing import Dict, Tuple
from fsn.constants import ISL_NOISE_SIGMA_M, BEARING_NOISE_SIGMA_DEG

def get_isl_measurements(sat_states: Dict[str, np.ndarray]) -> Dict[Tuple[str, str], Dict[str, float]]:
    """
    Computes ISL measurements between all satellite pairs.
    sat_states: Dict mapping satellite name to its 6-element state vector [x, y, z, vx, vy, vz]
    Returns a dict of measurements for each pair.
    """
    names = list(sat_states.keys())
    measurements = {}

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a, name_b = names[i], names[j]
            pos_a = sat_states[name_a][:3]
            pos_b = sat_states[name_b][:3]

            # Relative position in Hill frame (A to B)
            rel_pos = pos_b - pos_a
            dist_true = np.linalg.norm(rel_pos)

            # Add range noise
            dist_meas = dist_true + np.random.normal(0, ISL_NOISE_SIGMA_M)

            # Bearing angles (Azimuth and Elevation)
            # Azimuth in y-z plane (along-track / cross-track)
            az_true = np.degrees(np.arctan2(rel_pos[2], rel_pos[1]))
            # Elevation relative to radial direction x
            el_true = np.degrees(np.arctan2(rel_pos[0], np.sqrt(rel_pos[1]**2 + rel_pos[2]**2)))

            # Add bearing noise
            az_meas = az_true + np.random.normal(0, BEARING_NOISE_SIGMA_DEG)
            el_meas = el_true + np.random.normal(0, BEARING_NOISE_SIGMA_DEG)

            measurements[(name_a, name_b)] = {
                "range_m": dist_meas,
                "az_deg": az_meas,
                "el_deg": el_meas,
                "is_psp_link": 0 # To be set by simulation logic
            }

    return measurements
