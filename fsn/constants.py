import numpy as np

# Orbital Parameters
ORBIT_ALTITUDE_KM = 500.0
EARTH_RADIUS_KM = 6378.1
MU = 3.986004418e14  # Earth's gravitational parameter (m^3/s^2)

# Mean Motion n = sqrt(mu / a^3)
A = (EARTH_RADIUS_KM + ORBIT_ALTITUDE_KM) * 1000.0
MEAN_MOTION_N = np.sqrt(MU / A**3)

# Formation Parameters
# Sat-A (Chief) is at [0,0,0]
# Sat-B and Sat-C form an equilateral triangle in the y-z plane
# Spacing is 500m
FORMATION_SIZE_M = 500.0
SAT_B_START_POS = [0.0, FORMATION_SIZE_M / 2.0, np.sqrt(3) / 2.0 * FORMATION_SIZE_M]
SAT_C_START_POS = [0.0, -FORMATION_SIZE_M / 2.0, np.sqrt(3) / 2.0 * FORMATION_SIZE_M]

# Simulation Timing
SIM_TICK_S = 1.0  # 1 second per tick
ORBITAL_PERIOD_S = 2 * np.pi / MEAN_MOTION_N

# Fault Parameters
FAULT_INJECTION_TIME_S = ORBITAL_PERIOD_S / 2.0
NOMINAL_ATTITUDE_NOISE_DEG = 0.003
FAULT_ATTITUDE_NOISE_DEG = 2.0
FAULT_THRESHOLD_DEG = 0.5  # Threshold for CUSUM/detection

# ISL Parameters
ISL_NOISE_SIGMA_M = 0.5
BEARING_NOISE_SIGMA_DEG = 0.1

# Recovery Success Thresholds
FORMATION_ERROR_SUCCESS_M = 200.0
PSP_TARGET_ACCURACY_DEG = 0.15
PSP_RECOVERY_DELAY_S = 15.0       # seconds after fault before PSP stabilizes knowledge
PSP_CONVERGE_DURATION_S = 5.0     # ramp-down window (stable by ~20s)
ATTITUDE_CRITICAL_THRESHOLD_DEG = 0.5
FORMATION_RECOVERY_DURATION_S = 50.0  # sim-seconds (~5s wall clock at 10× tick rate)

# Displacement applied on fault (Hill frame, metres) — visible but recoverable
FAULT_FORMATION_OFFSETS = {
    "SAT_A": [0.0, 140.0, -200.0],
    "SAT_B": [0.0, -70.0, 100.0],
    "SAT_C": [0.0, 85.0, 110.0],
}

# Satellite Specs
INITIAL_FUEL_MS = 50.0
MASS_KG = 50.0
