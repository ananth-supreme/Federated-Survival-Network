# Federated Survival Network (FSN)
## Product Design Document v3 — Refined

*Redesigned for stronger UI/UX, cleaner app structure, and a launch-ready technical foundation*

> **Document intent:** This version keeps the original physics, fault recovery, and mission value intact, but redesigns the product so it feels polished, reliable, and easy to understand in a live demo or public release. FSN is still a Python-first satellite swarm recovery simulator. The redesign focuses on three things: a cleaner screen hierarchy, fewer UI surprises, and a modular architecture that separates simulation logic from presentation.

---

## Project Description

A Python-based simulation and mission control dashboard that demonstrates how a cluster of satellites can collectively rescue a "blind" satellite that has lost its attitude sensor — extending the satellite's operational life through shared data rather than physical repair.

When a satellite loses its star tracker (attitude sensor), it becomes disoriented and unable to maintain its orbital formation. FSN activates the **Phantom Sensor Protocol (PSP)**: healthy nearby satellites use laser Inter-Satellite Links (ISL) to measure the exact distance and bearing to the blind satellite, solve for its orientation using Wahba's problem, and feed the result back as a mathematically-computed virtual sensor. The blind satellite is rescued by data, not hardware.

The simulation runs in Python with a modular architecture separating the simulation core, state services, and presentation layers. The mission control dashboard is built with a modern web frontend backed by a FastAPI service layer. Data is persisted in SQLite (local demo) or PostgreSQL (production). Everything runs locally with a single startup command.

---

## Product Requirements Document

### 1. Introduction

The Federated Survival Network (FSN) is a physics simulation and real-time mission control dashboard that models autonomous satellite swarm recovery. It demonstrates the Phantom Sensor Protocol — a technique in which healthy satellites within a formation use laser Inter-Satellite Link (ISL) ranging to mathematically reconstruct the attitude of a satellite that has lost its physical sensor. The formation then autonomously reconfigures to maintain imaging coherence while the blind satellite is guided by virtual sensor data.

Its primary goal is to demonstrate a novel, physically grounded approach to satellite fault tolerance — one that is commercially relevant (mission life extension), technically defensible (real orbital mechanics, real attitude mathematics), and visually compelling in a live demo context.

The redesign does not change the core science. It changes how the product is presented, how the app is structured, and how the user experiences state transitions.

---

### 2. Goals and Launch Criteria

- Simulate three satellites in a stable LEO formation using Clohessy-Wiltshire orbital dynamics.
- Demonstrate fault injection: a star tracker failure on Sat-A causing its attitude knowledge error to spike from 0.003° to 2.0°.
- Implement the Phantom Sensor Protocol: use ISL laser ranging from Sat-B and Sat-C to solve Wahba's problem and produce a virtual attitude quaternion for Sat-A accurate to ≤0.15°.
- Implement a PPO-based Formation Reconfiguration Controller (`reconfig_controller.py`) that issues ΔV commands to healthy satellites to close the coverage gap caused by the fault.
- Present all of this through a polished mission control dashboard that a non-technical audience can follow during a 3-minute demo.
- Make the interface readable in seconds, not minutes. Judges should understand the state of the system from one glance.
- Remove layout jitter, redundant controls, and mixed visual priorities that make a dashboard feel unstable.
- Maintain a modular architecture so simulation, persistence, and UI can evolve independently.
- Keep the stack realistic for a student-built launch: low operational overhead, no paid services required, and minimal coupling.

**Launch criteria:** The app should run repeatably, handle fault injection without UI breakage, present a stable live view, and provide a narrative event trail that explains what changed and why.

---

### 3. Target Audience & Value Proposition

**Target Audience:** Hackathon judges from aerospace, engineering, and entrepreneurship backgrounds. Secondary audience: aerospace engineers, satellite operators evaluating mission life extension technology, and aerospace students or engineers who care about the validity of the physics and control logic.

**Value Proposition:** Dead satellites cost $300M+ per mission and generate dangerous orbital debris. Current fault recovery requires ground contact (10+ minute latency minimum), during which the formation breaks irreversibly. FSN demonstrates that a software-only, onboard Phantom Sensor approach — requiring no new hardware, no service mission, no ground command — can rescue a blind satellite in under 4 minutes using only the data already flowing between satellites in a healthy formation.

---

### 4. Users and Jobs To Be Done

**Judges** need a story arc: nominal operation, fault, PSP activation, recovery.

**Technical reviewers** need visible evidence that the solution is physically grounded and not just cosmetic.

**Demo operators** need a simple control surface with a small number of safe, obvious actions.

**Future contributors** need code that is easy to navigate and test without destabilizing the simulation.

---

### 5. User Stories

**Simulation Control**

- As a demo operator, I want to launch the simulation and see three satellites orbiting in a stable formation, all health indicators green.
- As a demo operator, I want to press a single "Inject Fault" button and immediately see Sat-A's health turn red on the dashboard.
- As a demo operator, I want to watch the Phantom Sensor Protocol activate automatically — without pressing any further buttons — and see Sat-A's sensor status switch from FAILED to PHANTOM SENSOR.
- As a demo operator, I want to watch the formation error chart peak and then recover below the 200m success threshold as the reconfiguration controller acts.

**Dashboard**

- As a viewer, I want to see the health of all three satellites at a glance — attitude error, battery state of charge, fuel remaining, and sensor source.
- As a viewer, I want to see a live chart showing formation error over time, with a reference line at 200m showing the success threshold.
- As a viewer, I want to see an ISL network diagram showing which laser links are active and which are providing Phantom Sensor data.
- As a viewer, I want to see a timestamped event log that narrates the fault and recovery sequence in plain English.

---

### 6. Redesign Principles

| Principle | Design Impact |
|---|---|
| Hierarchy first | The screen must clearly separate system status, live telemetry, and supporting detail. |
| Stable layout | Panels should stay in place across refresh cycles; only data should change, not the structure. |
| One signal per color | Green = healthy, red = fault, amber = PSP. No color reuse for decorative purposes. |
| Readable at a distance | Large numbers, short labels, and clean cards are more important than dense technical clutter. |
| Logic stays behind the curtain | The UI consumes state; it does not perform physics or controller logic itself. |

---

### 7. Features

#### 7.1. Orbital Simulation Engine

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

#### 7.2. Fault Injection

**Description:** At a user-specified simulation time (default: T = T_orbit / 2), inject a star tracker failure on Sat-A by replacing its nominal attitude noise with high-variance noise.

**Behaviour:**
- Before fault: attitude knowledge error σ = 0.003° (10 arcsec, star tracker spec)
- After fault: attitude knowledge error σ = 2.0° (Gaussian noise injected)
- `fault_active` flag set to True for Sat-A in the simulation state
- `sensor_source` switches from `PHYSICAL` to `FAILED`
- CUSUM change-point detector monitors the attitude error time series and logs a `FAULT_DETECTED` event to the database within 15 seconds

**Triggering:** Operator presses the "🚨 Inject Fault" button in the command area. The fault persists until PSP successfully reduces attitude error below 0.2°, at which point `sensor_source` switches to `PHANTOM`.

#### 7.3. ISL Laser Ranging Model

**Description:** Simulates two-way laser ranging between all satellite pairs. For each pair (A↔B, A↔C, B↔C), computes the measured distance and bearing angles in the Hill frame at each simulation tick.

**Behaviour:**
- True inter-satellite distance: Euclidean norm of position difference vector
- Measurement noise: Gaussian, σ = 0.5m (within commercial ISL specification)
- Bearing angles: azimuth `θ = atan2(Δz, Δy)`, elevation `φ = atan2(Δx, d_true)`
- When Sat-A fault is active, A↔B and A↔C measurements are highlighted as PSP-contributing links
- All measurements written to `isl_measurements` table every simulation tick

#### 7.4. Phantom Sensor Protocol (PSP)

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

#### 7.5. Formation Reconfiguration Controller

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

#### 7.6. Mission Control Dashboard

**Description:** A polished mission control interface backed by a FastAPI service layer and rendered in a modern web frontend. Auto-refreshes via WebSocket or SSE. Designed for a dark aerospace aesthetic — data-dense, uncluttered, and immediately readable during a live demo.

**Recommended Screen Structure:**

| Region | Contents | Reasoning |
|---|---|---|
| Top bar | System name, simulation clock, mode badge, overall health indicator | Always visible context and immediate confidence |
| Primary center | Orbit view + fault/recovery timeline | This is the main narrative the viewer should watch |
| Right rail | Satellite health cards, link status, alert summary | Fast scanability without crowding the main plot |
| Bottom band | Event log and command history | Explains what just happened in plain language |

**UI Rules:**
- Use fixed-height cards so the page does not jump when values update.
- Use loading placeholders or last-known values instead of empty panels on refresh.
- Group controls into a single command area. No scattered buttons.
- Show state transitions as badges and timeline events, not only as raw telemetry.
- Keep plots visually restrained: one primary chart, one orbit view, one supporting network view.

**Interaction Model:**
- Nominal state: all satellites display healthy status, orbit view is calm, and the event log is quiet.
- Fault injection: Sat-A turns red immediately, the attitude error spikes, and the event log records the failure.
- PSP activation: the sensor badge flips to amber, the link visualization highlights contributing paths, and the timeline marks the transition.
- Recovery: formation error improves, the system returns to a stable state, and the dashboard confirms success without changing layout.

---

### 8. Data Model

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

### 9. Data and State Design

The app is event-driven, not screen-driven. The simulation emits telemetry and events; the frontend renders a read-only view of that state. User actions such as fault injection or reset requests become commands, not direct mutations.

| State Object | Purpose |
|---|---|
| Telemetry snapshot | Current satellite positions, attitude error, battery, fuel, and sensor source |
| Event stream | Chronological recovery narrative with timestamps and typed milestones |
| Command queue | User actions such as inject fault, reset, pause, or replay |
| Derived views | Formation error, recovery stage, link health, and mission status badges |

**Design constraint:** Do not let the UI compute mission-critical logic. The UI should only visualize state, send commands, and display results. That rule is the easiest way to keep the app stable and protect the mission logic from frontend bugs.

---

### 10. User Experience & Design

**Overall vision:** The dashboard should feel like a real mission operations console — calm, legible, and operationally credible. Dark theme with a space aesthetic. All critical state changes (fault, PSP activation, recovery) must be visually dramatic without being confusing. A judge who has never seen the system before should be able to follow the fault-and-recovery story arc just by watching the screen.

**Key visual moments (in order during demo):**
1. All green metrics → calm, nominal formation
2. Red flash on Sat-A card + attitude error spike → fault visible instantly
3. Amber "PHANTOM SENSOR" badge appears on Sat-A → PSP activated, dramatic colour shift
4. Formation error chart peaks then drops below threshold line → recovery confirmed

---

### 11. Styling Guidelines

#### 11.1. Design Vision

FSN is a mission control application, not a consumer product. The aesthetic must communicate engineering credibility and technical seriousness while remaining immediately readable by a non-technical audience during a live demo. The design language is inspired by real aerospace ground station interfaces — dark background, high-contrast data, colour-coded health states.

The dominant emotion the dashboard should evoke is **controlled urgency**: calm during nominal operations, sharp and unambiguous when a fault fires, and visibly satisfying when recovery completes. Every colour change must mean something.

#### 11.2. Colour Palette

| Role | Colour | Hex | Usage |
|---|---|---|---|
| Background | Deep space | `#0A0E1A` | Page background |
| Secondary background | Dark panel | `#111827` | Cards, sidebar |
| Border / divider | Dark slate | `#1E2D50` | Card borders, chart gridlines |
| Primary text | Off-white | `#E8EDF8` | All body text, metric values |
| Secondary text | Muted slate | `#8A99BB` | Labels, captions, axis ticks |
| Nominal / healthy | Signal green | `#10B981` | Satellite health green, recovery line |
| Fault / failed | Alert red | `#EF4444` | Fault badge, diverging line, risk spike |
| Phantom Sensor | Amber gold | `#F59E0B` | PSP badge, ISL active links, PSP chart marker |
| Neutral / inactive | Cool grey | `#6B7280` | Inactive links, background metrics |
| Accent / interactive | Cyan | `#3B82F6` | Buttons, selected states, primary accent |

**Colour rules:**
- Green and red are reserved exclusively for health state. Do not use green for anything that is not "healthy/nominal" or red for anything that is not "fault/failed."
- Amber/gold is reserved exclusively for PSP state. This is the visual signature that makes PSP instantly recognisable across all panels simultaneously.
- When PSP activates, amber appears in exactly three places simultaneously: (1) Sat-A's sensor badge, (2) the A↔B and A↔C edges in the ISL graph, and (3) the PSP_ACTIVATED event marker on the formation chart.
- Every panel must update colour when state changes — the health cards, the ISL graph, the event log badge — all shift colour in the same refresh cycle.

#### 11.3. Typography

- **Metric values** (attitude error, etc.): large, bold display with delta colouring (green for improvement, red for deterioration). Use delta arrows on all satellite health metrics.
- **Section headers**: used sparingly — one per panel maximum.
- **Event log descriptions**: standard font, legible at small sizes.
- **Chart axis labels and titles**: use `#8A99BB` for axis text, `#E8EDF8` for chart titles, `#0A0E1A` for chart backgrounds.

#### 11.4. Chart Design

**Global chart defaults:**
```python
layout = dict(
    paper_bgcolor='#111827',
    plot_bgcolor='#0A0E1A',
    font=dict(color='#8A99BB', family='monospace'),
    xaxis=dict(gridcolor='#1E2D50', linecolor='#1E2D50'),
    yaxis=dict(gridcolor='#1E2D50', linecolor='#1E2D50'),
    margin=dict(l=40, r=20, t=40, b=40)
)
```

**Formation error chart:**
- "Without PSP" line: `#EF4444` (red), dashed, pre-recorded data
- "With PSP" line: `#10B981` (green), solid, live simulation data
- 200m threshold: horizontal dashed line `#F59E0B` (amber), labelled "Success threshold"
- FAULT_DETECTED marker: vertical dashed line `#EF4444`
- PSP_ACTIVATED marker: vertical dashed line `#F59E0B`

**ISL network graph:**
- Nodes: circles, `#3B82F6` fill, white label (satellite name)
- Nominal edges: `#1E2D50` (barely visible, inactive)
- PSP-active edges: `#F59E0B` (gold), thickness 3px, edge label = measured range in metres
- Non-PSP active edges: `#6B7280` (grey), thickness 1px

**Orbit scatter plot:**
- Satellite positions: filled circles — green if nominal, red if faulted, amber if PSP
- Target formation triangle: dashed `#1E2D50` outline overlay
- Trails: last 30 positions per satellite, fading opacity

#### 11.5. Layout Principles

**Density over emptiness:** This is a mission control interface. Every pixel should carry information. Avoid excessive default padding.

**Spatial consistency:** Panels should stay in the same position during nominal and fault states. Data changes in place — colour shifts, numbers update, chart lines diverge. Nothing moves or hides. The operator's eye stays anchored.

**Event log as narrator:** The event log is the only panel that uses plain English. Judges who are not following the charts can track the story through the event log descriptions. Entries must be written as narrative: "T+01:47 — Phantom Sensor Protocol activated. Sat-A attitude error reduced from 2.0° to 0.09°. Formation reconfiguration initiated."

---

### 12. Technical Specifications

#### 12.1. Technology Stack

| Layer | Recommended Stack | Why It Works | Role in FSN |
|---|---|---|---|
| Simulation | Python 3.11, NumPy, SciPy, ruptures, stable-baselines3 | Keeps the core math in one language and preserves existing logic | Orbit propagation, PSP solve, fault detection, controller inference |
| Backend / state API | FastAPI, Pydantic, WebSocket or SSE, SQLAlchemy | Separates live state from UI and gives the frontend a clean contract | Commands, state snapshots, event streaming |
| Frontend | Next.js or React, TypeScript, Tailwind CSS, shadcn/ui, Plotly.js | Produces a cleaner, more polished interface than a monolithic dashboard file | Mission console, charts, cards, navigation |
| Persistence | SQLite for local demo, PostgreSQL for production | Local-first setup stays simple; production gets stronger concurrency and reliability | Telemetry, event log, command history |
| Quality / ops | pytest, ruff, mypy, Playwright, Docker Compose | Improves confidence and prevents regressions | Testing, linting, browser checks, reproducible startup |

**Implementation choice:** For a public-facing version, a Python backend plus a modern web frontend keeps the simulation logic untouched while giving the interface a cleaner, more credible product feel. For a fast hackathon demo, the same architecture can be collapsed into a local-only deployment using SQLite and a single background runner.

#### 12.2. Simulation Core Libraries

**NumPy** — All matrix and vector operations: CW state matrix construction, Wahba's problem eigensolver, ISL bearing vector computation, formation error calculation.

**SciPy** — `scipy.spatial.transform.Rotation` for quaternion operations; `scipy.linalg.eig` for the Wahba problem attitude solve.

**ruptures** — CUSUM change-point detection on the attitude error time series. Detects the fault transition within 15 seconds.

**stable-baselines3** — PPO policy definition, weight loading, and inference for `reconfig_controller.py`. Pre-trained weights load in one line; inference is < 5ms per step. No training happens at demo runtime.

#### 12.3. Environment Setup

```bash
pip install numpy scipy fastapi uvicorn pydantic sqlalchemy plotly pandas ruptures stable-baselines3
```

For local development, no external accounts, API keys, or Docker are required. Everything runs on a laptop.

#### 12.4. Running the Project

```bash
# Terminal 1 — run the simulation and API
python runner.py

# Terminal 2 — launch the frontend
npm run dev
```

The simulation loop writes to the database every 1 second. The frontend reads state via WebSocket/SSE and refreshes in real time.

---

### 13. Non-Functional Requirements

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

### 14. Constraints and Limitations

**No live RL training:** The Formation Reconfiguration agent (`reconfig_controller.py`) is trained offline and its weights are frozen before the demo. Runtime inference is fast (< 5ms per step) and deterministic.

**Simulated ISL, not real hardware:** Inter-satellite laser ranging is modelled with Gaussian noise consistent with commercial ISL specifications. No real satellite hardware is involved.

**No space weather or J2 perturbations:** The CW equations assume a circular reference orbit and no atmospheric drag or gravitational perturbations. Sufficient for a 500km altitude, 94-minute demo scenario.

**2D Hill frame visualisation:** The orbit plot shows the y-z (along-track / cross-track) plane only. The x (radial) component is near-zero for the target formation geometry and is omitted from the dashboard view for simplicity.

**SQLite for demo, PostgreSQL for production:** SQLite is sufficient for hackathon and demo scope. Production deployments should migrate to PostgreSQL for stronger concurrency.

---

### 15. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Layout shift during refresh | Makes the app feel broken and hard to read | Use fixed regions, reserved heights, and last-known-value rendering |
| Tight coupling between simulation and UI | One bug can take down the whole experience | Introduce a service boundary and read-only state snapshots |
| Too many controls | Users get lost and demo flow becomes messy | Limit controls to fault injection, reset, and replay |
| Ambiguous color usage | State becomes visually confusing | Reserve green, red, and amber for only one meaning each |

---

### 16. MVP Scope for Launch

- A stable mission control dashboard with fixed hierarchy and clear state badges.
- A robust telemetry pipeline with event logging and replay support.
- PSP activation, recovery visualization, and controller outputs that can be explained live.
- A modular codebase with tests for the PSP solver, event stream, and UI data contracts.

Anything beyond that — richer visualization, advanced analytics, multiple mission scenarios, or multi-user support — should come after the launch version is stable.

---

## App Architecture

### Layer Structure

| Layer | Responsibility | Key Modules |
|---|---|---|
| Simulation core | Physics, fault injection, PSP, controller logic | `orbital_model.py`, `fault_manager.py`, `psp_solver.py`, `reconfig_controller.py` |
| State services | Persistence, read models, command queue, validation | `db.py`, `repository.py`, `command_bus.py`, `schemas.py` |
| Presentation layer | Dashboard rendering, charts, interactions | `app/`, `components/`, `views/`, `styles/` |
| Integration layer | Simulation runner, API, background jobs, refresh loop | `api.py`, `runner.py`, WebSocket hub |

### Why This Structure Is Better

- The UI reads from a stable state snapshot instead of touching live simulation objects directly.
- Commands are queued and validated, which reduces race conditions and weird demo-time glitches.
- Each domain has one job, making it easier to test, debug, and swap components later.
- The simulation logic remains intact even if the frontend is redesigned again.

---

## Project Structure

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

## File Descriptions

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

## `requirements.txt`

```
numpy>=1.24.0
scipy>=1.11.0
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.0.0
sqlalchemy>=2.0.0
plotly>=5.17.0
pandas>=2.0.0
ruptures>=1.1.7
stable-baselines3>=2.0.0
pytest>=7.0.0
ruff>=0.4.0
mypy>=1.0.0
```

---

## Final Recommendation

Keep the physics and purpose exactly where they are. Rebuild the product surface around them. The new version should feel calm, legible, and operationally credible: a mission console with a story, not a demo with extra widgets.

**Preserve the logic. Improve the structure. Reduce the visual noise. Let the UI support the science instead of competing with it.**
