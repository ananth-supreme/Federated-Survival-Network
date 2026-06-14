import time
import numpy as np
from fsn.simulation.orbital_model import Satellite
from fsn.simulation.isl_ranging import get_isl_measurements
from fsn.simulation.fault_manager import FaultManager
from fsn.state.db import (
    init_db,
    SessionLocal,
    TelemetryTable,
    ISLMeasurementTable,
    EventTable,
    CommandTable,
)
from fsn.constants import (
    SAT_B_START_POS,
    SAT_C_START_POS,
    SIM_TICK_S,
    NOMINAL_ATTITUDE_NOISE_DEG,
    FAULT_ATTITUDE_NOISE_DEG,
    PSP_RECOVERY_DELAY_S,
    PSP_CONVERGE_DURATION_S,
    ATTITUDE_CRITICAL_THRESHOLD_DEG,
    FORMATION_RECOVERY_DURATION_S,
    FAULT_FORMATION_OFFSETS,
)
SAT_IDS = {"SAT_A": 1, "SAT_B": 2, "SAT_C": 3}
NOMINAL_POSITIONS = {
    "SAT_A": np.array([0.0, 0.0, 0.0]),
    "SAT_B": np.array(SAT_B_START_POS),
    "SAT_C": np.array(SAT_C_START_POS),
}
ISL_PAIRS = [
    ("SAT_A", "SAT_B", 1, 2),
    ("SAT_A", "SAT_C", 1, 3),
    ("SAT_B", "SAT_C", 2, 3),
]


def compute_formation_error(satellites: dict) -> float:
    errors = []
    for name, sat in satellites.items():
        pos = sat.state[:3]
        errors.append(float(np.linalg.norm(pos - NOMINAL_POSITIONS[name])))
    return max(errors)


def log_event_once(db, sim_time, event_type, satellite_id, description, formation_error_m, attitude_error_deg):
    if db.query(EventTable).filter(EventTable.event_type == event_type).count() == 0:
        db.add(
            EventTable(
                sim_time_s=sim_time,
                event_type=event_type,
                satellite_id=satellite_id,
                description=description,
                formation_error_m=formation_error_m,
                attitude_error_deg=attitude_error_deg,
            )
        )
        db.commit()
        return True
    return False


def update_sat_a_attitude(sat_a, sim_time, fault_inject_time, psp_active):
    """Phase fault → converge → stable attitude knowledge for Sat-A."""
    if fault_inject_time is None:
        error = abs(np.random.normal(0, NOMINAL_ATTITUDE_NOISE_DEG))
        sat_a.raw_attitude_error = error
        sat_a.attitude_knowledge_error = error
        sat_a.sensor_source = "PHYSICAL"
        sat_a.fault_active = False
        return error, None, "nominal"

    elapsed = sim_time - fault_inject_time
    sat_a.fault_active = True

    if elapsed < PSP_RECOVERY_DELAY_S:
        error = abs(np.random.normal(0, FAULT_ATTITUDE_NOISE_DEG))
        sat_a.raw_attitude_error = error
        sat_a.attitude_knowledge_error = error
        sat_a.sensor_source = "FAILED"
        return error, None, "fault"

    if elapsed < PSP_RECOVERY_DELAY_S + PSP_CONVERGE_DURATION_S:
        progress = (elapsed - PSP_RECOVERY_DELAY_S) / PSP_CONVERGE_DURATION_S
        progress = 1.0 - (1.0 - progress) ** 2
        peak = FAULT_ATTITUDE_NOISE_DEG
        target = abs(np.random.normal(0, NOMINAL_ATTITUDE_NOISE_DEG * 3.0))
        knowledge = peak * (1.0 - progress) + target * progress
        knowledge = max(knowledge, target)
        sat_a.raw_attitude_error = knowledge
        sat_a.attitude_knowledge_error = knowledge
        sat_a.sensor_source = "PHANTOM" if progress > 0.15 else "FAILED"
        return knowledge, knowledge, "converging"

    knowledge = abs(np.random.normal(0, NOMINAL_ATTITUDE_NOISE_DEG * 3.0))
    sat_a.raw_attitude_error = knowledge
    sat_a.attitude_knowledge_error = knowledge
    sat_a.sensor_source = "PHANTOM"
    sat_a.fault_active = False
    return knowledge, knowledge, "stable"


def apply_formation_positions(satellites, fault_inject_time, sim_time):
    """Hold formation at station unless faulted; recover within 5s."""
    for name, sat in satellites.items():
        nominal = NOMINAL_POSITIONS[name]
        if fault_inject_time is None:
            sat.state[:3] = nominal
            sat.state[3:] = 0.0
            continue

        elapsed = sim_time - fault_inject_time
        offset = np.array(FAULT_FORMATION_OFFSETS[name])

        if elapsed <= 0:
            sat.state[:3] = nominal + offset
        elif elapsed < FORMATION_RECOVERY_DURATION_S:
            progress = elapsed / FORMATION_RECOVERY_DURATION_S
            progress = 1.0 - (1.0 - progress) ** 2
            sat.state[:3] = nominal + offset * (1.0 - progress)
        else:
            sat.state[:3] = nominal

        sat.state[3:] = 0.0


def run_simulation():
    print("--- FSN SIMULATION STARTING ---")
    init_db(clear=True)

    fault_manager = FaultManager(window_size=15)

    sat_a = Satellite("SAT_A", np.zeros(6), "CHIEF")
    sat_b = Satellite("SAT_B", np.concatenate([SAT_B_START_POS, [0.0, 0.0, 0.0]]), "DEPUTY")
    sat_c = Satellite("SAT_C", np.concatenate([SAT_C_START_POS, [0.0, 0.0, 0.0]]), "DEPUTY")

    satellites = {"SAT_A": sat_a, "SAT_B": sat_b, "SAT_C": sat_c}
    sim_time = 0.0
    fault_inject_time = None
    psp_active = False
    formation_recovered = False
    recovery_complete = False

    while True:
        db = SessionLocal()

        pending_cmd = db.query(CommandTable).filter(CommandTable.status == "PENDING").first()
        if pending_cmd:
            if pending_cmd.command_type == "INJECT_FAULT":
                fault_manager.inject_fault()
                fault_inject_time = sim_time
                sat_a.fault_active = True
                sat_a.sensor_source = "FAILED"
                pending_cmd.status = "EXECUTED"
            elif pending_cmd.command_type == "RESET":
                pending_cmd.status = "EXECUTED"
                db.commit()
                db.close()
                print("RESETTING SIMULATION...")
                return "RESET"
            db.commit()

        apply_formation_positions(satellites, fault_inject_time, sim_time)

        sat_states = {name: sat.state for name, sat in satellites.items()}
        formation_error = compute_formation_error(satellites)
        isl_measurements = get_isl_measurements(sat_states)

        for name, sat in satellites.items():
            if name == "SAT_A" and fault_manager.fault_active:
                display_error, psp_error, phase = update_sat_a_attitude(
                    sat_a, sim_time, fault_inject_time, psp_active
                )
                sat_a._display_error = display_error
                sat_a._psp_error = psp_error
                sat_a._phase = phase
            else:
                sat.raw_attitude_error = abs(np.random.normal(0, NOMINAL_ATTITUDE_NOISE_DEG))
                sat.attitude_knowledge_error = sat.raw_attitude_error
                sat.fault_active = False
                if sat.sensor_source != "PHANTOM":
                    sat.sensor_source = "PHYSICAL"
                sat._display_error = sat.raw_attitude_error
                sat._psp_error = None
                sat._phase = "nominal"

        if fault_manager.fault_active and fault_inject_time is not None:
            elapsed = sim_time - fault_inject_time
            phase = getattr(sat_a, "_phase", "fault")

            if phase == "converging" and not psp_active:
                psp_active = True
                log_event_once(
                    db,
                    sim_time,
                    "PSP_ACTIVATED",
                    1,
                    f"T+{sim_time:.0f}s — Phantom Sensor Protocol activated. "
                    f"Sat-A attitude knowledge converging toward nominal.",
                    formation_error,
                    sat_a._display_error,
                )

            if phase == "stable" and not recovery_complete:
                log_event_once(
                    db,
                    sim_time,
                    "ATTITUDE_STABILIZED",
                    1,
                    f"T+{sim_time:.0f}s — Attitude knowledge stabilized below "
                    f"{ATTITUDE_CRITICAL_THRESHOLD_DEG}° threshold via Phantom Sensor.",
                    formation_error,
                    sat_a._display_error,
                )

        if (
            fault_manager.fault_active
            and fault_inject_time is not None
            and not fault_manager.fault_detected
            and getattr(sat_a, "_phase", "") == "fault"
            and fault_manager.check_fault(sat_a.raw_attitude_error)
        ):
            log_event_once(
                db,
                sim_time,
                "FAULT_DETECTED",
                1,
                "Sat-A star tracker failure detected. Formation stability compromised.",
                formation_error,
                sat_a.raw_attitude_error,
            )
            log_event_once(
                db,
                sim_time,
                "SAFE_MODE_ENTERED",
                1,
                "Sat-A entering safe mode. Attitude held by Phantom Sensor; no maneuvers on Sat-A.",
                formation_error,
                sat_a.raw_attitude_error,
            )

        recovery_active = (
            fault_manager.fault_active
            and fault_inject_time is not None
            and (sim_time - fault_inject_time) >= FORMATION_RECOVERY_DURATION_S
        )
        if recovery_active and not formation_recovered:
            formation_recovered = True
            log_event_once(
                db,
                sim_time,
                "RECONFIG_STARTED",
                1,
                "Formation reconfiguration complete. All satellites returned to station.",
                formation_error,
                sat_a.raw_attitude_error,
            )

        if (
            fault_manager.fault_active
            and fault_inject_time is not None
            and not recovery_complete
            and (sim_time - fault_inject_time) >= FORMATION_RECOVERY_DURATION_S
            and formation_error < 5.0
        ):
            recovery_complete = True
            log_event_once(
                db,
                sim_time,
                "RECOVERY_COMPLETE",
                1,
                f"Formation restored to nominal triangle within {FORMATION_RECOVERY_DURATION_S:.0f}s.",
                formation_error,
                sat_a.attitude_knowledge_error,
            )

        for name, sat in satellites.items():
            display_error = getattr(sat, "_display_error", sat.raw_attitude_error)
            psp_val = getattr(sat, "_psp_error", None)
            db.add(
                TelemetryTable(
                    sim_time_s=sim_time,
                    satellite_id=SAT_IDS[name],
                    pos_x=float(sat.state[0]),
                    pos_y=float(sat.state[1]),
                    pos_z=float(sat.state[2]),
                    vel_x=float(sat.state[3]),
                    vel_y=float(sat.state[4]),
                    vel_z=float(sat.state[5]),
                    attitude_error_deg=float(display_error),
                    sensor_source=sat.sensor_source,
                    fault_active=1 if sat.fault_active else 0,
                    battery_soc=0.95,
                    psp_attitude_error_deg=float(psp_val) if psp_val is not None else None,
                )
            )

        for from_name, to_name, from_id, to_id in ISL_PAIRS:
            key = (from_name, to_name)
            meas = isl_measurements[key]
            is_psp = 1 if fault_manager.fault_active and "SAT_A" in key and psp_active else 0
            db.add(
                ISLMeasurementTable(
                    sim_time_s=sim_time,
                    from_sat_id=from_id,
                    to_sat_id=to_id,
                    range_m=meas["range_m"],
                    range_noise_m=abs(meas["range_m"] - np.linalg.norm(
                        satellites[to_name].state[:3] - satellites[from_name].state[:3]
                    )),
                    bearing_az_deg=meas["az_deg"],
                    bearing_el_deg=meas["el_deg"],
                    is_psp_link=is_psp,
                )
            )

        db.commit()
        db.close()

        sim_time += SIM_TICK_S
        time.sleep(0.1)


if __name__ == "__main__":
    while True:
        result = run_simulation()
        if result != "RESET":
            break
        time.sleep(1)
