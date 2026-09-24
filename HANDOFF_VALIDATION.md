# GitHub handoff validation

Validated on Windows on 24 September 2026.

## Checks completed

- Python backend and desktop tests: **37 passed, 1 skipped**. The optional upstream-data integration test skipped because original flight logs are not included. Two dependency deprecation warnings remain.
- Desktop JavaScript tests: **10 passed**, including RPM synchronization, CAD animation channels, sensor appearance, vibration controls and local API boundaries.
- Desktop TypeScript check: passed.
- Public demo TypeScript check and production build: passed.
- Public demo verification: passed for seven synthetic sessions, fault scenarios, thermal calculations, CAD decompression, static assets and exclusion of private backend data.
- Public demo frozen lockfile validation: passed.
- Restored GLB and STEP assets: SHA-256 matches the original project exports.

Build and test checks used the existing local dependency installation; a fresh dependency download on another computer has not been tested. Install commands and prerequisites are in [README.md](README.md).

## Handoff boundaries

- This folder has no previous Git history, hosting-account configuration, private imported logs, local databases, dependency caches or virtual environments.
- Compressed CAD assets and the editable Blender scene are supplied. Uncompressed STEP/GLB files and web build output are regenerated using the documented commands.
- Original manufacturer manuals are not redistributed. Model provenance and research limitations are documented in the repository.
- No production EXE is included. Windows installer packaging is not validated.
- No GitHub repository has been created or pushed as part of this handoff.
- These checks demonstrate software behavior, not physical engine accuracy, fault-diagnosis validity or airworthiness.
