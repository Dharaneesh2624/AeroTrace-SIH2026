# Model card and architecture

Version 0.1; demonstration only. No maintenance, airworthiness or control authority.

```text
Pinned public CSV / canonical telemetry JSON
  -> SI units + timestamp validation + per-signal quality
  -> isolated engine/session/ECU stream + causal display filter
  -> physics identities  |  contextual regression residuals
  -> domain gate + held-out threshold + persistent event evidence
  -> transactional history + state API + CAD signal bindings

Offline: overlap-safe date split -> robust fitting -> calibration -> held-out audit
Separate: explicitly synthetic energy-balance bench scenarios
```

## Physics identities

Geometry inputs: bore 0.083 m, stroke 0.092 m, four cylinders, reduction 1.69.

- Displacement `Vd = pi*bore^2*stroke*cylinders/4 = 0.0019911037247 m3`.
- Crank speed `N = 1.69 * propeller_rpm`.
- Mean piston speed `2*stroke*N/60`, m/s.
- Four-stroke firing frequency `cylinders*N/120`, Hz. This is not measured vibration.
- Intake density `rho = manifold_absolute_pressure / (287.05*(intake_C+273.15))`.
- Air mass flow `rho*Vd*N*VE/120`, kg/s, with assumed `VE=0.85` and sensitivity range 0.65-1.0.
- Manifold/ambient pressure ratio and gauge boost are derived from two recorded pressures.

No crank-angle pressure trace, cylinder heat-release model, friction map, turbo map,
combustion kinetics or validated power model is inferred from these low-rate logs.
The CAD animation phase is an arbitrary integrated display phase. Sampling at 1 Hz
cannot recover crank phase, individual injection timing or combustion instability.

## Synthetic bench physics

Assume a constant brake efficiency eta and fuel heating value LHV:
`fuel_energy_rate = requested_power/eta`; synthetic fuel flow follows from LHV and density.

Two coupled energy balances:

`Cc*dTc/dt = fc*fuel_energy_rate - kc*cooling_factor*(Tc-Ta) - kco*(Tc-To)`

`Co*dTo/dt = fo*fuel_energy_rate - ko*cooling_factor*(To-Ta) + kco*(Tc-To)`

Boost uses a first-order lag toward an explicitly assumed pressure-ratio/power law.
Integration uses four 0.25-second substeps for each one-second output. Heat capacities,
heat fractions, conductances, fuel properties, efficiency and lag are illustrative,
not calibrated AE300 parameters. No altitude derating or flight cooling model is claimed.

## Statistical model

Idle and loaded models are fitted separately. Regime classification uses observed
speed, status flags and load with demonstration regime boundaries. Status decoding
is based on the upstream recording reference, not an independently certified decoder.

Each target uses `intercept + sum(beta_i*z_i) + sum(gamma_i*z_i^2)`. `z` is centred
and scaled using training rows only. Five iterations of Huber-like residual weighting
reduce the effect of isolated outliers in an unlabelled reference. Ridge regularization
stabilizes the fit. This is not a neural network, Isolation Forest or PINN.

Targets and conditioning inputs:

| Target | Conditioning inputs |
|---|---|
| Absolute boost | RPM, recorded load, ambient pressure, intake temperature |
| Oil pressure | RPM, load, oil temperature |
| Rail pressure | RPM, load, power lever |
| Fuel supply pressure | RPM, load |
| Battery voltage | RPM, load |
| Coolant/oil/gearbox temperature rates | Previous corresponding temperature, previous intake temperature, previous load/RPM |

Thermal-rate models are empirical local dynamics, not physics-constrained thermal
identification. Intake temperature is a covariate; it is not relabelled ambient temperature.

Signed residual scores use the training residual median and robust MAD scale with
explicit numerical floors. The regime anomaly score is maximum absolute residual z.
The threshold is the 99.5th percentile on separate calibration dates, at least 3.
The threshold is not an approved engine limit or an estimated failure probability.

Context outside observed training ranges plus a small margin causes abstention for
affected target models. All five core pressure/electrical targets are needed for a
composite score. Thermal residuals are optional and their availability is reported.
At least five successive valid candidate samples spanning four seconds are needed
for a persistent event. Gaps, missing core data and regime changes reset persistence.
This suppresses brief transients but may miss short real faults. A new model ID also
resets temporal state. Display EMA is not used to hide raw-input fault evidence.

`reference_alignment_index = 100/(1+score_ratio^2)` is a display metric only. It is
not a percent-health estimate, failure risk, confidence or safety clearance. Degradation
summaries use regime-specific session medians and a median pairwise slope over at
least three separate dates. Operating mix can explain a slope; RUL remains unavailable.

## Evaluation and failure modes

Independent train/calibration/test date groups; no random row split. Same-day and
overlapping intervals are grouped conservatively. Exact timestamp/value duplicates
are deweighted during fitting/calibration. Holding out dates does not prove engine-to-engine
generalization, especially with unverified source engine/ECU identities.

Unlabelled test anomaly fractions are not false-positive rates. Synthetic tests are
software-sensitivity demonstrations only. No thresholds are retuned on synthetic-test
outcomes. See the generated report, including the weaker thermal-ramp sensitivity.

Known limitations: low-rate aliasing, faulty reference contamination, decoder errors,
unobserved controls, constant-pressure regulation mistaken for normality, sensor bias
versus real fault ambiguity, unmodelled startup/cold transients, seasonal/engine/configuration
shift, absent flight airflow, limited thermal horizon and no confirmed fault labels.

## Promotion gate

Keep this model in research mode until measurements, engine configuration and units
are independently verified. Collect engineer-reviewed labels, validate on unseen
engines/dates, measure event sensitivity/delay and false alarms per hour, test robustness
to packet loss/drift, calibrate uncertainty and obtain the applicable engineering review.
Do not perform unattended online adaptation or infer maintenance actions from this model.
