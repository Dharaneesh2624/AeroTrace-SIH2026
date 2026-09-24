# Validation record — 20 September 2026

## Update — 21 September 2026: telemetry-driven CAD and fault lab

Real-RPM update: real speed (1:1) is now the default; slow 1/120 motion is optional. All 8 Node tests pass, including 2,000 propeller revolutions and 3,380 crank revolutions per simulated minute at 24/30/60/144 fps, and a dropped-frame interval test. This verifies angular timing, not the ability of a monitor to resolve every rotation or actual measured crank phase. The earlier 7-test count below is the preceding checkpoint.

Browser verification after the real-speed rebuild: the running viewer reported 22,308 crank degrees/second for 3,718 derived crank RPM at 1× playback. Switching to Study selected the 1/120 rate, and switching back restored REAL SPEED. The preview was left running in real-speed mode. The refreshed source archive includes this change; old Windows binaries do not.

- 38 Python tests passed (29 backend + 9 desktop), with the same two dependency deprecation warnings.
- 7 Node tests passed, including loading the real GLB and checking piston stroke/seek poses, RPM motion, zero/missing RPM, pause, replay speed, continuous propeller ratio, sensor colours and IPC policy.
- TypeScript checking and production webpack build passed.
- Browser verification: coast-down replay changed actual rendered piston-position readouts from -0.0733662 m to -0.0813754 m; Pause retained -0.0813754 m on a subsequent check. Inspect final fault sample showed propeller RPM 0, derived crank RPM 0, stopped motion and model abstention for the stopped regime.
- Six fault profiles preserve source sessions and re-run analytics. Injection metadata and original values are retained. Faults are imposed signal experiments, not validated physical failure dynamics.
- Continuous shaft/gear rotation now uses unwrapped slowed crank travel, avoiding a jump at the 720-degree piston-cycle boundary. Accessory ratios remain illustrative CAD assumptions.
- These updates are in the source/browser preview. Previously produced Windows binaries are stale and were not rebuilt or revalidated; the existing Application Control blocker remains.

## Passed

- TypeScript checking and webpack production build.
- 29 existing backend pytest tests (2 dependency deprecation warnings).
- 1 desktop integration test with assertions for authentication, synthetic replay, 32 bindings, persistent deviations, event summaries, null RUL, route limits, database persistence, CSV import/deduplication and malformed-input rejection (2 dependency warnings).
- 2 Node tests for the IPC API-route allowlist and packaged-page origin policy.
- Browser preview: engine geometry rendered; cutaway changed visible components; simulated voltage-drop sample at index 185 displayed 20.1 V and a persistent anomaly; thermal bench produced visible curves and final simulated coolant 54.1 °C, oil 51 °C and assumed fuel flow 18.5 L/h at default settings.

Tests establish software behaviour only, not AE300 engineering accuracy, model diagnostic performance or flight safety. Browser tests exercise source Python plus the built UI, not Electron IPC/native dialogs.

## Build artifacts and blockers

- PyInstaller produced `desktop/backend-bundle/aerotrace-server/aerotrace-server.exe`. Its earlier direct launch was blocked with WinError 4551 (Application Control).
- Electron builder produced `output/ae300_desktop_v1/win-unpacked/`, including the frontend and bundled Python resources.
- NSIS packaging on 20 September exited 1 with `spawn UNKNOWN` in `computeScriptAndSignUninstaller`. The Windows Code Integrity log confirmed events 3077 and 3033 at 09:25:04 local time for `AeroTrace-Setup-0.1.0-x64.exe`; it failed signing-level/code-integrity requirements. Event 3118 also reported a Smart App Control block.
- The approximately 204-kB Setup executable is an incomplete intermediate. The approximately 160-MB `.nsis.7z` is a packaging payload, not an installer. Neither should be presented as a finished application installer.
- Full output is preserved in `output/ae300_desktop_v1/package-2026-09-20.log`. Security settings were not modified.

## Not verified

Native application launch, completed NSIS installer, install/uninstall, native file dialogs, Electron renderer/IPC behaviour at runtime, packaged backend lifecycle, code signing, behaviour on another Windows computer, and a full disconnected-network test. No release-ready claim is made.

## Changes during resumption

- Replaced ambiguous “Local engine online” with “Local analytics ready”.
- Distinguished transient anomaly candidates from readings within the learned reference.
- Used a numeric chart axis so replay cursors remain valid between downsampled points.
- Made the desktop import test self-contained with a generated CSV fixture.
- Added a portable build script with failure checks and this handoff documentation.

Next release gate: an approved development/release environment and trusted signing process, followed by the native checks in README.md. Do not disable security protections to get past this gate.
