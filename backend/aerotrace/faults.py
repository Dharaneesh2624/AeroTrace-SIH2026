"""Deterministic signal-level fault experiments, not validated failure dynamics."""
from .schema import Record, sanitize

CATALOG = {
    'voltage_drop': {'label': 'Bus voltage drop', 'signal': 'battery_v', 'effect': 'Subtract up to 12 V; floor at zero.'},
    'boost_loss': {'label': 'Boost pressure loss', 'signal': 'boost_pa', 'effect': 'Remove up to 90% of pressure above ambient; ambient is required.'},
    'oil_pressure_loss': {'label': 'Oil pressure loss', 'signal': 'oil_pressure_pa', 'effect': 'Reduce oil pressure by up to 95%.'},
    'coolant_rise': {'label': 'Coolant temperature rise', 'signal': 'coolant_c', 'effect': 'Ramp temperature upward by up to 40 degrees C; not a heat-transfer failure solver.'},
    'oil_sensor_dropout': {'label': 'Oil temperature sensor dropout', 'signal': 'oil_c', 'effect': 'Remove oil-temperature readings; severity is not applicable.'},
    'coast_down': {'label': 'Commanded coast-down demo', 'signal': 'propeller_rpm', 'effect': 'Ramp RPM down by the severity fraction. At 100%, RPM reaches zero. Other channels are unchanged; this is not a coupled stall model.'},
}

def inject(records, kind, start, duration, severity):
    if kind not in CATALOG or not 0 < severity <= 1:
        raise ValueError('Unknown fault or severity outside (0, 1]')
    if start < 0 or duration < 2 or start + duration > len(records):
        raise ValueError('Fault interval must fit the source session and contain at least two samples')
    signal = CATALOG[kind]['signal']
    output, provenance = [], []
    changed = 0
    for index, original in enumerate(records):
        values = dict(original.values)
        active = start <= index < start + duration
        before = values.get(signal)
        if active and before is not None:
            ramp = (index - start) / (duration - 1)
            if kind == 'voltage_drop': values[signal] = max(0, before - 12 * severity)
            elif kind == 'boost_loss':
                ambient = values.get('ambient_pa')
                if ambient is not None: values[signal] = before - max(0, before - ambient) * .9 * severity
            elif kind == 'oil_pressure_loss': values[signal] = before * (1 - .95 * severity)
            elif kind == 'coolant_rise': values[signal] = before + 40 * severity * ramp
            elif kind == 'oil_sensor_dropout': values[signal] = None
            elif kind == 'coast_down': values[signal] = before * (1 - severity * ramp)
        clean, quality = sanitize(values)
        # Keep original reasons for unchanged invalid/missing measurements.
        for key in quality:
            if values.get(key) == original.values.get(key):
                quality[key] = original.quality.get(key, quality[key])
        altered = active and values.get(signal) != before
        changed += int(altered)
        output.append(Record(original.time, original.session, original.engine, clean, quality))
        provenance.append({'kind': kind, 'active': active, 'changed': altered,
                           'signal': signal, 'original_value': before,
                           'injected_value': clean.get(signal), 'requested_value': values.get(signal)})
    if not changed:
        raise ValueError('No usable readings were changed in this interval; choose another source or interval')
    return output, provenance
