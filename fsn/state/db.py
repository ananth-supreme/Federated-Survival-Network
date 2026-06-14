from sqlalchemy import create_engine, Column, Integer, Float, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class SatelliteTable(Base):
    __tablename__ = 'satellites'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    role = Column(String)
    mass_kg = Column(Float)
    fuel_budget_ms = Column(Float)
    fuel_remaining_ms = Column(Float)

class TelemetryTable(Base):
    __tablename__ = 'telemetry'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_time_s = Column(Float)
    satellite_id = Column(Integer, ForeignKey('satellites.id'))
    pos_x = Column(Float)
    pos_y = Column(Float)
    pos_z = Column(Float)
    vel_x = Column(Float)
    vel_y = Column(Float)
    vel_z = Column(Float)
    attitude_error_deg = Column(Float)
    sensor_source = Column(String)
    fault_active = Column(Integer)
    battery_soc = Column(Float)
    psp_attitude_error_deg = Column(Float, nullable=True)

class ISLMeasurementTable(Base):
    __tablename__ = 'isl_measurements'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_time_s = Column(Float)
    from_sat_id = Column(Integer, ForeignKey('satellites.id'))
    to_sat_id = Column(Integer, ForeignKey('satellites.id'))
    range_m = Column(Float)
    range_noise_m = Column(Float)
    bearing_az_deg = Column(Float)
    bearing_el_deg = Column(Float)
    is_psp_link = Column(Integer)

class EventTable(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    sim_time_s = Column(Float)
    event_type = Column(String)
    satellite_id = Column(Integer, ForeignKey('satellites.id'), nullable=True)
    description = Column(String)
    formation_error_m = Column(Float)
    attitude_error_deg = Column(Float)

class CommandTable(Base):
    __tablename__ = 'command_queue'
    id = Column(Integer, primary_key=True, autoincrement=True)
    issued_at = Column(Float)
    command_type = Column(String)
    status = Column(String)
    payload = Column(String, nullable=True)

# Database connection
DB_URL = "sqlite:///fsn_mission.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(clear=False):
    Base.metadata.create_all(bind=engine)
    if clear:
        clear_db()

    db = SessionLocal()
    if db.query(SatelliteTable).count() == 0:
        sats = [
            SatelliteTable(id=1, name="SAT_A", role="CHIEF", mass_kg=50.0, fuel_budget_ms=50.0, fuel_remaining_ms=50.0),
            SatelliteTable(id=2, name="SAT_B", role="DEPUTY", mass_kg=50.0, fuel_budget_ms=50.0, fuel_remaining_ms=50.0),
            SatelliteTable(id=3, name="SAT_C", role="DEPUTY", mass_kg=50.0, fuel_budget_ms=50.0, fuel_remaining_ms=50.0),
        ]
        db.add_all(sats)
        db.commit()
    elif clear:
        for sat in db.query(SatelliteTable).all():
            sat.fuel_remaining_ms = sat.fuel_budget_ms
        db.commit()
    db.close()

def clear_db():
    db = SessionLocal()
    db.query(TelemetryTable).delete()
    db.query(ISLMeasurementTable).delete()
    db.query(EventTable).delete()
    db.query(CommandTable).delete()
    db.commit()
    db.close()
