from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from fsn.state.db import (
    SessionLocal,
    TelemetryTable,
    EventTable,
    CommandTable,
    ISLMeasurementTable,
    SatelliteTable,
)
from fsn.state.schemas import (
    TelemetrySchema,
    EventSchema,
    CommandSchema,
    ISLMeasurementSchema,
)

app = FastAPI(title="FSN Mission Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_latest_telemetry(db):
    satellites = {s.id: s for s in db.query(SatelliteTable).all()}
    latest = []
    for sat_id in range(1, 4):
        row = (
            db.query(TelemetryTable)
            .filter(TelemetryTable.satellite_id == sat_id)
            .order_by(TelemetryTable.id.desc())
            .first()
        )
        if row:
            payload = TelemetrySchema.model_validate(row, from_attributes=True).model_dump()
            sat = satellites.get(sat_id)
            if sat:
                payload["role"] = sat.role
                payload["name"] = sat.name
            latest.append(payload)
    return latest


def get_latest_isl(db):
    latest = []
    for from_id, to_id in [(1, 2), (1, 3), (2, 3)]:
        row = (
            db.query(ISLMeasurementTable)
            .filter(
                ISLMeasurementTable.from_sat_id == from_id,
                ISLMeasurementTable.to_sat_id == to_id,
            )
            .order_by(ISLMeasurementTable.id.desc())
            .first()
        )
        if row:
            latest.append(
                ISLMeasurementSchema.model_validate(row, from_attributes=True).model_dump()
            )
    return latest


@app.get("/state")
async def get_current_state():
    db = SessionLocal()
    latest_telemetry = get_latest_telemetry(db)
    events = (
        db.query(EventTable)
        .order_by(EventTable.sim_time_s.desc())
        .limit(10)
        .all()
    )
    isl = get_latest_isl(db)
    db.close()
    return {
        "telemetry": latest_telemetry,
        "events": [
            EventSchema.model_validate(e, from_attributes=True).model_dump() for e in events
        ],
        "isl": isl,
    }


@app.post("/commands")
async def post_command(command: CommandSchema):
    db = SessionLocal()
    db_cmd = CommandTable(
        issued_at=command.issued_at,
        command_type=command.command_type,
        status="PENDING",
        payload=command.payload,
    )
    db.add(db_cmd)
    db.commit()
    db.close()
    return {"status": "queued"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            events = (
                db.query(EventTable)
                .order_by(EventTable.sim_time_s.asc())
                .limit(20)
                .all()
            )
            data = {
                "telemetry": get_latest_telemetry(db),
                "events": [
                    EventSchema.model_validate(e, from_attributes=True).model_dump()
                    for e in events
                ],
                "isl": get_latest_isl(db),
            }
            await websocket.send_json(data)
            db.close()
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
