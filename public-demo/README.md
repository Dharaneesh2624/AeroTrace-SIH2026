# AeroTrace public SIH demo

Static, synthetic-only browser edition. Run `pnpm install --frozen-lockfile`, `pnpm build`, then `pnpm start`.
The private desktop app and its databases remain outside this directory.

## Research boundaries

- Seven fresh generated sessions: one synthetic source and six precomputed signal injections.
- Fault interval is fixed at samples 30–89, full severity. No custom online scoring or uploads.
- Precomputed outputs come from the existing unlabelled-reference research backend, not validated fault labels.
- The CAD is a reconstruction, not an OEM manufacturing model.
- Crank motion uses derived crank RPM; vibration displacement and roughness are illustrative, not accelerometer readings.
- Case vibration is magnified 60× by default and shown at 1/20 frequency. Rotation remains independently selectable at 1:1 or 1/120.
- Thermal simulation uses the same uncalibrated two-node balance as the local backend.
- No confirmed diagnosis, RUL estimate, flight readiness, hardware control or safety clearance.

## Visual references

- Grafana dashboard best practices: https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/
- Dewesoft condition monitoring: https://dewesoft.com/applications/condition-monitoring
- Dewesoft order tracking: https://manual.dewesoft.com/x/setupmodule/modules/machinery/ordertracking

No vendor artwork or branding was copied. The interface uses the existing project CAD and original styling.
