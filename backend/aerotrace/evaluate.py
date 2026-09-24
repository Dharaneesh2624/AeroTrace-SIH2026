"""Held-out audit and synthetic perturbation checks, not real fault accuracy."""
from collections import Counter
from dataclasses import replace
import statistics
import time
from .model import score
from .monitor import process, empty_state
from .schema import sanitize, regime

def evaluate(model, sessions):
    counts, timings, summaries = Counter(), [], []
    for session in sessions:
        state = empty_state()
        ratios = {"idle": [], "loaded": []}
        events = 0
        was_alert = False
        for record in session:
            begin = time.perf_counter()
            result, state = process(record, model, state)
            timings.append((time.perf_counter()-begin)*1000)
            analysis = result["analysis"]
            counts[analysis["status"]] += 1
            counts["rows"] += 1
            counts["candidate_anomaly_rows"] += int(analysis["candidate_anomaly"])
            counts["persistent_anomaly_rows"] += int(result["persistent_anomaly"])
            if result["persistent_anomaly"] and not was_alert:
                events += 1
            was_alert = result["persistent_anomaly"]
            if analysis["score_ratio"] is not None:
                ratios[analysis["regime"]].append(analysis["score_ratio"])
        summaries.append({"session": session[0].session, "date": session[0].time.date().isoformat(),
                          "rows": len(session), "persistent_events": events,
                          "median_score_by_regime": {s: statistics.median(v) if v else None for s, v in ratios.items()}})
    counts = dict(counts)
    counts["coverage_fraction"] = counts.get("scored", 0)/counts["rows"]
    counts["unlabelled_candidate_fraction_of_scored"] = counts["candidate_anomaly_rows"]/max(1, counts.get("scored", 0))
    return {"held_out": counts, "sessions": summaries,
            "inference_latency_ms": {"median": statistics.median(timings), "p95": sorted(timings)[int(.95*(len(timings)-1))]},
            "interpretation": "Unlabelled example sessions: anomaly fraction is NOT false-positive rate; no real precision/recall can be estimated",
            "synthetic_tests": synthetic_checks(model, sessions)}

def synthetic_checks(model, sessions):
    # Choose baseline-supported windows without using injected outcomes for selection.
    windows = []
    for session in sessions:
        for start in range(30, len(session)-30, 90):
            window = session[start:start+30]
            scores = [score(model, row, window[i-1] if i else None) for i, row in enumerate(window)]
            if all(s["status"] == "scored" and s["score_ratio"] < .8 and s["regime"] == "loaded" for s in scores):
                windows.append(window)
            if len(windows) >= 20:
                break
        if len(windows) >= 20:
            break
    specs = {"oil_pressure_drop_70pct": ("oil_pressure_pa", "multiply", .3),
             "boost_drop_45pct": ("boost_pa", "multiply", .55),
             "rail_drop_50pct": ("rail_pressure_pa", "multiply", .5),
             "bus_voltage_drop_8V": ("battery_v", "add", -8),
             "coolant_ramp_2C_per_s": ("coolant_c", "ramp", 2),
             "oil_sensor_dropout": ("oil_c", "missing", None)}
    output = {}
    for label, (channel, action, amount) in specs.items():
        detected, delays, quality_detected = 0, [], 0
        for window in windows:
            state = empty_state()
            found = quality_found = False
            for i, original in enumerate(window):
                values = dict(original.values)
                if i >= 10:
                    if action == "multiply": values[channel] *= amount
                    elif action == "add": values[channel] += amount
                    elif action == "ramp": values[channel] += (i-9)*amount
                    else: values[channel] = None
                values, quality = sanitize(values)
                result, state = process(replace(original, values=values, quality=quality), model, state)
                if i >= 10 and result["persistent_anomaly"] and not found:
                    found = True
                    delays.append(i-10)
                if i >= 10 and quality[channel] != "valid": quality_found = True
            detected += int(found)
            quality_detected += int(quality_found)
        output[label] = {"windows": len(windows), "persistent_anomaly_detections": detected,
                         "data_quality_detections": quality_detected,
                         "median_delay_s": statistics.median(delays) if delays else None,
                         "nature": "synthetic perturbation; not proof of real fault sensitivity"}
    return output

