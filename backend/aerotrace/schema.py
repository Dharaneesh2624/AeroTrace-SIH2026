"""Explicit units and plausibility bounds, NOT approved operating limits."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math

# channel ID, CSV header, canonical name, unit, broad physical/data bounds
CHANNELS = [
    (800, "Boost Pressure [hPa]", "boost_pa", "Pa", 1000, 600000),
    (801, "Ambient Air Pressure [hPa]", "ambient_pa", "Pa", 1000, 150000),
    (802, "Propeller Speed [rpm]", "propeller_rpm", "rpm", 0, 4000),
    (803, "Engine Oil Pressure [hPa]", "oil_pressure_pa", "Pa", 0, 1500000),
    (804, "Rail Pressure [bar]", "rail_pressure_pa", "Pa", 0, 250000000),
    (805, "Power Lever Position [%]", "power_lever_pct", "%", 0, 105),
    (806, "Coolant Temperature [deg C]", "coolant_c", "degC", -80, 200),
    (807, "Intake Air Temperature [deg C]", "intake_c", "degC", -80, 200),
    (808, "Battery Voltage [V]", "battery_v", "V", 0, 60),
    (809, "Fuel Pressure [hPa]", "fuel_pressure_pa", "Pa", 0, 1500000),
    (810, "Gearbox Oil Temperature [deg C]", "gearbox_oil_c", "degC", -80, 200),
    (811, "Engine Oil Temperature [deg C]", "oil_c", "degC", -80, 200),
    (812, "Prop Actuator Duty Cycle [%]", "prop_duty_pct", "%", -105, 105),
    (813, "Engine Status [bin]", "engine_status", "bitmask", 0, 65535),
    (814, "Engine Oil Level [mm]", "oil_level_mm", "mm", 0, 200),
    (815, "Engine Load [%]", "engine_load_pct", "%", 0, 105),
]
BY_NAME = {c[2]: c for c in CHANNELS}
UNITS = {c[2]: c[3] for c in CHANNELS}

def timestamp(value: str, *, csv_utc=False) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        if not csv_utc:
            raise ValueError("Live timestamps require an explicit UTC offset")
        dt = dt.replace(tzinfo=timezone.utc)  # upstream README declares UTC
    dt = dt.astimezone(timezone.utc)
    if not 2000 <= dt.year <= 2040:
        raise ValueError("Unsupported clock year (including decoder 2049 fallback)")
    return dt

def sanitize(values: dict) -> tuple[dict, dict]:
    unknown = set(values) - set(BY_NAME)
    if unknown:
        raise ValueError(f"Unknown canonical signals: {sorted(unknown)}")
    clean, quality = {}, {}
    for name, (_, _, _, _, low, high) in BY_NAME.items():
        raw = values.get(name)
        if raw is None or raw == "":
            clean[name], quality[name] = None, "missing"
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            clean[name], quality[name] = None, "not_numeric"
            continue
        if not math.isfinite(value):
            reason = "not_finite"
        elif name.endswith("_c") and value <= -270:
            reason = "sensor_initialization_sentinel"
        elif not low <= value <= high:
            reason = "outside_plausibility_bounds"
        elif name == "engine_status" and value != int(value):
            reason = "noninteger_bitmask"
        else:
            clean[name], quality[name] = value, "valid"
            continue
        clean[name], quality[name] = None, reason
    return clean, quality

@dataclass
class Record:
    time: datetime
    session: str
    engine: str
    values: dict
    quality: dict = field(default_factory=dict)

def regime(values: dict) -> str:
    rpm = values.get("propeller_rpm")
    flags = values.get("engine_status")
    if rpm is None or flags is None:
        return "unknown"
    flags = int(flags)
    if rpm < 100:
        return "stopped"
    if flags & 2:
        return "starting"
    if flags & 1:
        return "afterrun"
    if not flags & 4:
        return "unknown"
    load = values.get("engine_load_pct")
    if load is None:
        return "unknown"
    return "idle" if load < 20 else "loaded"

