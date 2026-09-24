from datetime import datetime, timezone
import pytest
from aerotrace.schema import Record, sanitize

@pytest.fixture
def values():
    return {"boost_pa": 180000, "ambient_pa": 101000, "propeller_rpm": 1500,
            "oil_pressure_pa": 400000, "rail_pressure_pa": 80000000, "power_lever_pct": 50,
            "coolant_c": 80, "intake_c": 40, "battery_v": 28, "fuel_pressure_pa": 400000,
            "gearbox_oil_c": 70, "oil_c": 85, "prop_duty_pct": 10, "engine_status": 12,
            "oil_level_mm": 30, "engine_load_pct": 50}

@pytest.fixture
def record(values):
    v, q = sanitize(values)
    return Record(datetime(2024, 8, 18, tzinfo=timezone.utc), "session", "engine", v, q)

@pytest.fixture
def model(values):
    models = {}
    floors = {"boost_pa": 1500, "oil_pressure_pa": 15000, "rail_pressure_pa": 2e6, "fuel_pressure_pa": 12000, "battery_v": .15}
    for target, floor in floors.items():
        models[target] = {"features": ["propeller_rpm"], "center": [1500], "spread": [500],
                          "coefficients": [values[target], 0, 0], "residual_center": 0,
                          "residual_scale": floor, "lower": [500], "upper": [2500]}
    return {"schema_version": 1, "model_id": "test-model", "regimes": {"loaded": {"models": models, "threshold": 4}},
            "algorithm": "test fixture", "training_health": "synthetic", "scope": "tests", "split": {}}

