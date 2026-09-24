from dataclasses import replace
from datetime import timedelta
import json
import numpy as np
import pytest
from aerotrace.model import _fit, _predict, score, contextual, save, load
from aerotrace.monitor import process, empty_state
from aerotrace.schema import sanitize

def changed(record, **kwargs):
    v, q = sanitize(dict(record.values, **kwargs))
    return replace(record, values=v, quality=q)

def test_robust_fit():
    x = np.linspace(0, 10, 1000)[:, None]
    y = 4+2*x[:, 0]
    y[::100] += 1000
    fit = _fit(x, y, .1)
    assert _predict(fit, [5]) == pytest.approx(14, abs=.1)

def test_model_roundtrip(tmp_path, model, record):
    p = tmp_path/"model.json"
    save(model, p)
    assert score(load(p), record) == score(model, record)

def test_no_fitting_during_inference(model, record):
    before = json.dumps(model, sort_keys=True)
    for _ in range(10): score(model, record)
    assert json.dumps(model, sort_keys=True) == before

def test_persistence_and_dropout(model, record):
    state = empty_state()
    fault = changed(record, battery_v=18)
    for i in range(5):
        result, state = process(replace(fault, time=fault.time+timedelta(seconds=i)), model, state)
        assert result["persistent_anomaly"] == (i == 4)
    assert result["hypotheses"][0]["signal"] == "battery_v"
    dropout = changed(record, oil_pressure_pa=None)
    result, state = process(replace(dropout, time=record.time+timedelta(seconds=5)), model, state)
    assert not result["persistent_anomaly"]
    assert result["reference_alignment_index"] is None
    assert "oil_pressure_pa" not in result["filtered_display_values"]

def test_gap_resets_persistence(model, record):
    fault = changed(record, battery_v=18)
    state = empty_state()
    for sec in [0, 1, 2, 3, 20]:
        result, state = process(replace(fault, time=fault.time+timedelta(seconds=sec)), model, state)
    assert not result["persistent_anomaly"]
    assert any(w["type"] == "time_gap" for w in result["warnings"])

def test_unknown_regime_and_ood(model, record):
    assert score(model, changed(record, engine_status=None))["status"] == "unmodelled_regime"
    assert score(model, changed(record, propeller_rpm=3800))["status"] == "out_of_domain"

def test_causal_rates_do_not_cross_gap(record):
    new = replace(changed(record, coolant_c=81), time=record.time+timedelta(seconds=1))
    assert contextual(new, record)["coolant_rate_c_s"] == 1
    assert "coolant_rate_c_s" not in contextual(replace(new, time=record.time+timedelta(seconds=3)), record)
    assert "coolant_rate_c_s" not in contextual(replace(new, session="different"), record)

def test_phase_is_only_visual(model, record):
    result, state = process(record, model)
    result, state = process(replace(record, time=record.time+timedelta(seconds=1)), model, state)
    assert 0 <= result["visual_crank_angle_deg"] < 720
    assert result["rul"]["hours"] is None
    assert "arbitrary" in result["phase_quality"]

def test_new_model_resets_state(model, record):
    fault = changed(record, battery_v=18)
    state = empty_state()
    for i in range(4):
        _, state = process(replace(fault, time=fault.time+timedelta(seconds=i)), model, state)
    replacement = dict(model, model_id="replacement")
    result, state = process(replace(fault, time=fault.time+timedelta(seconds=4)), replacement, state)
    assert not result["persistent_anomaly"]
    assert state["candidate_count"] == 1

