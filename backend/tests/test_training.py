from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import pytest
from aerotrace.ingest import load_directory, split_sessions
from aerotrace.model import train, score, load, save
from aerotrace.trends import trend_summary

def test_training_rejects_overlap(record):
    with pytest.raises(ValueError, match="disjoint"):
        train([[record]], [[replace(record, time=record.time+timedelta(seconds=1))]], {})

def test_reject_bad_model_scaling(tmp_path, model):
    p = tmp_path/"model.json"
    model["regimes"]["loaded"]["models"]["battery_v"]["spread"] = [0]
    save(model, p)
    with pytest.raises(ValueError, match="scaling"): load(p)

def test_trends_abstain_and_no_rul():
    sessions = [{"date": "2024-01-01", "median_score_by_regime": {"idle": .1, "loaded": .2}}]*10
    assert trend_summary(sessions)["regimes"]["loaded"]["status"] == "insufficient_history"
    sessions += [{"date": f"2024-01-0{i}", "median_score_by_regime": {"idle": .1, "loaded": .2*i}} for i in (2, 3)]
    result = trend_summary(sessions)
    assert result["regimes"]["loaded"]["slope_per_day"] == pytest.approx(.2)
    assert result["rul_hours"] is None

def test_real_data_training_and_split_if_available():
    root = Path(__file__).resolve().parents[1]
    data = root/"data/public_examples"
    if not list(data.glob("*.csv")):
        pytest.skip("Run scripts/fetch_examples.py for integration dataset")
    sessions, audits = load_directory(data)
    split, manifest = split_sessions(sessions)
    model = train(split["train"], split["calibration"], manifest)
    assert set(model["regimes"]) == {"idle", "loaded"}
    assert sum(len(s) for s in sessions) == 45006
    assert max(s[-1].time for s in split["train"]) < min(s[0].time for s in split["calibration"])
    assert max(s[-1].time for s in split["calibration"]) < min(s[0].time for s in split["test"])
    before = json.dumps(model, sort_keys=True)
    for record in split["test"][0][:100]: score(model, record)
    assert json.dumps(model, sort_keys=True) == before
