# AeroTrace AE300 backend - research release 0.1

A working local backend for AE300 log analysis and a CAD-linked digital-twin
prototype. It does not command the engine, diagnose airworthiness, or provide a
validated remaining-life or reliability prediction.

## What is implemented

- Downloads the 15 public AustroView CSV examples at a pinned Git commit, with SHA-256 provenance.
- Strict channel/unit adapter: hPa and bar become Pa; temperature sentinels and bad values become `null` with quality reasons.
- Session/day-overlap grouping prevents chronological train/calibration/test leakage.
- Physics identities: crankshaft speed, piston speed, firing frequency, intake density, boost ratio, and assumed-VE airflow sensitivity.
- Separate two-node thermal energy-balance and boost-lag bench simulator. Constants are explicitly uncalibrated.
- Eight contextual regression residual models in idle and loaded regimes: five pressure/electrical channels and three one-step thermal rates.
- Held-out residual threshold calibration, operating-domain checks, causal filtering, five-sample/four-second alert persistence, and evidence-based fault alternatives.
- A descriptive reference-alignment index and session trend summaries. Neither is a calibrated health probability.
- Transactional SQLite history, independent engine/session/source state, duplicate handling, restart persistence, paginated replay/history.
- Local FastAPI API, optional API-key authentication, explicit live/replay timestamps and stale-state indication.
- R4 CAD node bindings, including multi-signal MOK. Unmeasured EGT/CHT/vibration remain unbound.
- Frozen JSON model artefact, automated tests, held-out audit and labelled synthetic-perturbation tests.

## Quick start on this computer

From `C:\aerotrace\backend`:

```powershell
.\.venv\Scripts\python.exe -m aerotrace.cli serve
```

Open **http://127.0.0.1:8000/docs** for the interactive API. The provided launcher
binds only to loopback, with one worker. Training and tests have already run locally.

For a portable/new environment (Python 3.11+):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe scripts/fetch_examples.py
.\.venv\Scripts\python.exe -m aerotrace.cli train
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m aerotrace.cli serve
```

The release ZIP includes the trained research model, but not raw third-party logs,
the Python environment, live database, or the large CAD geometry. The fetch command
downloads the pinned examples without executing upstream code.

## Replay a log

Offline causal analysis (JSON Lines):

```powershell
.\.venv\Scripts\python.exe -m aerotrace.cli replay data/public_examples/DataLog_20240819_session07_20240818_174831.csv --limit 300
```

With the API running, a second terminal can replay at 10x speed:

```powershell
.\.venv\Scripts\python.exe scripts/replay_to_api.py data/public_examples/DataLog_20240819_session07_20240818_174831.csv --session demo-replay --limit 120 --speed 10
```

Query `/v1/streams/public-example/demo-replay/ecu-unverified/state` for the most
recent stored state and 32 CAD bindings. This is historical replay, not live ECU
data. GET history uses an `after` sample-ID cursor; a frontend may poll it to animate
new samples. There is no frontend or WebSocket server in this release.

## API

| Route | Purpose |
|---|---|
| `GET /health` | Model readiness and authentication mode |
| `GET /v1/schema` | Canonical signal units |
| `GET /v1/model` | Model provenance and split metadata |
| `POST /v1/telemetry` | One canonical packet; score and persist atomically |
| `GET /v1/streams` | Up to 1,000 known streams |
| `GET /v1/streams/{engine}/{session}/{source}/state` | Latest state, freshness and CAD mapping |
| `GET /v1/streams/{engine}/{session}/{source}/history` | History/replay, `after` and `limit` |
| `POST /v1/simulate/bench` | Bounded synthetic thermal/boost scenario |
| `GET /v1/capabilities` | Implemented and unavailable capabilities |

Minimal packet (partial inputs are accepted but cause model abstention):

```json
{
  "engine_id": "bench-AE300", "session_id": "run-001", "source_id": "ecu-A",
  "timestamp": "2024-08-18T17:48:31Z", "mode": "replay",
  "values": {"propeller_rpm": 1500, "boost_pa": 180000, "ambient_pa": 101000}
}
```

Use `GET /v1/schema` for all 16 canonical keys. Unknown keys, NaN, infinities,
naive live timestamps and conflicting duplicates are rejected. Missing values are
never silently forward-filled into the model. Model histories are separate for
each engine/session/source; do not merge ECU A and B into one stream. Clock reversal
requires a distinct replay session. Repeating identical data is idempotent.

`mode=live` rejects packets older than 60 seconds or more than five seconds in the
future. Latest live state is marked stale after five seconds. This is an ingestion
interface, not a tested CAN connection. No messages are sent to an ECU.

## Model and data status

See `artifacts/VALIDATION_REPORT.md`, `evaluation.json`, `data_audit.json`,
`data_provenance.json`, `split.json` and `model.json`.

The public dataset has 45,006 rows across 15 files; overlapping files mean this is
not 45,006 independent operating seconds. Health labels and engine/ECU identity are
unverified. Training uses July 26, July 29 and August 1; calibration uses August 17;
test uses August 18-19, 2024. All dates in an overlap group stay together.

There is no supervised fault classifier. A fault alternative is an explanation to
investigate, not a confirmed failure. Synthetic injections are intentionally large
and do not establish real-world detection rates. Inference does not adapt its
baseline automatically, which avoids learning an emerging fault as normal.

## Physics and honest missing outputs

See `docs/MODEL_CARD.md` for equations and assumptions. Engine load is **not**
converted directly to shaft power. Real torque, fuel flow, efficiency, EGT and CHT
are returned unavailable when not measured. Volumetric efficiency is assumed;
its range is a sensitivity interval, not confidence bounds.

RUL and reliability always return `null` with an explanation. They need a defined
failure endpoint, labelled maintenance/run-to-failure histories and calibrated
uncertainty. The package does not fabricate a time-to-failure or mission-success
probability from one example aircraft's logs.

The bench simulator accepts **explicit assumed shaft power**, not throttle or a
mission plan. It is a synthetic educational model, not an AE300 flight-performance
map, calibrated combustion model, cooling-system design tool or operational test.

## Security and deployment

Local development only. If using an API key, set `AEROTRACE_API_KEY` in the shell
before startup and send it in `X-API-Key`. Do not publish this directly to a network.
Before deployment add TLS, reverse-proxy request/rate limits, user authentication,
authorization, retention/backups, monitoring and a reviewed secure telemetry adapter.
No arbitrary file/URL upload or executable model loading is exposed. The API loads
only a local configured JSON model at startup. Restart deliberately to activate a
new model; alert persistence resets when the model ID changes. SQLite is a local
prototype store, not fleet-scale infrastructure or a hard-real-time guarantee.

Paths may be overridden with `AEROTRACE_MODEL` and `AEROTRACE_DB`. The launcher
does not expose a non-loopback host option. Tests include duplicate concurrency;
high-volume soak, hardware-in-the-loop and production security audits remain undone.

## Recommended next inputs

1. Your own de-identified logs with engine configuration, ECU source and maintenance-confirmed events; reserve entire engines/dates for external validation.
2. Approved operating limits and a measured performance map before enabling operational threshold alarms or torque/fuel-efficiency estimates.
3. Synchronized CHT, EGT, measured fuel flow, alternator current and suitable high-rate vibration/injection data for the currently unobservable faults.

Sources and requirement coverage are in `docs/SOURCES_AND_COVERAGE.md`.
