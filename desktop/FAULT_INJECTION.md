# Fault injection and RPM-linked motion

## Try it

1. Open the Digital twin workspace and expand Fault injection lab.
2. Choose an original CSV session or the synthetic systems demo as source.
3. Choose a scenario, zero-based start sample, duration and severity.
4. Select Create injected replay. A separate INJECTED session is saved; the original remains unchanged.
5. Select Replay fault onset to start a few samples before injection, or Inspect final fault sample to pause at its last sample.
6. Use Cutaway and leave RPM-linked motion checked. **Real speed · 1:1** is the default. At 1× replay, recorded propeller RPM drives the propeller at that speed and derived crank RPM drives the crankshaft. Use **Study · 1/120** only for slowed inspection. Play/Pause and replay speed drive the mechanism. Zero or unavailable RPM stops motion. Select the original session to return to baseline data.

At 100% severity the commanded coast-down reaches zero RPM at the final injected sample. It returns to the original recorded RPM after the selected interval. This deliberately imposed signal profile does not predict how an AE300 stalls or restarts. Use the final-sample button to inspect the zero-RPM state without playback immediately leaving the interval.

## Implemented perturbations

| Scenario | Experimental signal change at 100% severity |
|---|---|
| Bus voltage drop | Subtract 12 V, with a zero floor |
| Boost loss | Remove 90% of pressure above recorded ambient |
| Oil pressure loss | Reduce recorded pressure by 95% |
| Coolant rise | Linear ramp to +40 degrees C by the last fault sample |
| Oil temperature dropout | Set readings unavailable throughout the interval; severity unused |
| Commanded coast-down | Linear multiplier from 1 to 0 on recorded RPM |

Intervals use sample indices, not elapsed-time seconds. Changes are restricted to the interval; channels not targeted remain unchanged. Existing missing readings are not fabricated. Requests that change no usable readings are rejected. The standard sanitiser still enforces broad data plausibility, not approved operating limits.

Each experimental row includes the original value, requested/injected value, active-interval flag and changed flag. The backend runs the same causal analytics over the modified sequence; it does not mark a fault as detected merely because the injector knows its label. Existing source anomalies can persist. A dropout is primarily a data-quality event, and unsupported model regimes may abstain. This is not a detector accuracy benchmark.

JSON session reports include source-session lineage, injection settings, changed-row count and limitations. Nested injection into already injected sessions is rejected. Local storage uses the existing authenticated replay API; no ECU communication is added.

## Motion contract

The baked GLB cycle covers 720 crank degrees across frames 1–241 at 30 fps. The viewer samples this geometry at the RPM-integrated phase; the clip's original eight-second duration does not constrain playback speed. Crank RPM uses the configured 1.69 gearbox ratio. Default angular speed is crank RPM × 6 degrees per second, multiplied by replay speed. Study mode additionally divides by 120. A 2,000-rpm propeller input therefore means 3,380 crankshaft rpm, not 2,000 rpm for every shaft.

Seek resets to a reproducible pose from the replay sequence. Pause freezes motion. Missing RPM and zero RPM freeze motion. Large timestamp gaps do not accumulate an invented phase. Stored slowed travel is converted back to physical travel for real-speed rendering, so older replay data remains compatible. Frame updates use elapsed wall time without a delta cap that would silently slow down low-frame-rate rendering. Phase remains illustrative, not measured; 1 Hz telemetry cannot establish actual crank phase. Other fault types do not automatically change RPM, stop the engine, or animate damage because no validated coupled engine dynamics have been established.

At real engine speeds, a display cannot show every revolution. Frame-rate aliasing can make a shaft appear stationary, slow or reversed even with correct angular timing. Numeric RPM and the speed-mode label are authoritative for the requested rate; Study mode is for inspecting individual strokes. At 2× replay, physical-time motion also advances twice as fast; use 1× for wall-clock RPM matching.

Amber emissive highlighting identifies the mapped sensor for an active injected signal; it is not a claim that the sensor itself failed. The mapping uses the existing 32 CAD bindings; some share the same recorded input.

The viewer now uses the backend's `physics.crankshaft_rpm` as its speed input. A visible cycle-angle readout reports the illustrative pose. Piston/rod/valve motion uses the baked cycle, while continuous shaft/gear rotation uses the R4 motion descriptors in `src/cad-rotors.json` so non-integer ratios do not reset at each piston cycle. The propeller reduction is 1.69; accessory ratios are assumptions already present in the reconstructed CAD. Sensor colours distinguish injected signals (amber), backend residual deviations (red), missing recorded measurements (grey), and ordinary selection (teal).

## Validation scope

Automated tests cover all six perturbations, interval boundaries, source preservation, missing data, request validation, session lineage, reanalysis, zero-RPM physics and the animation-rate helper. Native Windows packaging remains blocked as documented in VALIDATION.md. This update is delivered in the source/browser preview, not a newly validated Windows executable.
