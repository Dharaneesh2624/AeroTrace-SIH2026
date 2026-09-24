"""Causal per-stream monitoring. Never controls an engine."""
import math
from .model import score
from .physics import derived
from .schema import Record, regime, timestamp

HYPOTHESES = {
    "oil_pressure_pa": ["lubrication pressure deviation", "pressure-sensor bias", "temperature/map mismatch"],
    "boost_pa": ["air-path/control deviation", "pressure-sensor bias", "operating point not represented"],
    "rail_pressure_pa": ["fuel-rail regulation deviation", "sensor bias", "unobserved commanded-pressure change"],
    "fuel_pressure_pa": ["fuel supply pressure deviation", "sensor bias"],
    "battery_v": ["electrical bus voltage deviation", "load or regulator change", "voltage measurement bias"],
    "coolant_rate_c_s": ["cooling trend deviation", "sensor transient", "unobserved airflow change"],
    "oil_rate_c_s": ["oil thermal trend deviation", "sensor transient"],
    "gearbox_rate_c_s": ["gearbox thermal trend deviation", "sensor transient"],
}

def empty_state():
    return {"previous": None, "ema": {}, "candidate_start": None, "candidate_count": 0,
            "phase_deg": 0.0, "rows": 0}

def process(record, model, state=None):
    state = state or empty_state()
    if state.get("model_id") not in (None, model["model_id"]):
        state = empty_state()  # persistence from an older model cannot carry alerts forward
    state["model_id"] = model["model_id"]
    previous = None
    if state["previous"]:
        p = state["previous"]
        previous = Record(timestamp(p["time"]), record.session, record.engine, p["values"], p["quality"])
    dt = (record.time-previous.time).total_seconds() if previous else None
    if dt is not None and dt <= 0:
        raise ValueError("Records must increase in time within a stream")
    continuity = dt is not None and .5 <= dt <= 1.5
    if not continuity:
        state["ema"] = {}
        state["candidate_start"], state["candidate_count"] = None, 0
        previous = None
    alpha = 1-math.exp(-(dt or 1)/3)
    for name, value in record.values.items():
        if value is None:
            state["ema"].pop(name, None)  # never forward-fill missing channels as healthy
        elif name != "engine_status":
            old = state["ema"].get(name, value)
            state["ema"][name] = old+alpha*(value-old)
    analysis = score(model, record, previous)
    if previous and regime(previous.values) != regime(record.values):
        state["candidate_start"], state["candidate_count"] = None, 0
    if analysis["candidate_anomaly"]:
        if state["candidate_start"] is None:
            state["candidate_start"] = record.time.isoformat()
        state["candidate_count"] += 1
    else:
        state["candidate_start"], state["candidate_count"] = None, 0
    elapsed = ((record.time-timestamp(state["candidate_start"])).total_seconds()
               if state["candidate_start"] else 0)
    persistent = state["candidate_count"] >= 5 and elapsed >= 4
    faults = []
    if persistent:
        ranked = sorted(analysis["residuals"].items(), key=lambda x: abs(x[1]["signed_z"]), reverse=True)
        for name, evidence in ranked[:3]:
            if abs(evidence["signed_z"]) >= 3:
                faults.append({"signal": name, "kind": "anomaly_hypotheses_not_diagnosis",
                               "alternatives": HYPOTHESES[name], "evidence": evidence,
                               "confidence": None, "action": "Review source data and seek qualified engineering assessment; no automatic maintenance decision"})
    warnings = []
    bad = [name for name, q in record.quality.items() if q != "valid"]
    if bad:
        warnings.append({"type": "data_quality", "signals": bad})
    if dt is not None and not continuity:
        warnings.append({"type": "time_gap", "seconds": dt, "action": "Temporal state reset"})
    if analysis["status"] != "scored":
        warnings.append({"type": "model_abstention", "reason": analysis["status"]})
    # Non-combustion pressure consistency check; not an approved operational alarm.
    v = record.values
    if regime(v) == "stopped" and v.get("boost_pa") is not None and v.get("ambient_pa") is not None:
        if abs(v["boost_pa"]-v["ambient_pa"]) > 20000:
            warnings.append({"type": "stopped_pressure_inconsistency", "quality": "heuristic_review_only"})
    rpm = v.get("propeller_rpm")
    if previous and rpm is not None and previous.values.get("propeller_rpm") is not None:
        avg_rpm = (rpm+previous.values["propeller_rpm"])/2
        state["phase_deg"] = (state["phase_deg"] + avg_rpm*1.69*6*dt) % 720
    ratio = analysis.get("score_ratio")
    index = None if ratio is None else 100/(1+ratio*ratio)
    state["previous"] = {"time": record.time.isoformat(), "values": record.values, "quality": record.quality}
    state["rows"] += 1
    result = {"timestamp": record.time.isoformat(), "engine_id": record.engine, "session_id": record.session,
              "model_id": model["model_id"], "values": record.values, "quality": record.quality,
              "filtered_display_values": dict(state["ema"]), "physics": derived(record.values),
              "analysis": analysis, "persistent_anomaly": persistent, "hypotheses": faults,
              "warnings": warnings, "reference_alignment_index": index,
              "index_meaning": "0..100 model alignment only; NOT health certification or probability",
              "visual_crank_angle_deg": state["phase_deg"],
              "phase_quality": "arbitrary integrated display phase; 1 Hz cannot observe crank phase",
              "rul": {"status": "unavailable", "hours": None, "reason": "No run-to-failure histories, failure labels or validated degradation law"},
              "reliability": {"status": "unavailable", "probability": None},
              "scope": "research_only_not_airworthiness_or_control"}
    return result, state
