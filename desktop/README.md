# AeroTrace desktop — AE300 research workspace

Status on 20 September 2026: the dashboard and source analytics run locally. Windows packaging is **not release-ready**. The bundled backend launch and the NSIS uninstaller-generation executable were blocked by Windows Application Control. Do not install or distribute the small `AeroTrace-Setup-0.1.0-x64.exe` intermediate as a completed installer. See [VALIDATION.md](VALIDATION.md).

## Features implemented

New: [fault injection and RPM-linked motion](FAULT_INJECTION.md), including six controlled experiments, source-preserving replay and a cutaway mechanism driven by RPM and playback state. See that guide for the signal-level limitations and how to inspect a stopped engine.

- Local 619-solid reconstructed engine viewer: assembled, cutaway, electronics and illustrative mechanism motion.
- 32 CAD sensor bindings; 16 telemetry-channel inputs. Bindings may share a recorded channel; they are not 32 independently measured signals.
- CSV import, persistent local sessions, replay controls, event seeking, trend plots and JSON research reports.
- Contextual anomaly candidates and persistent deviations, data-quality warnings, physics estimates and an explicitly uncalibrated thermal experiment.
- Electron shell with a private loopback Python service, token-authenticated API, sandboxed renderer and restricted IPC.

The first-run 480-s demo is generated locally, not an AE300 flight log. Its synthetic baseline is not guaranteed to match the learned reference; an anomaly outside an injected interval is not proof of a detected real fault. The reference model was developed from unlabelled public AustroView examples. No confirmed diagnosis, failure probability, validated RUL, OEM-complete geometry, manufacturing readiness or airworthiness assessment is claimed. There is no ECU control or live hardware connection.

## Open the source preview

The existing workspace preview is at `http://127.0.0.1:8010/` while its process is running. To restart from this workspace:

```powershell
Set-Location C:/aerotrace/desktop
& ../backend/.venv/Scripts/python.exe scripts/preview_host.py
```

For a fresh checkout, use Python 3.12 and a Node/pnpm toolchain, install the backend into your own virtual environment, then build the UI:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -e './backend[test]' 'pyinstaller==6.22.3' pillow
Set-Location desktop
pnpm install --frozen-lockfile
pnpm run build
& ../.venv/Scripts/python.exe scripts/preview_host.py
```

The source archive preserves `backend/` and `desktop/` as siblings and includes prepared CAD assets. Preview data is stored under `desktop/preview-data/`. Stop the preview with Ctrl+C in its terminal. This developer preview exposes its local session token to its own renderer; it is for a trusted local machine only. Do not expose port 8010 to a network. It is not the packaged Electron runtime and cannot validate installer or Electron security behaviour.

## Build Windows software on an approved development machine

After installing the dependencies above:

```powershell
# Run from desktop; supply your virtual environment's Python executable.
./scripts/build_windows.ps1 -Python ../.venv/Scripts/python.exe -Pnpm pnpm
```

The script runs tests, compiles the UI, packages Python with PyInstaller, and then builds NSIS. It checks exit codes and does not alter OS security settings. Output goes to `output/ae300_desktop_v1/`. A failed command is not a completed release. Tool downloads require internet during setup/build; runtime assets are local.

The current packaging configuration is unsigned. A release requires an administrator-approved build/test environment and an appropriate trusted code-signing/release process. Do not disable or evade Smart App Control to run these artifacts. Signing alone is not a guarantee of admission under an organization's policy.

## Native launch checks still required

On an environment whose policy permits this development build, verify ordinary installation, launch, offline operation, native CSV picker, JSON save dialog, restart persistence, backend shutdown and uninstall. An optional hidden smoke check is implemented:

```powershell
& ../output/ae300_desktop_v1/win-unpacked/AeroTrace.exe --smoke-test C:/AeroTraceSmoke
```

Use a fresh test-data directory and inspect its result files. Do not run this on the currently blocked machine as a workaround. The whole `win-unpacked` folder, including `resources/backend/`, is needed; `AeroTrace.exe` is not self-contained.

Packaged application data uses Electron's per-user `userData` directory (`data/desktop.sqlite3`, `data/telemetry.sqlite3`, and `backend.log`). Uninstall is configured to retain app data. Imported logs are not uploaded.

## Project layout

`src/` contains the React/Three.js/ECharts UI; `electron/` contains the desktop lifecycle and IPC policy; `python/desktop_server.py` contains the replay companion; `../backend/aerotrace/` contains analytics; `scripts/` contains preparation, preview and build tools.

CSV headers and units are validated against `backend/aerotrace/schema.py`. Raw `.ae3` files must first be decoded to compatible AustroView CSVs. The desktop import limit is 10 MB and 20,000 valid records per file. Missing/invalid measurements remain unavailable. Reports summarize research evidence rather than maintenance instructions.

Source/provenance: [AustroView](https://github.com/ingramleedy/AustroView), reference revision `f9187ca3cd9094c5b547a8186559f5e099976c6d`. Backend assumptions and evaluation are documented in `backend/docs/` and `backend/artifacts/`. No raw public CSVs, private imported logs or runtime databases are included in the desktop source archive.
