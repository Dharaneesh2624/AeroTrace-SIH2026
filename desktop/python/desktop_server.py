"""Private offline desktop companion. Started and owned by Electron, no ECU access."""
import argparse
import asyncio
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile
import threading
import time
from uuid import uuid4
from typing import Literal
import uvicorn
from fastapi import HTTPException, Query
from pydantic import BaseModel, Field
from aerotrace.api import create_app
from aerotrace.cad_bridge import bindings
from aerotrace.ingest import read_session
from aerotrace.model import load
from aerotrace.monitor import process, empty_state
from aerotrace.schema import Record, sanitize, timestamp
from aerotrace.faults import CATALOG, inject

class ImportRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=10_000_000)

class FaultRequest(BaseModel):
    source_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    kind: Literal['voltage_drop', 'boost_loss', 'oil_pressure_loss', 'coolant_rise', 'oil_sensor_dropout', 'coast_down']
    start_index: int = Field(ge=0, strict=True)
    duration_samples: int = Field(ge=2, le=20000, strict=True)
    severity: float = Field(gt=0, le=1, allow_inf_nan=False)

def connect(db):
    con = sqlite3.connect(str(db), timeout=30)
    con.row_factory = sqlite3.Row
    return con

def add_session(db, model, records, name, source, audit, injection=None):
    sid = uuid4().hex
    state = empty_state()
    counts = Counter()
    start = time.perf_counter()
    phase = 0.0
    previous = None
    with closing(connect(db)) as con, con:
        for i, record in enumerate(records):
            result, state = process(record, model, state)
            result["data_origin"] = source
            rpm = record.values.get('propeller_rpm')
            if previous is not None:
                dt = (record.time - previous.time).total_seconds()
                prior_rpm = previous.values.get('propeller_rpm')
                if .5 <= dt <= 1.5 and rpm is not None and prior_rpm is not None:
                    phase = phase + (rpm + prior_rpm) / 2 * 1.69 * 6 * dt / 120
            result['motion'] = {'display_phase_deg': phase % 720, 'display_total_deg': phase, 'slowdown': 120,
                                'quality': 'RPM-driven illustration; not measured crank phase'}
            previous = record
            if injection is not None: result['injection'] = injection[i]
            counts[result["analysis"]["status"]] += 1
            counts["persistent_anomaly_rows"] += int(result["persistent_anomaly"])
            counts["quality_warning_rows"] += int(any(q != "valid" for q in record.quality.values()))
            con.execute("INSERT INTO replay_samples VALUES(?,?,?)", (sid, i, json.dumps(result, allow_nan=False)))
        meta = {"id": sid, "name": name, "source": source, "count": len(records),
                "start": records[0].time.isoformat(), "end": records[-1].time.isoformat(),
                "model_id": model["model_id"], "audit": audit, "counts": dict(counts),
                "analysis_seconds": round(time.perf_counter()-start, 3),
                "limitations": "Research reconstruction. No confirmed diagnoses, validated RUL or airworthiness assessment."}
        con.execute("INSERT INTO replay_sessions VALUES(?,?)", (sid, json.dumps(meta)))
    return meta

def synthetic_records():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(480):
        wave = math.sin(i/45)
        values = {"boost_pa": 205000+5000*wave, "ambient_pa": 95000, "propeller_rpm": 2200+15*wave,
                  "oil_pressure_pa": 470000+8000*wave, "rail_pressure_pa": 105e6+2e6*wave,
                  "power_lever_pct": 65+2*wave, "coolant_c": 82+math.sin(i/100), "intake_c": 42+.6*wave,
                  "battery_v": 28.1+.05*wave, "fuel_pressure_pa": 420000+6000*wave,
                  "gearbox_oil_c": 76+.4*wave, "oil_c": 88+.7*wave, "prop_duty_pct": 12+wave,
                  "engine_status": 12, "oil_level_mm": 31, "engine_load_pct": 65+2*wave}
        if 180 <= i < 210: values["battery_v"] -= 8
        if 300 <= i < 320: values["boost_pa"] *= .55
        if 390 <= i < 405: values["oil_c"] = None
        v, q = sanitize(values)
        rows.append(Record(start+timedelta(seconds=i), "synthetic-demo", "illustrative-engine", v, q))
    return rows

def desktop_app(data_dir, assets, token):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    model = load(assets/"model.json")
    registry = assets/"cad_sensor_map.json"
    db = data_dir/"desktop.sqlite3"
    app = create_app(assets/"model.json", data_dir/"telemetry.sqlite3", token, registry)
    with closing(connect(db)) as con:
        con.executescript("PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS replay_sessions(id TEXT PRIMARY KEY, meta TEXT); CREATE TABLE IF NOT EXISTS replay_samples(session TEXT, idx INTEGER, result TEXT, PRIMARY KEY(session,idx));")
        existing = con.execute("SELECT count(*) FROM replay_sessions").fetchone()[0]
    if not existing:
        add_session(db, model, synthetic_records(), "Synthetic systems demo", "synthetic", {
            "note": "Generated locally; not an actual AE300 flight", "injections": [
                {"start_s": 180, "end_s": 210, "kind": "voltage drop"},
                {"start_s": 300, "end_s": 320, "kind": "boost drop"},
                {"start_s": 390, "end_s": 405, "kind": "oil sensor dropout"}]})

    @app.get("/v1/desktop/sessions")
    def sessions():
        with closing(connect(db)) as con:
            rows = con.execute("SELECT meta FROM replay_sessions ORDER BY rowid DESC LIMIT 100").fetchall()
        return [json.loads(r[0]) for r in rows]

    @app.post("/v1/desktop/import")
    def import_csv(request: ImportRequest):
        if not request.filename.lower().endswith(".csv"):
            raise HTTPException(422, "Import an AustroView CSV, not a raw .ae3 file")
        # Filename is metadata only; never used as a filesystem path.
        with tempfile.TemporaryDirectory(prefix="aerotrace-import-") as scratch:
            target = Path(scratch)/"import.csv"
            target.write_text(request.content, encoding="utf-8")
            try:
                records, audit = read_session(target, engine="imported-unverified-engine")
            except (ValueError, KeyError, TypeError) as exc:
                raise HTTPException(422, str(exc)) from exc
        if not records or len(records) > 20000:
            raise HTTPException(422, "A session must contain 1..20,000 usable records")
        digest = hashlib.sha256(request.content.encode()).hexdigest()
        for prior in sessions():
            if prior.get("audit", {}).get("content_sha256") == digest:
                return prior
        audit.update(file=request.filename, content_sha256=digest)
        return add_session(db, model, records, request.filename, "imported_log", audit)

    def require_session(sid):
        with closing(connect(db)) as con:
            row = con.execute("SELECT meta FROM replay_sessions WHERE id=?", (sid,)).fetchone()
        if row is None: raise HTTPException(404, "Unknown replay session")
        return json.loads(row[0])

    @app.get('/v1/desktop/faults')
    def fault_catalog():
        return CATALOG

    @app.post('/v1/desktop/faults')
    def create_fault(request: FaultRequest):
        meta = require_session(request.source_id)
        if meta['source'] == 'fault_injected':
            raise HTTPException(422, 'Choose an original or synthetic source, not an already injected session')
        with closing(connect(db)) as con:
            rows = con.execute('SELECT result FROM replay_samples WHERE session=? ORDER BY idx', (request.source_id,)).fetchall()
        originals = [json.loads(row['result']) for row in rows]
        records = [Record(timestamp(r['timestamp']), r['session_id'], r['engine_id'], r['values'], r['quality']) for r in originals]
        try:
            modified, provenance = inject(records, request.kind, request.start_index, request.duration_samples, request.severity)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        audit = {'source_id': request.source_id, 'source_name': meta['name'], 'source_origin': meta['source'],
                 'fault': request.model_dump(), 'effect': CATALOG[request.kind]['effect'],
                 'changed_samples': sum(p['changed'] for p in provenance),
                 'source_persistent_rows': meta['counts'].get('persistent_anomaly_rows', 0),
                 'note': 'Counterfactual signal injection; baseline may already contain anomalies. Source log is unchanged. Interval uses sample indices, not elapsed seconds.'}
        return add_session(db, model, modified, 'INJECTED · ' + CATALOG[request.kind]['label'], 'fault_injected', audit, provenance)

    @app.get("/v1/desktop/sessions/{sid}/window")
    def window(sid: str, start: int = Query(0, ge=0), limit: int = Query(120, ge=1, le=500)):
        meta = require_session(sid)
        with closing(connect(db)) as con:
            rows = con.execute("SELECT idx,result FROM replay_samples WHERE session=? AND idx>=? ORDER BY idx LIMIT ?", (sid, start, limit)).fetchall()
            legacy_motion = {}
            if rows and 'display_total_deg' not in json.loads(rows[0]['result']).get('motion', {}):
                # Legacy sessions keep raw data unchanged; derive deterministic slowed
                # poses from their prefix on read, including correct seek behaviour.
                phase, prior = 0.0, None
                for old in con.execute('SELECT idx,result FROM replay_samples WHERE session=? AND idx<=? ORDER BY idx', (sid, start+limit-1)):
                    r = json.loads(old['result'])
                    if prior:
                        dt = (timestamp(r['timestamp'])-timestamp(prior['timestamp'])).total_seconds()
                        rpm, last = r['values'].get('propeller_rpm'), prior['values'].get('propeller_rpm')
                        if .5 <= dt <= 1.5 and rpm is not None and last is not None:
                            phase = phase+(rpm+last)/2*1.69*6*dt/120
                    legacy_motion[old['idx']] = {'display_phase_deg': phase%720, 'display_total_deg': phase, 'slowdown': 120}
                    prior = r
        results = []
        for row in rows:
            result = json.loads(row["result"])
            result["index"] = row["idx"]
            if row['idx'] in legacy_motion: result['motion'] = legacy_motion[row['idx']]
            result["cad"] = bindings(result, registry)
            results.append(result)
        return {"session": meta, "items": results}

    @app.get("/v1/desktop/sessions/{sid}/overview")
    def overview(sid: str):
        meta = require_session(sid)
        points = []
        event_intervals = []
        current = None
        stride = max(1, meta["count"]//1200)
        with closing(connect(db)) as con:
            for row in con.execute("SELECT idx,result FROM replay_samples WHERE session=? ORDER BY idx", (sid,)):
                r = json.loads(row["result"])
                if row["idx"] % stride == 0:
                    points.append({"index": row["idx"], "timestamp": r["timestamp"], "values": r["values"],
                                   "ratio": r["analysis"].get("score_ratio"), "alert": r["persistent_anomaly"]})
                if r["persistent_anomaly"]:
                    if current is None: current = {"start": row["idx"], "timestamp": r["timestamp"], "signals": [h["signal"] for h in r["hypotheses"]]}
                    current["end"] = row["idx"]
                elif current:
                    event_intervals.append(current)
                    current = None
        if current: event_intervals.append(current)
        return {"session": meta, "points": points, "events": event_intervals}

    @app.get("/v1/desktop/sessions/{sid}/report")
    def report(sid: str):
        return {"format": "AeroTrace research report v1", "session": require_session(sid),
                "rul_hours": None, "confirmed_faults": None,
                "disclaimer": "Anomalies are hypotheses for engineering review, not maintenance instructions or airworthiness decisions."}

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args()
    token = os.environ.get("AEROTRACE_DESKTOP_TOKEN")
    if not token or len(token) < 32: raise RuntimeError("Private desktop token required")
    assets = args.assets or Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))/"assets"
    app = desktop_app(args.data_dir, assets, token)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    sock.setblocking(False)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=sock.getsockname()[1], log_level="warning", access_log=False))
    # Closing stdin (parent exits/crashes) asks uvicorn to exit; no orphan service.
    def parent_watch():
        for _ in sys.stdin: pass
        server.should_exit = True
    threading.Thread(target=parent_watch, daemon=True).start()
    print("AEROTRACE_READY:"+json.dumps({"port": sock.getsockname()[1]}), flush=True)
    server.run(sockets=[sock])

if __name__ == "__main__":
    main()
