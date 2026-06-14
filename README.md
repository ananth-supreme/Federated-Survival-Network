# Federated Survival Network (FSN)

A Python-based satellite swarm recovery simulator with a Next.js mission control dashboard.

## Project Description

A Python-based simulation and mission control dashboard that demonstrates how a cluster of satellites can collectively rescue a "blind" satellite that has lost its attitude sensor — extending the satellite's operational life through shared data rather than physical repair.

When a satellite loses its star tracker (attitude sensor), it becomes disoriented and unable to maintain its orbital formation. FSN activates the **Phantom Sensor Protocol (PSP)**: healthy nearby satellites use laser Inter-Satellite Links (ISL) to measure the exact distance and bearing to the blind satellite, solve for its orientation using Wahba's problem, and feed the result back as a mathematically-computed virtual sensor. The blind satellite is rescued by data, not hardware.

The simulation runs in Python with a modular architecture separating the simulation core, state services, and presentation layers. The mission control dashboard is built with a modern web frontend backed by a FastAPI service layer. Data is persisted in SQLite (local demo) or PostgreSQL (production). Everything runs locally with a single startup command.


### 1. Features

#### 1.1. Orbital Simulation Engine

**Description:** FSN operates using a standalone Python orbital simulation core. Orbital propagation of the three-satellite Hill's frame formation uses the Clohessy-Wiltshire (CW) equations implemented in `orbital_model.py`. The simulation writes satellite states to the database each tick for the dashboard and RL agent to consume.

**Behaviour:**
- Initializes three satellites in a stable equilateral triangle formation: Sat-A (chief, [0, 0, 0]), Sat-B ([0, +250, +433]m), Sat-C ([0, -250, +433]m) in the Hill frame.
- `runner.py` polls satellite state at 1 Hz and writes position, velocity, and attitude data to the `telemetry` table.
- The natural motion condition `ẏ₀ = -2n·x₀` ensures bounded orbits without continuous thrust.
- Simulation time advances in 1-second steps. Dashboard reads state every 2 seconds.

**Orbit parameters:**
- Altitude: 500 km (sun-synchronous, 97.4° inclination)
- Mean motion n: ≈ 1.107 × 10⁻³ rad/s
- Orbital period T: ≈ 94.6 minutes
- Inter-satellite spacing: 500m (equilateral triangle side length)

#### 1.2. Fault Injection

**Description:** At a user-specified simulation time (default: T = T_orbit / 2), inject a star tracker failure on Sat-A by replacing its nominal attitude noise with high-variance noise.

**Behaviour:**
- Before fault: attitude knowledge error σ = 0.003° (10 arcsec, star tracker spec)
- After fault: attitude knowledge error σ = 2.0° (Gaussian noise injected)
- `fault_active` flag set to True for Sat-A in the simulation state
- `sensor_source` switches from `PHYSICAL` to `FAILED`
- CUSUM change-point detector monitors the attitude error time series and logs a `FAULT_DETECTED` event to the database within 15 seconds

**Triggering:** Operator presses the "🚨 Inject Fault" button in the command area. The fault persists until PSP successfully reduces attitude error below 0.2°, at which point `sensor_source` switches to `PHANTOM`.

#### 1.3. ISL Laser Ranging Model

**Description:** Simulates two-way laser ranging between all satellite pairs. For each pair (A↔B, A↔C, B↔C), computes the measured distance and bearing angles in the Hill frame at each simulation tick.

**Behaviour:**
- True inter-satellite distance: Euclidean norm of position difference vector
- Measurement noise: Gaussian, σ = 0.5m (within commercial ISL specification)
- Bearing angles: azimuth `θ = atan2(Δz, Δy)`, elevation `φ = atan2(Δx, d_true)`
- When Sat-A fault is active, A↔B and A↔C measurements are highlighted as PSP-contributing links
- All measurements written to `isl_measurements` table every simulation tick

#### 1.4. Phantom Sensor Protocol (PSP)

**Description:** Core algorithmic feature. When `fault_active` is True for Sat-A, PSP uses ISL bearing vectors from B→A and C→A — combined with the known positions of Sat-B and Sat-C in the Hill frame — to solve for Sat-A's attitude via a simplified implementation of Wahba's problem (QUEST method via `scipy.linalg`).

**Behaviour:**
- Reference vectors `r_i`: unit vectors from Sat-A to each healthy satellite, computed from known positions in the Hill frame
- Body-frame vectors `b_i`: derived from ISL bearing angles measured by Sat-A's laser terminal
- Attitude solution: rotation matrix R minimising `L(R) = (1/2) Σᵢ wᵢ ||b_i - R·r_i||²`
- Weights `wᵢ = 1/σ_range²` based on ISL measurement quality
- Output: virtual quaternion fed back to Sat-A's attitude controller as if from hardware
- Expected accuracy: virtual attitude error ≤ 0.15° (vs. 2.0° of failed star tracker)
- `sensor_source` for Sat-A switches from `FAILED` to `PHANTOM` on successful PSP activation
- `PSP_ACTIVATED` event written to the events table

#### 1.5. Formation Reconfiguration Controller

**Description:** A PPO (Proximal Policy Optimisation) reinforcement learning agent (`reconfig_controller.py`) that, upon fault detection, issues ΔV commands to Sat-B and Sat-C to close the imaging coverage gap left by the faulted Sat-A.

**Behaviour:**
- Observes formation state: position errors, velocities, and sensor status of all three satellites
- At each decision step, the PPO policy outputs continuous ΔV actions for Sat-B and Sat-C
- Sat-A enters reduced-power safe mode (attitude held by PSP, no maneuvers commanded on Sat-A)
- ΔV budget consumed per maneuver: approximately 0.2 m/s per satellite (0.4% of 50 m/s total budget)
- Agent runs continuously until formation error < 50m, then logs `RECOVERY_COMPLETE`

**PPO Architecture:**
- **State space:** 12-dimensional vector — position error (y, z) and velocity (vy, vz) for Sat-B and Sat-C, plus scalar attitude error and PSP active flag for Sat-A
- **Action space:** 4-dimensional continuous — ΔVy and ΔVz for each of Sat-B and Sat-C, clipped to ±0.5 m/s
- **Policy network:** 2-layer MLP (64 → 64 → action dim), shared actor-critic backbone
- **Reward function:** `−formation_error_m / 500 − 0.01 * |ΔV|` (minimise error, penalise fuel use)
- **Training:** Pre-trained offline in simulation; frozen weights loaded at demo runtime

**Success criterion:** Formation error < 200m achieved within 240 simulated seconds (4 minutes) of fault detection.

## I. Quick Start

#### 1.1 Environment Setup

Requires Python 3.11+.

```bash
pip install numpy scipy fastapi uvicorn pydantic sqlalchemy plotly pandas ruptures stable-baselines3
```

For local development, no external accounts, API keys, or Docker are required. Everything runs on a pc.

#### 1.2 Running the Project

# Terminal 1 — run the simulation 
```bash
cd Federated-Survival-Network-main
python -m fsn.runner
```

# Terminal 2 — run the api 
```bash
cd Federated-Survival-Network-main
python -m fsn.api.api
```

# Terminal 3 — launch the frontend
```bash
cd fsn
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the dashboard.


The simulation loop writes to the database every 1 second. The frontend reads state via WebSocket/SSE and refreshes in real time.

---


## Simulation Details
- **Engine:** Clohessy-Wiltshire (CW) equations for relative motion.
- **Protocol:** Phantom Sensor Protocol (PSP) using Wahba's problem solver (SVD method).
- **Recovery:** Heuristic-based formation reconfiguration.
- **Fault Detection:** CUSUM detection of attitude sensor noise.
---

### II. Non-Functional Requirements

**Reliability:** The demo path should run repeatedly without manual cleanup. A "Reset Simulation" control clears the database and restarts the simulation runner — ensuring the demo is repeatable on demand.

**Performance:**
- Simulation loop: ≤ 50ms per 1-second tick
- Dashboard refresh: smooth even as telemetry grows
- PSP solve time: ≤ 10ms per call (Wahba's problem via `numpy.linalg.eig` on a 3×3 matrix)
- Fault detection latency: ≤ 15 simulated seconds from noise injection to `FAULT_DETECTED` event

**Accuracy:**
- CW propagation error after one orbit: < 1m positional drift
- PSP virtual attitude accuracy: < 0.15° RMS across 50 test cases with random fault injection timing
- Formation recovery success rate: > 80% of injected fault scenarios achieve formation error < 200m within 4 minutes

**Traceability:** Every major state transition must produce a readable event entry.

**Accessibility:** Contrast must remain high enough for a live room or projected screen.

**Maintainability:** Modules should be testable in isolation, especially the PSP solver and controller.

A launch-ready version should also include browser-based smoke tests, type checks, and a lightweight replay mode so the exact fault-and-recovery sequence can be demonstrated consistently.

---
### III. Data Model

#### `satellites` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | 1, 2, 3 for Sat-A, Sat-B, Sat-C |
| `name` | TEXT | "SAT_A", "SAT_B", "SAT_C" |
| `role` | TEXT | "CHIEF", "DEPUTY", or "BLIND" |
| `mass_kg` | REAL | 50.0 (CubeSat class) |
| `fuel_budget_ms` | REAL | 50.0 m/s total ΔV |
| `fuel_remaining_ms` | REAL | Decrements with each maneuver |

#### `telemetry` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `sim_time_s` | REAL | Elapsed simulation seconds |
| `satellite_id` | INTEGER FK | References `satellites.id` |
| `pos_y` | REAL | Along-track position in Hill frame (m) |
| `pos_z` | REAL | Cross-track position in Hill frame (m) |
| `vel_y` | REAL | Along-track velocity (m/s) |
| `vel_z` | REAL | Cross-track velocity (m/s) |
| `attitude_error_deg` | REAL | Current attitude knowledge error (°) |
| `sensor_source` | TEXT | "PHYSICAL", "PHANTOM", or "FAILED" |
| `fault_active` | INTEGER | 0 = nominal, 1 = faulted |
| `battery_soc` | REAL | State of charge 0.0–1.0 |
| `psp_attitude_error_deg` | REAL | Virtual sensor error when PSP active; NULL otherwise |

#### `isl_measurements` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `sim_time_s` | REAL | When measurement was taken |
| `from_sat_id` | INTEGER FK | Transmitting satellite |
| `to_sat_id` | INTEGER FK | Receiving satellite |
| `range_m` | REAL | Measured inter-satellite distance (m) |
| `range_noise_m` | REAL | Noise applied (Gaussian σ = 0.5m) |
| `bearing_az_deg` | REAL | Azimuth angle in Hill frame (°) |
| `bearing_el_deg` | REAL | Elevation angle in Hill frame (°) |
| `is_psp_link` | INTEGER | 1 if this link is actively contributing to PSP |

#### `events` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `sim_time_s` | REAL | When event occurred |
| `event_type` | TEXT | One of: `FAULT_DETECTED`, `PSP_ACTIVATED`, `RECONFIG_STARTED`, `RECOVERY_COMPLETE`, `SAFE_MODE_ENTERED` |
| `satellite_id` | INTEGER FK | Affected satellite |
| `description` | TEXT | Human-readable narrative for event log |
| `formation_error_m` | REAL | Formation error at moment of event |
| `attitude_error_deg` | REAL | Attitude error at moment of event |

#### `command_queue` table

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `issued_at` | REAL | Sim time the command was issued |
| `command_type` | TEXT | e.g., `INJECT_FAULT`, `RESET`, `PAUSE`, `REPLAY` |
| `status` | TEXT | `PENDING`, `EXECUTED`, `REJECTED` |
| `payload` | TEXT | JSON blob of command parameters |

---

## IV. Project Structure

```
fsn/
│
├── simulation/
│   ├── __init__.py
│   ├── orbital_model.py          # CW equations — orbit propagation for all three satellites
│   ├── isl_ranging.py            # Laser ranging model: distance, bearing, noise
│   │                             # Returns measurement dict for all 3 satellite pairs
│   ├── psp_solver.py             # Phantom Sensor Protocol (PSP)
│   │                             # Wahba's problem via scipy.linalg — returns virtual quaternion
│   ├── fault_manager.py          # Star tracker noise injection at T_fault
│   │                             # CUSUM fault detection via ruptures
│   └── reconfig_controller.py    # PPO Formation Reconfiguration Agent
│                                 # Pre-trained policy; issues ΔV for Sat-B/C at each step
│
├── state/
│   ├── __init__.py
│   ├── db.py                     # SQLite/PostgreSQL init, create tables, insert helpers, read queries
│   ├── repository.py             # Read models and snapshot queries for the UI
│   ├── command_bus.py            # Command queue: validate, enqueue, and dispatch user actions
│   └── schemas.py                # Pydantic models for telemetry, events, commands
│
├── api/
│   ├── __init__.py
│   └── api.py                    # FastAPI app — REST + WebSocket/SSE endpoints
│                                 # Exposes: /state, /events, /commands, /ws
│
├── app/
│   ├── components/               # Reusable UI components (health cards, charts, ISL graph)
│   ├── views/                    # Page-level views (mission console, event log, replay)
│   └── styles/                   # Tailwind config and shared design tokens
│
├── runner.py                     # Main simulation loop
│                                 # Calls orbital_model → fault check → ISL → PSP → RL agent
│                                 # → writes to DB, every 1 sim-second
│
├── constants.py                  # All magic numbers in one place:
│                                 # ORBIT_ALTITUDE_KM, MEAN_MOTION_N, FORMATION_SIZE_M,
│                                 # FAULT_THRESHOLD_DEG, ISL_NOISE_SIGMA_M,
│                                 # FORMATION_ERROR_SUCCESS_M, FAULT_INJECTION_TIME_S
│
├── requirements.txt              # Python dependencies
├── package.json                  # Frontend dependencies (Next.js / React)
│
├── README.md                     # What it is, how to run it, physics references,
│                                 # architecture diagram
│
└── .gitignore                    # database/*.db, __pycache__/, node_modules/, .env
```

---

## V. File Descriptions

**`simulation/orbital_model.py`**
Implements the Clohessy-Wiltshire equations for Hill's frame propagation of the three-satellite formation. Advances satellite state at each 1-second tick. Returns position and velocity for all three satellites. Enforces the natural motion condition `ẏ₀ = -2n·x₀` for bounded orbits.

**`simulation/isl_ranging.py`**
Given two satellite position vectors in the Hill frame, computes: true Euclidean distance, Gaussian measurement noise (σ = 0.5m), azimuth bearing angle, and elevation bearing angle. Called for all three satellite pairs (A↔B, A↔C, B↔C) at every simulation tick. Returns a measurement dict written to `isl_measurements` table.

**`simulation/psp_solver.py`**
The core PSP algorithm. Called when `fault_active=True` for Sat-A. Takes ISL bearing vectors from Sat-B and Sat-C to Sat-A (body-frame) and the known Hill-frame reference vectors. Constructs the Wahba cost matrix and solves for the optimal rotation using `scipy.linalg.eig`. Returns a virtual attitude quaternion and estimated accuracy. This is the mathematical heart of the project.

**`simulation/fault_manager.py`**
Two responsibilities: (1) at `T_fault`, switch Sat-A's attitude noise from σ = 0.003° to σ = 2.0°; (2) monitor the attitude error time series using CUSUM (`ruptures`) and flag `fault_active=True` within 15 seconds of the noise jump. Writes a `FAULT_DETECTED` event to the database.

**`simulation/reconfig_controller.py`**
The PPO Formation Reconfiguration Agent. Loads pre-trained `stable-baselines3` PPO weights at startup. At each simulation tick when `fault_active=True`, constructs the 12-dimensional observation vector from current satellite states, runs a forward pass through the frozen policy network, and returns continuous ΔV actions for Sat-B and Sat-C. Actions are clipped to ±0.5 m/s. Logs `RECOVERY_COMPLETE` when formation error drops below 50m.

**`state/db.py`**
Complete database layer. Functions: `init_db()` (create tables), `insert_telemetry(state_dict)`, `insert_isl_measurement(meas_dict)`, `insert_event(event_dict)`, `enqueue_command(cmd_dict)`, `get_telemetry(last_n)`, `get_events()`.

**`state/repository.py`**
Read models for the UI. Provides stable state snapshots that the frontend consumes without touching live simulation objects directly.

**`state/command_bus.py`**
Validates and dispatches user commands (inject fault, reset, pause, replay) from the command queue. Prevents race conditions during demo-time interactions.

**`state/schemas.py`**
Pydantic models defining the data contracts for telemetry, events, ISL measurements, and commands. Ensures type safety across the simulation-to-UI boundary.

**`api/api.py`**
FastAPI application. Exposes REST endpoints (`/state`, `/events`, `/commands`) and a WebSocket/SSE endpoint for real-time state streaming to the frontend.

**`runner.py`**
The main loop. Initialises the database and opens the simulation. Loops indefinitely: advance `orbital_model` → check `fault_manager` → compute ISL ranges → if fault: run `psp_solver` + `reconfig_controller` → insert all data to DB → sleep 1s. Designed to run in a terminal window alongside the API server.

**`constants.py`**
Single source of truth for all simulation parameters. Ensures consistent values across all files without magic numbers scattered through the codebase.

---
