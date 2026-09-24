"""Map signal values to R4 nodes without inventing independently measured sensors."""
import json
from pathlib import Path
from .schema import CHANNELS

def bindings(result, path):
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    channels = {c[0]: c[2] for c in CHANNELS}
    mapped = []
    for sensor in registry:
        channel = sensor.get("telemetry_channel")
        ids = [int(c) for c in channel.split("/")] if isinstance(channel, str) else [channel] if channel is not None else []
        readings = []
        for cid in ids:
            signal = channels.get(cid)
            if signal:
                readings.append({"canonical_signal": signal, "value": result["values"].get(signal),
                                 "unit": next(c[3] for c in CHANNELS if c[2] == signal),
                                 "quality": result["quality"].get(signal, "unavailable")})
        name = channels.get(channel) if not isinstance(channel, str) else None
        value = result["values"].get(name) if name else None
        mapped.append({"sensor_id": sensor["id"], "object": sensor["object"], "canonical_signal": name,
            "readings": readings,
            "value": value, "unit": next((c[3] for c in CHANNELS if c[2] == name), None),
            "quality": result["quality"].get(name, "unavailable") if name else "unavailable",
            "source_scope": "shared recorded ECU channel; not independent redundant sensor readings" if readings else "not measured by base log"})
    return {"bindings": mapped, "visual_crank_angle_deg": result["visual_crank_angle_deg"],
            "phase_quality": result["phase_quality"], "coordinate_system": "CAD mm; GLB meters"}
