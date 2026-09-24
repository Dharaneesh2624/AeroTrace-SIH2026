# Sources and requirement coverage

## Sources inspected

- User's `DRDO REQUIREMENT (1).pdf`: used as supplied project scope, not independently verified as an official current SIH notice. It calls for telemetry, physics, analytics, replay and prognostics; it does not supply training labels or calibrated maps.
- [AustroView repository](https://github.com/ingramleedy/AustroView), pinned commit `f9187ca3cd9094c5b547a8186559f5e099976c6d`. The source/README define 16 base recording channels, one-second records and CSV units. The 15 examples are real public logs according to that project, not the user's own engine data. Its decoder and outputs are community-developed and not manufacturer approved. Base recording IDs 800-815 are not live CAN arbitration IDs. LiveView parsing is not supplied by this backend.
- [Manufacturer E4 factsheet](https://www.diamondaircraft.com/fileadmin/diamondaircraft/products/austro-engine/AE_E4_Series_Factsheet_screen.pdf): reference power/engine architecture. The nominal rated power is used only in the clearly synthetic bench example.
- Local R4 parameter registry and inspected engine manuals provide bore/stroke/cylinder count and reduction. CAD coordinates are reconstructed and are not certified installation locations.
- [NASA ideal-gas equation of state](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/equation-of-state/): ideal-gas density relationship, not AE300-specific calibration.
- [scikit-learn novelty/outlier documentation](https://scikit-learn.org/stable/modules/outlier_detection.html): conceptual distinction between unlabelled outlier analysis and clean-reference novelty. This backend implements its own small NumPy residual model; it does not depend on scikit-learn.
- [FastAPI testing documentation](https://fastapi.tiangolo.com/tutorial/testing/): HTTP test approach.

Public CSV source hashes/URLs are in `artifacts/data_provenance.json`. Downloaded
logs remain in local `data/public_examples`; the release ZIP does not redistribute
them. No upstream decoder source code is vendored or automatically executed. For new
`.ae3` files, first export approved CSVs or run a separately reviewed AustroView install.
Raw `.ae3` decoding and hardware acquisition are outside this backend's tested boundary.

## Requirement coverage

| Capability | Current status | Required for stronger claim |
|---|---|---|
| Real-time representation | Local JSON ingestion, stale checks, CAD bindings | Verified CAN/DAQ gateway, time sync, hardware tests |
| Historical replay | CSV -> causal analytics; API history and replay client | Frontend playback interface |
| Physics/thermodynamics | Identities and uncalibrated thermal bench simulation | Measured maps, fuel/torque, calibration and validation |
| Fault detection | Contextual statistical anomalies + persistence | Confirmed fault events and external validation |
| Diagnosis | Alternative hypotheses and residual evidence | Labelled faults, extra measurements, engineer review |
| Health index | Explicitly named reference-alignment metric | Validated link between metric and physical degradation |
| Degradation | Descriptive session trend function | Longitudinal component histories with maintenance resets |
| RUL/failure prediction | Deliberate abstention, null output | Defined failure criterion, run-to-failure/censored data, uncertainty validation |
| Fuel efficiency | Unavailable on base logs | Measured fuel flow and shaft power |
| CHT/EGT/vibration/injection | Missing-channel registry, no invented estimates | Appropriate synchronized instruments/recordings |
| Battery/alternator | Voltage trend only | Current and charging-system context |
| Environmental scenarios | Assumed bench inlet conditions only | Calibrated airflow, cooling and performance maps |
| Mission reliability | Not implemented/validated | Reliability evidence and approved engineering process; no operational recommendations supplied |
| Fleet analytics | Isolated engine streams, not fleet-trained | Multiple identified engines; scaling/security work |
| UI | API/OpenAPI and CAD node data | Actual dashboard/CAD viewer integration |

No automatic aircraft control, ECU writes, autonomous maintenance, flight planning
or operational mission optimization is implemented.
