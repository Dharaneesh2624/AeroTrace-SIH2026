"""Replay a local CSV to the local API; no connection to CAN or an engine."""
import argparse
import os
from pathlib import Path
import time
import httpx
from aerotrace.ingest import read_session

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--session", default="demo-replay")
    p.add_argument("--limit", type=int, default=120)
    p.add_argument("--speed", type=float, default=10)
    a = p.parse_args()
    if not 1 <= a.limit <= 100000 or not .1 <= a.speed <= 1000:
        p.error("limit 1..100000 and speed .1..1000 required")
    records, _ = read_session(a.csv)
    headers = {"X-API-Key": os.environ["AEROTRACE_API_KEY"]} if os.environ.get("AEROTRACE_API_KEY") else {}
    with httpx.Client(base_url="http://127.0.0.1:8000", headers=headers, timeout=15) as client:
        for record in records[:a.limit]:
            packet = {"engine_id": "public-example", "session_id": a.session, "source_id": "ecu-unverified",
                      "timestamp": record.time.isoformat(), "mode": "replay", "values": record.values}
            response = client.post("/v1/telemetry", json=packet)
            response.raise_for_status()
            print(response.json()["sample_id"], response.json()["analysis"]["status"])
            time.sleep(1/a.speed)

if __name__ == "__main__":
    main()
