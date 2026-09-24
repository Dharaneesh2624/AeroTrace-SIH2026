"""Local-first research API. Deployment is deliberately single-worker initially."""
from datetime import datetime, timezone
import hmac
import os
from pathlib import Path
from typing import Annotated, Literal
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat
from . import __version__
from .model import load
from .schema import Record, UNITS, sanitize, timestamp
from .store import Store, Conflict
from .physics import simulate_bench
from .cad_bridge import bindings

ROOT = Path(__file__).resolve().parents[1]
Identifier = Annotated[str, Field(min_length=1, max_length=96, pattern=r"^[A-Za-z0-9_.-]+$")]

class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    engine_id: Identifier
    session_id: Identifier
    source_id: Identifier
    timestamp: str = Field(max_length=40)
    mode: Literal["replay", "live"] = "replay"
    values: dict[str, FiniteFloat | None] = Field(max_length=16)

class Segment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    duration_s: int = Field(ge=1, le=3600, strict=True)
    shaft_power_kw: FiniteFloat = Field(ge=0, le=123.5)
    ambient_c: FiniteFloat = Field(default=25, ge=-30, le=55)
    ambient_pa: FiniteFloat = Field(default=101325, ge=30000, le=110000)
    cooling_factor: FiniteFloat = Field(default=1, ge=.2, le=1.5)

class BenchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    initial_c: FiniteFloat = Field(default=25, ge=-30, le=150)
    segments: list[Segment] = Field(min_length=1, max_length=10)

def create_app(model_path=None, database=None, api_key=None, cad_path=None):
    path = Path(model_path or os.environ.get("AEROTRACE_MODEL", ROOT/"artifacts/model.json"))
    model = load(path) if path.exists() else None
    store = Store(database or os.environ.get("AEROTRACE_DB", ROOT/"artifacts/telemetry.sqlite3"))
    key = api_key if api_key is not None else os.environ.get("AEROTRACE_API_KEY")
    registry = Path(cad_path or ROOT/"config/cad_sensor_map.json")

    def authorize(x_api_key: str | None = Header(default=None)):
        if key and not hmac.compare_digest(x_api_key or "", key):
            raise HTTPException(401, "API key required")

    app = FastAPI(title="AeroTrace AE300 research backend", version=__version__, dependencies=[Depends(authorize)])
    app.state.store = store

    @app.get("/health")
    def health():
        return {"status": "ok" if model else "model_not_trained", "model_id": model["model_id"] if model else None,
                "safety": "research_only", "authentication": "api_key" if key else "local_loopback_only"}

    @app.get("/v1/schema")
    def schema():
        return {"units": UNITS, "cad_bindings_available": registry.exists(),
                "timestamps": "explicit ISO8601 UTC offset; CSV UTC assumption is adapter-specific",
                "limits": "Plausibility bounds are NOT manufacturer operating limits"}

    @app.get("/v1/model")
    def model_card():
        if model is None:
            raise HTTPException(503, "Train the reference model first")
        return {k: model[k] for k in ("model_id", "algorithm", "training_health", "scope", "split")}

    @app.post("/v1/telemetry")
    def ingest(packet: Packet):
        if model is None:
            raise HTTPException(503, "Train the reference model first")
        try:
            dt = timestamp(packet.timestamp)
            if packet.mode == "live":
                age = (datetime.now(timezone.utc)-dt).total_seconds()
                if age > 60 or age < -5:
                    raise ValueError("Live packet stale/future; use replay mode for history")
            values, quality = sanitize(packet.values)
            record = Record(dt, packet.session_id, packet.engine_id, values, quality)
            result = store.ingest(record, packet.source_id, packet.mode, model, packet.model_dump())
            return result
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/v1/streams")
    def streams():
        return store.streams()

    @app.get("/v1/streams/{engine}/{session}/{source}/history")
    def history(engine: str, session: str, source: str, after: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000)):
        rows = store.history(engine, session, source, after, limit)
        return {"items": rows, "next_after": rows[-1]["sample_id"] if rows else after}

    @app.get("/v1/streams/{engine}/{session}/{source}/state")
    def state(engine: str, session: str, source: str):
        result = store.latest(engine, session, source)
        if result is None:
            raise HTTPException(404, "Unknown stream")
        age = (datetime.now(timezone.utc)-timestamp(result["timestamp"])).total_seconds()
        result["freshness"] = {"age_s": age, "status": "historical_replay" if result["mode"] == "replay" else "stale" if age > 5 else "recent"}
        if registry.exists():
            result["cad"] = bindings(result, registry)
        return result

    @app.post("/v1/simulate/bench")
    def simulate(request: BenchRequest):
        try:
            return simulate_bench([s.model_dump() for s in request.segments], request.initial_c)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/v1/capabilities")
    def capabilities():
        return {"implemented": ["CSV replay", "canonical live JSON ingestion", "physics identities", "two-node synthetic bench simulation",
                                "contextual residual anomaly detection", "persistent event evidence", "CAD signal bindings", "SQLite history"],
                "not_validated": ["real fault classification", "remaining useful life", "failure probability", "mission reliability", "airworthiness"],
                "missing_measurements": ["EGT", "CHT", "fuel flow", "high-rate vibration", "injection timing", "alternator current"],
                "interfaces_not_implemented": ["raw .ae3 decoding", "LiveView parsing", "CAN hardware acquisition", "ECU commands", "frontend dashboard"]}

    return app
