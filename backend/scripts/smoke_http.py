"""End-to-end test against the running loopback server; stores a named demo stream."""
import json
from pathlib import Path
import httpx
from aerotrace.ingest import read_session
from aerotrace.schema import regime

ROOT = Path(__file__).resolve().parents[1]
records, _ = read_session(ROOT/"data/public_examples/DataLog_20240819_session07_20240818_174831.csv")
start = next(i for i, r in enumerate(records) if i > 100 and regime(r.values) == "loaded")
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15) as client:
    assert client.get("/health").json()["status"] == "ok"
    for r in records[start:start+10]:
        packet = {"engine_id": "public-example", "session_id": "http-smoke-demo", "source_id": "ecu-unverified",
                  "timestamp": r.time.isoformat(), "mode": "replay", "values": r.values}
        response = client.post("/v1/telemetry", json=packet)
        assert response.status_code == 200, response.text
    latest = client.get("/v1/streams/public-example/http-smoke-demo/ecu-unverified/state").json()
    assert len(latest["cad"]["bindings"]) == 32
    mok = next(x for x in latest["cad"]["bindings"] if x["sensor_id"] == "MOK")
    assert len(mok["readings"]) == 2
    history = client.get("/v1/streams/public-example/http-smoke-demo/ecu-unverified/history").json()
    assert len(history["items"]) == 10
    assert client.post("/v1/telemetry", json=packet).json()["duplicate"]
    simulation = client.post("/v1/simulate/bench", json={"segments": [{"duration_s": 60, "shaft_power_kw": 50}]}).json()
    assert len(simulation["samples"]) == 60
    openapi = client.get("/openapi.json").json()
    (ROOT/"artifacts/openapi.json").write_text(json.dumps(openapi, indent=2), encoding="utf-8")
    report = {"http_smoke_pass": True, "sample_count": 10, "cad_bindings": 32,
              "composite_oil_sensor_readings": 2, "simulation_samples": 60,
              "schema_endpoints": len(openapi["paths"]), "latest_analysis_status": latest["analysis"]["status"],
              "mode": latest["freshness"]["status"], "note": "Loopback HTTP and stored historical examples, not a physical engine connection"}
    (ROOT/"artifacts/http_smoke.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT/"artifacts/example_telemetry_packet.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
