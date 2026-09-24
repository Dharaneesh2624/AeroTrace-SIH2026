# AE300 R4 — start here

A parametric engineering reconstruction for SIH Digital Twin development. Not a complete OEM manufacturing definition.

**619 separate valid CAD solids · 32 sensor bindings · animated linked mechanism.**

## Open

- `AE300_R4_Functional.blend`: fully assembled engine and separately located aircraft electronics; press Space for slow-motion playback.
- `AE300_R4_Cutaway.blend`: the same model with outer housings hidden for mechanism inspection.
- `AE300_R4_Assembly.step`: static named B-rep assembly, millimetres, for a STEP-compatible CAD application.
- `AE300_R4_Animated.glb` / `.fbx`: baked animation for viewers and downstream integration.
- `AE300_R4_motion.gif`: quick motion preview without CAD software.
- `parts/`: subsystem STEP files and selected individual parts.
- `source/` (ZIP) or `cad/ae300_v4/` (workspace): editable generator and parameter registry.

## What is functional

| System | Implemented | Limitation |
|---|---|---|
| Block/head/sump | Bored B-rep solids with removable housings | Casting contours, jackets and port geometry approximate |
| Crank/rods/pistons/rings | Analytic linked mechanism, 83 mm bore / 92 mm stroke | Rod length, journals, tolerances and bowl shape assumed |
| Reduction gearbox/flange | Three rotating gears; 1.69 ratio; source flange holes | Spur demo replaces OEM helical geometry; no bearing loads |
| Cam/valve train | Counter-rotating cams; 16 prescribed valves; moving retainers/followers/springs | No conjugate cam contact or spring force solution |
| Timing chain | Sprockets, chain paths, guides, tensioner concept | Chain static; assumed pitch and route |
| Accessory drive | Crank/alternator/pump pulleys and pump impeller animate | Static schematic belt; assumed drive ratios; starter parked |
| Air/exhaust/turbo | Hollow manifolds, turbo envelopes, wastegate concept | Turbo blade aerodynamics/rotor not modelled |
| Fuel injection | Pump, metering unit, rail, injectors, pipes, glow plugs | No nozzle needle/injector internals or EECU injection solver |
| Cooling/lubrication | Pump/filter/cooler/thermostat and hollow route concepts | Not continuous OEM internal galleries or a fluid simulation |
| Installation | Four documented mount datums and flange hole pattern | Mount bracket/support designs conceptual; envelope not exact |
| Electronics/sensors | 32 named signal bindings incl. CTS_GPC; family-specific shapes | Exact supplier dimensions and threads unavailable; no live data |
| EECU | Shell, backplate, fins, vent, 3 connectors, ECU A/B conceptual boards | No real PCB traces, firmware, connector pinout or controller simulation |
| Harness/electrics | GPC, BPA, external regulator; sensor and actuator branch registry; separate SIH loom | Unvalidated routes; no conductor gauge, wire list or electrical safety qualification |

## Checked

- Build-time OpenCascade checks recorded 619 valid connected solids before export.
- Four 83 mm bores and six 12.75 mm flange holes are source-controlled generator parameters.
- 721 analytic crank-angle samples: 92 mm stroke, rod closure and ideal axial valve clearance.
- R4 STEP geometric read-back and sampled moving-solid checks could not be rerun: Windows Application Control blocks OCP. Text-level STEP structure/count/units checks passed; this is not geometric reimport validation.
- Reopened Blender: maximum rod/piston joint error 0.00002670 mm.
- Valve positions, spring-retainer closure and gear/accessory driver ratios.
- Baked GLB reimported into a fresh Blender scene; rod/piston positions checked at nine frames.
- Selected housing/shaft/cam/ECU static clearances checked. Bare EECU reference envelope checked separately from harness plugs and mounting screws.
- GLB contains 115 animated node/path channels; required mechanism channels and sensor names checked.

Read `DESIGN_NOTES.md` before using geometry or sensor placement for engineering decisions.
Known source dimensions and assumptions are separated in `parameters.json`. No real engine telemetry is connected.

## R4 hardware audit

See `hardware_audit.json` for added components and remaining unavailable OEM inputs. `connection_map.json` identifies conceptual cable routes, NOT installation pinouts.
The previous EECU depth transcription (246 mm) was corrected to 226 mm from IM Fig14.7; 48.5 mm main-body height is distinguished from 58.5 mm raised overall height.
A full OEM-complete model still requires the applicable configuration/serial baseline, IPC, dimensioned casting and part drawings, supplier sensor/connector drawings, and approved harness data.