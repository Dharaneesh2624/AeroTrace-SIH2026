from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import json
import pytest
from fastapi.testclient import TestClient
from aerotrace.api import create_app
from aerotrace.model import save
from aerotrace.store import Store, Conflict
from aerotrace.cad_bridge import bindings

def test_store_idempotency_restart_and_conflict(tmp_path, model, record):
    p = tmp_path/"db.sqlite3"
    db = Store(p)
    first = db.ingest(record, "ecuA", "replay", model, {"x": 1})
    second = Store(p).ingest(record, "ecuA", "replay", model, {"x": 1})
    assert second["duplicate"] and first["sample_id"] == second["sample_id"]
    with pytest.raises(Conflict): db.ingest(record, "ecuA", "replay", model, {"x": 2})
    with pytest.raises(Conflict): db.ingest(replace(record, time=record.time-timedelta(seconds=1)), "ecuA", "replay", model, {})
    other = db.ingest(record, "ecuB", "replay", model, {})
    assert not other["duplicate"]
    assert len(db.streams()) == 2

def test_concurrent_duplicate(tmp_path, model, record):
    db = Store(tmp_path/"db.sqlite3")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: db.ingest(record, "ecu", "replay", model, {}), range(8)))
    assert sum(not x["duplicate"] for x in results) == 1
    assert len(db.history("engine", "session", "ecu")) == 1

def test_api_validation_and_readback(tmp_path, model, record):
    p = tmp_path/"model.json"
    save(model, p)
    app = create_app(p, tmp_path/"db.sqlite3", api_key="test-key")
    client = TestClient(app)
    assert client.get("/health").status_code == 401
    client.headers["X-API-Key"] = "test-key"
    assert client.get("/health").status_code == 200
    packet = {"engine_id": "engine", "session_id": "session", "source_id": "ecu", "timestamp": record.time.isoformat(),
              "mode": "replay", "values": record.values}
    response = client.post("/v1/telemetry", json=packet)
    assert response.status_code == 200, response.text
    assert client.post("/v1/telemetry", json=packet).json()["duplicate"]
    altered = dict(packet, values=dict(packet["values"], battery_v=27))
    assert client.post("/v1/telemetry", json=altered).status_code == 409
    assert client.post("/v1/telemetry", json=dict(packet, mode="live")).status_code == 422
    assert client.post("/v1/telemetry", json=dict(packet, timestamp="2024-01-01")).status_code == 422
    assert client.post("/v1/telemetry", json=dict(packet, values={"rpm": 20})).status_code == 422
    state = client.get("/v1/streams/engine/session/ecu/state").json()
    assert state["freshness"]["status"] == "historical_replay"
    page = client.get("/v1/streams/engine/session/ecu/history?limit=1").json()
    assert len(page["items"]) == 1
    assert client.get(f"/v1/streams/engine/session/ecu/history?after={page['next_after']}").json()["items"] == []
    assert client.get("/v1/streams/not/here/ecu/state").status_code == 404
    assert client.get("/openapi.json").status_code == 200

def test_api_missing_model(tmp_path):
    c = TestClient(create_app(tmp_path/"absent.json", tmp_path/"db.sqlite3"))
    assert c.get("/health").json()["status"] == "model_not_trained"
    assert c.get("/v1/model").status_code == 503
    assert c.post("/v1/simulate/bench", json={"segments": [{"duration_s": 20, "shaft_power_kw": 50}]}).status_code == 200
    assert c.post("/v1/simulate/bench", json={"segments": [{"duration_s": 3600, "shaft_power_kw": 50}]*3}).status_code == 422

def test_cad_composite_signal(tmp_path, model, record):
    from aerotrace.monitor import process
    result, _ = process(record, model)
    p = tmp_path/"sensors.json"
    p.write_text(json.dumps([{"id": "MOK", "object": "Sensor_MOK", "telemetry_channel": "811/814"},
                             {"id": "EGT", "object": "Sensor_EGT", "telemetry_channel": None}]))
    rows = bindings(result, p)["bindings"]
    assert len(rows[0]["readings"]) == 2
    assert rows[1]["value"] is None

