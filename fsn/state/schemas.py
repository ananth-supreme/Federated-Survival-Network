from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SatelliteSchema(BaseModel):
    id: int
    name: str
    role: str
    mass_kg: float
    fuel_budget_ms: float
    fuel_remaining_ms: float

class TelemetrySchema(BaseModel):
    id: Optional[int] = None
    sim_time_s: float
    satellite_id: int
    pos_x: float = 0.0
    pos_y: float
    pos_z: float
    vel_x: float = 0.0
    vel_y: float
    vel_z: float
    attitude_error_deg: float
    sensor_source: str
    fault_active: int
    battery_soc: float
    psp_attitude_error_deg: Optional[float] = None
    role: Optional[str] = None
    name: Optional[str] = None

class ISLMeasurementSchema(BaseModel):
    id: Optional[int] = None
    sim_time_s: float
    from_sat_id: int
    to_sat_id: int
    range_m: float
    range_noise_m: float
    bearing_az_deg: float
    bearing_el_deg: float
    is_psp_link: int

class EventSchema(BaseModel):
    id: Optional[int] = None
    sim_time_s: float
    event_type: str
    satellite_id: Optional[int] = None
    description: str
    formation_error_m: float
    attitude_error_deg: float

class CommandSchema(BaseModel):
    id: Optional[int] = None
    issued_at: float
    command_type: str
    status: str
    payload: Optional[str] = None
