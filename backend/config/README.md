# CAD signal registry

`cad_sensor_map.json` is copied from the locally developed AE300 R4 CAD package.
It supplies names and channel bindings, not certified sensor locations or CAN IDs.
The server converts all readings to its canonical units (Pa, rpm, degC, V, mm, %).
MOK carries oil temperature and oil level as separate `readings`.
Redundant bodies sharing a channel are visual bindings, not two independent measurements.

No approved aircraft operating thresholds, OEM power/torque maps or wiring pinouts
are supplied. Broad ingestion bounds are only input plausibility checks.
