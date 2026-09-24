import csv
from dataclasses import replace
from datetime import timedelta
import math
import pytest
from aerotrace.schema import CHANNELS, sanitize, timestamp, regime
from aerotrace.ingest import read_session, split_sessions
from aerotrace.physics import derived, EngineParameters, simulate_bench

def test_si_conversion(tmp_path):
    p = tmp_path/"demo.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Timestamp"]+[c[1] for c in CHANNELS])
        w.writerow(["2024-01-01 00:00:00", 1800, 1013, 2300, 4000, 800, 50, 80, 40, 28, 4000, 70, -273.1, 10, 12, 30, 50])
    rows, audit = read_session(p)
    assert rows[0].values["boost_pa"] == 180000
    assert rows[0].values["rail_pressure_pa"] == 80000000
    assert rows[0].values["oil_c"] is None
    assert rows[0].quality["oil_c"] == "sensor_initialization_sentinel"
    assert audit["issues"]["sensor_initialization_sentinel"] == 1

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1])
def test_bad_rpm(value):
    v, q = sanitize({"propeller_rpm": value})
    assert v["propeller_rpm"] is None
    assert q["propeller_rpm"] != "valid"

def test_unknown_signal():
    with pytest.raises(ValueError): sanitize({"rpm_maybe": 2})

def test_clock():
    with pytest.raises(ValueError): timestamp("2024-01-01T00:00:00")
    with pytest.raises(ValueError): timestamp("2049-01-01T00:00:00Z")
    assert timestamp("2024-01-01T05:30:00+05:30").hour == 0

def test_overlap_split(record):
    sessions = []
    for i, day in enumerate([0, 0, 1, 2, 3]):
        r = replace(record, time=record.time+timedelta(days=day, seconds=i), session=str(i))
        sessions.append([r, replace(r, time=r.time+timedelta(seconds=50))])
    split, manifest = split_sessions(sessions)
    membership = {s[0].session: k for k, ss in split.items() for s in ss}
    assert membership["0"] == membership["1"]
    assert max(s[-1].time for s in split["train"]) < min(s[0].time for s in split["calibration"])
    with pytest.raises(ValueError): split_sessions(sessions[:2])

def test_physics(values):
    p = EngineParameters()
    assert p.displacement_m3*1e6 == pytest.approx(1991.103724733, rel=1e-10)
    values["propeller_rpm"] = 2300
    d = derived(values)
    assert d["crankshaft_rpm"]["value"] == 3887
    assert d["airflow_kg_s"]["value"] > 0
    assert d["shaft_power_kw"]["value"] is None
    values["propeller_rpm"] = 0
    assert derived(values)["airflow_kg_s"]["value"] == 0

def test_no_invented_values():
    d = derived({})
    assert "airflow_kg_s" not in d
    assert d["fuel_flow_l_h"]["value"] is None

def test_bench_zero_power():
    r = simulate_bench([{"duration_s": 300, "shaft_power_kw": 0}], initial_c=25)
    assert r["samples"][-1]["coolant_c"] == 25
    assert r["samples"][-1]["synthetic_fuel_flow_l_h"] == 0

def test_bench_heat_and_bound():
    r = simulate_bench([{"duration_s": 300, "shaft_power_kw": 60}])
    assert 25 < r["samples"][-1]["coolant_c"] < 120
    assert all(math.isfinite(x["oil_c"]) for x in r["samples"])
    with pytest.raises(ValueError): simulate_bench([{"duration_s": 300, "shaft_power_kw": 500}])
