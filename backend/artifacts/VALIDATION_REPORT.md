# AE300 backend validation report

Model: `48333087f1b59604`

Input: 15 sessions / 45,006 rows.
Labels: unavailable. Reference health: unverified. No supervised fault classifier or validated RUL model.

## Held-out results

```json
{
  "unmodelled_regime": 1028,
  "rows": 14979,
  "candidate_anomaly_rows": 115,
  "persistent_anomaly_rows": 12,
  "scored": 13951,
  "coverage_fraction": 0.9313705854863475,
  "unlabelled_candidate_fraction_of_scored": 0.0082431366927102
}
```

These are unlabelled anomaly counts, not false positives or fault accuracy.

## Synthetic perturbation checks

| Perturbation | Windows | Persistent detection | Data quality detection | Median delay, s |
|---|---:|---:|---:|---:|
| oil_pressure_drop_70pct | 20 | 20 | 0 | 4.0 |
| boost_drop_45pct | 20 | 20 | 0 | 4.0 |
| rail_drop_50pct | 20 | 20 | 0 | 4.0 |
| bus_voltage_drop_8V | 20 | 20 | 0 | 4.0 |
| coolant_ramp_2C_per_s | 20 | 11 | 0 | 4 |
| oil_sensor_dropout | 20 | 0 | 20 | None |

Perturbations are deliberately large synthetic demonstrations, not naturally occurring labelled failures.
Missing temperature data can invalidate the oil-pressure model: dropout must produce abstention, not a healthy score.

## Limits

- Day grouping keeps overlapping recordings out of different splits. Original engine/ECU identities are unverified.
- Only two held-out calendar days; not a fleet or independent-engine validation.
- Empirical thermal models predict one-step temperature change, not absolute combustion temperature.
- No calibrated failure probability, remaining life, mission reliability or airworthiness assessment.
- Model is frozen after training; inference never updates its baseline.

Inference timings (in-process only, excluding database/network): `{"median": 0.0638999999864609, "p95": 0.09409999984200113}`.