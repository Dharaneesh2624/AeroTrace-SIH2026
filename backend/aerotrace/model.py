"""Robust contextual regression and calibrated residual novelty detection.

No labelled failure classifier is claimed. Models are JSON, not executable pickle.
All feature scaling is train-only; thresholds use a disjoint calibration group.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from .schema import regime

SPECS = {
    "boost_pa": (["propeller_rpm", "engine_load_pct", "ambient_pa", "intake_c"], 1500.0),
    "oil_pressure_pa": (["propeller_rpm", "engine_load_pct", "oil_c"], 15000.0),
    "rail_pressure_pa": (["propeller_rpm", "engine_load_pct", "power_lever_pct"], 2e6),
    "fuel_pressure_pa": (["propeller_rpm", "engine_load_pct"], 12000.0),
    "battery_v": (["propeller_rpm", "engine_load_pct"], .15),
    "coolant_rate_c_s": (["previous_coolant_c", "previous_intake_c", "previous_engine_load_pct", "previous_propeller_rpm"], .03),
    "oil_rate_c_s": (["previous_oil_c", "previous_intake_c", "previous_engine_load_pct", "previous_propeller_rpm"], .03),
    "gearbox_rate_c_s": (["previous_gearbox_oil_c", "previous_intake_c", "previous_engine_load_pct", "previous_propeller_rpm"], .03),
}

def contextual(record, previous=None):
    values = dict(record.values)
    if previous is not None and previous.session == record.session and previous.engine == record.engine:
        dt = (record.time-previous.time).total_seconds()
        if .5 <= dt <= 1.5 and regime(previous.values) == regime(values):
            for key, value in previous.values.items():
                values["previous_"+key] = value
            for target, source in [("coolant_rate_c_s", "coolant_c"), ("oil_rate_c_s", "oil_c"), ("gearbox_rate_c_s", "gearbox_oil_c")]:
                before, now = previous.values.get(source), values.get(source)
                if before is not None and now is not None:
                    values[target] = (now-before)/dt
    return values

def _basis(x):
    return np.column_stack((np.ones(len(x)), x, x*x))

def _fit(x, y, floor):
    center = np.median(x, axis=0)
    spread = np.maximum(np.std(x, axis=0), 1e-6)
    a = _basis((x-center)/spread)
    weights = np.ones(len(y))
    penalty = np.eye(a.shape[1])*.5
    penalty[0, 0] = 1e-9
    for _ in range(5):
        coeff = np.linalg.solve(a.T@(weights[:, None]*a)+penalty, a.T@(weights*y))
        error = y-a@coeff
        med = np.median(error)
        scale = max(floor, float(1.4826*np.median(np.abs(error-med))))
        weights = np.minimum(1, 1.5*scale/np.maximum(np.abs(error-med), 1e-9))
    bias = float(np.median(y-a@coeff))
    return {"center": center.tolist(), "spread": spread.tolist(), "coefficients": coeff.tolist(),
            "residual_center": bias, "residual_scale": scale,
            "lower": np.min(x, axis=0).tolist(), "upper": np.max(x, axis=0).tolist()}

def _predict(spec, x):
    x = np.asarray(x, dtype=float)
    z = (x-np.asarray(spec["center"]))/np.asarray(spec["spread"])
    return float(np.dot(np.concatenate(([1.0], z, z*z)), spec["coefficients"])) + spec["residual_center"]

def _domain(spec, x):
    # Conservative support gate. Do not silently extrapolate a learned engine map.
    for value, low, high, spread in zip(x, spec["lower"], spec["upper"], spec["spread"]):
        margin = max((high-low)*.15, spread*.25, 1e-5)
        if value < low-margin or value > high+margin:
            return False
    return True

def _observations(sessions):
    seen = set()
    for session in sessions:
        previous = None
        for record in session:
            values = contextual(record, previous)
            previous = record
            # Identical recordings must not multiply training weight.
            key = (record.time, tuple(sorted(record.values.items())))
            if key in seen:
                continue
            seen.add(key)
            yield record, values

def train(train_sessions, calibration_sessions, manifest):
    if not train_sessions or not calibration_sessions:
        raise ValueError("Training and calibration sessions are required")
    if max(s[-1].time.date() for s in train_sessions) >= min(s[0].time.date() for s in calibration_sessions):
        raise ValueError("Training and calibration must be chronological disjoint day groups")
    model = {"schema_version": 1, "algorithm": "Huber-weighted quadratic ridge + held-out residual threshold",
             "training_health": "unlabelled; NOT confirmed healthy", "regimes": {}, "split": manifest,
             "scope": "public single-source demonstration; no fault probabilities or RUL"}
    obs = list(_observations(train_sessions))
    cal = list(_observations(calibration_sessions))
    for state in ("idle", "loaded"):
        specs = {}
        for target, (features, floor) in SPECS.items():
            samples = [(v, v[target]) for r, v in obs if regime(r.values) == state
                       and v.get(target) is not None and all(v.get(f) is not None for f in features)]
            if len(samples) < 120:
                continue
            x = np.array([[v[f] for f in features] for v, _ in samples])
            y = np.array([y for _, y in samples])
            fitted = _fit(x, y, floor)
            fitted.update({"features": features, "train_rows": len(samples)})
            specs[target] = fitted
        if len(specs) < 4:
            continue
        candidate = {"models": specs, "threshold": 1.0}
        scores = []
        for r, values in cal:
            if regime(r.values) != state:
                continue
            scored = _score(candidate, values)
            if scored["status"] == "scored":
                scores.append(scored["raw_score"])
        if len(scores) < 60:
            continue
        candidate["threshold"] = max(3.0, float(np.quantile(scores, .995)))
        candidate["calibration_rows"] = len(scores)
        candidate["calibration_quantile"] = .995
        model["regimes"][state] = candidate
    if not model["regimes"]:
        raise ValueError("Insufficient train/calibration support; no model published")
    model["model_id"] = hashlib.sha256(json.dumps(model, sort_keys=True).encode()).hexdigest()[:16]
    return model

def _score(state_model, values):
    details, unsupported, missing = {}, [], []
    for target, spec in state_model["models"].items():
        if values.get(target) is None or any(values.get(f) is None for f in spec["features"]):
            missing.append(target)
            continue
        x = [values[f] for f in spec["features"]]
        if not _domain(spec, x):
            unsupported.append(target)
            continue
        expected = _predict(spec, x)
        residual = values[target]-expected
        details[target] = {"observed": values[target], "expected": expected, "residual": residual,
                           "signed_z": residual/spec["residual_scale"]}
    # Missing core measurements invalidate the composite, not necessarily other per-channel results.
    core = {"boost_pa", "oil_pressure_pa", "rail_pressure_pa", "fuel_pressure_pa", "battery_v"}
    status = "scored" if core <= set(details) else "out_of_domain" if unsupported else "insufficient_data"
    raw = max((abs(d["signed_z"]) for d in details.values()), default=None)
    ratio = raw/state_model["threshold"] if raw is not None and status == "scored" else None
    return {"status": status, "raw_score": raw, "threshold": state_model["threshold"],
            "score_ratio": ratio, "candidate_anomaly": ratio is not None and ratio > 1,
            "residuals": details, "unsupported_targets": unsupported, "missing_targets": missing,
            "interpretation": "Statistical novelty relative to unlabelled reference, not a failure probability"}

def score(model, record, previous=None):
    state = regime(record.values)
    if state not in model["regimes"]:
        return {"status": "unmodelled_regime", "regime": state, "score_ratio": None,
                "candidate_anomaly": False, "residuals": {}}
    return dict(_score(model["regimes"][state], contextual(record, previous)), regime=state)

def save(model, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(model, indent=2, allow_nan=False), encoding="utf-8")

def load(path):
    model = json.loads(Path(path).read_text(encoding="utf-8"))
    if model.get("schema_version") != 1:
        raise ValueError("Unsupported model schema")
    for state in model["regimes"].values():
        if not math.isfinite(state["threshold"]) or state["threshold"] <= 0:
            raise ValueError("Invalid model threshold")
        for spec in state["models"].values():
            n = len(spec["features"])
            if any(len(spec[k]) != n for k in ("center", "spread", "lower", "upper")) or len(spec["coefficients"]) != 1+2*n:
                raise ValueError("Malformed model dimensions")
            if not set(spec["features"]) <= {f for fs, _ in SPECS.values() for f in fs}:
                raise ValueError("Unknown model features")
            if not all(math.isfinite(x) for key in ("center", "spread", "coefficients", "lower", "upper") for x in spec[key]):
                raise ValueError("Non-finite model parameter")
            if any(x <= 0 for x in spec["spread"]) or not math.isfinite(spec["residual_scale"]) or spec["residual_scale"] <= 0:
                raise ValueError("Invalid model scaling")
            if not math.isfinite(spec["residual_center"]):
                raise ValueError("Invalid residual center")
    return model
