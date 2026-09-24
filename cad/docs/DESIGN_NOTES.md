# AE300 R4 — functional CAD reconstruction

This package is a parameter-driven AE300/E4 engineering reconstruction for the SIH
engine-health Digital Twin. It contains actual OpenCascade boundary-representation
solids, a named STEP assembly, subsystem STEP files, an editable Blender scene and
animated exchange files generated from the same tessellated solids.

**Functional scope:** linked crank, rods, pistons, reduction shafts/gears and an
idealized four-stroke valve sequence, translating retainers/followers, compressed
springs, and rotating accessory pulleys. The model supports component selection,
section views and named telemetry attachment. It is not a complete OEM production
definition, a validated engine simulator, or a manufacturing release.

## Open the model

- Open `AE300_R4_Assembly.step` in a STEP-compatible CAD application for editable
  solids, names, colours and subsystem grouping. STEP holds a static assembly pose;
  it does not carry the Blender drivers or native feature history.
- Open `AE300_R4_Functional.blend` in Blender and press Space to play the mechanism.
  This file now opens fully assembled with separately located aircraft equipment.
  `AE300_R4_Cutaway.blend` opens with housings hidden for section review. Select
  `AE300_CONTROL__animate_crank_angle` and change its `crank_angle_deg` custom
  property to inspect a specific phase when playback is stopped and the property
  animation is disabled. Timeline animation otherwise controls this property.
- `AE300_R4_Animated.glb` and `.fbx` contain sampled mechanism motion for importing
  into a viewer or Unreal workflow. Unreal integration has not been tested here.
- To restore all bodies in Blender, run the embedded `SHOW_ASSEMBLED.py` text or
  restore the objects' eye/camera visibility in the Outliner. Aircraft integration
  equipment can be hidden independently.
- CAD units are millimetres. Blender and GLB geometry is in metres. Do not apply an
  additional 1000x scale on import.

The preview covers two crankshaft revolutions (one four-stroke cycle), deliberately
slowed. Repeating it resets the propeller and accessory phases because their speed
ratios do not all complete integer turns in 720 crank degrees. This is a cycle
inspection clip, not a seamless real-time engine-speed loop.

## R4 hardware completion and corrections

R4 adds the documented CTS_GPC temperature-sensor binding, GPC box, pneumatic
boost-pressure actuator distinct from the wastegate diaphragm, external alternator
regulator, oil separator/bypass, filler/dipstick/drain concepts, timing-drive
enclosure, casting ribs, and named sensor/actuator harness branches. Sensor bodies
now distinguish pressure transducers, temperature probes, speed pickups, proposed
thermocouples and accelerometers, and other sensor families. Exact supplier
dimensions and thread specifications remain unavailable.

The EECU has a separate enclosure and backplate, fins, vent, and three circular
receptacle/mating-plug concepts labelled G115 (ECU A), G121 (power), and G116 (ECU B).
Those labels are from MM71-5/PDF109. The internal boards only illustrate redundant
architecture; they are NOT actual PCB layouts and contain no firmware simulation.

**Correction to R3:** IM Fig14.7/PDF81 was enlarged and rechecked. The drawing plan
depth is 226 mm, not the earlier 246 mm transcription. Main-body height48.5 mm is
distinct from the raised connector-region overall height58.5 mm. Width247 mm,
connector pitch77.25 mm and connector centre height30.7 mm are represented.
Splitting the 226 mm depth between shell and receptacle projection, mounting-hole
coordinates, fin pitch and all internal dimensions remains reconstruction. Bare
EECU extents are checked separately from mating backshells and screw projections.

`hardware_validation.json` contains selected static clearance checks for cam/head,
shaft/gearbox, timing-gear/case and conceptual PCB/enclosure pairs; it is not a
whole-assembly interference qualification. `connection_map.json` describes routes
and network roles, never pin assignments. SIH sensors use a separate DAQ network;
CTS_GPC is routed to the glow controller. This is NOT an approved aircraft harness.

## Source control

Primary geometry references inspected for this revision:

1. Uploaded `installion manual.pdf`: E4.02.01 Rev22. Fig4.4.1–4.4.4, PDF pages
   22–25; Table6.1/Fig6.4, PDF32; EECU Fig14.7, PDF81; propeller interface
   Fig15.2/section15.4, PDF134.
2. Uploaded `AE300 Manual.pdf`: E4.08.04 Rev13 package. Printed01-9 to01-12,
   PDF31–34, and sensor architecture printed01-24/25, PDF46–47. Individual pages
   have their own revision numbers; the package revision does not replace them.
3. The manufacturer’s public [AE300 specification](https://www.diamondaircraft.com/en/austro-engine/e4-series/overview/)
   confirms 123.5 kW, four cylinders and 1991 cm³. Its current 186 kg dry mass differs
   from the historical manual’s 185 kg; neither is used to infer model mass.
4. AustroView's [channel definitions](https://github.com/ingramleedy/AustroView/blob/main/austroview.py)
   are used only as a telemetry naming reference. They are not live CAN message IDs.

The uploaded “complete detailed parameter” compilation was not accepted as an
unverified geometry authority. Direct drawing inspection corrected:

| Item | Earlier model | R3 reference |
|---|---:|---:|
| Front-view height | 741 mm | **574 mm** |
| Rear-left mount Z | −288 mm | **−298 mm** |
| Block material representation | Aluminium | **Cast iron**, per MM01-12 |
| Mount origin | Added 25 mm Z offset | **Propeller-flange centre, no offset** |
| Cylinder arrangement | Upright box model | Inclined bank; **40° reconstruction assumption** |
| Crankshaft representation | Straight cylinder | Connected four-throw, five-main solid |
| Rod animation | Static/disconnected | Analytic closure at crankpin and wrist pin |
| Flange outer diameter | Approximate | **127 mm**, Fig15.2 |

## Verified dimensions and reconstruction choices

`parameters.json` separates verified source values from assumed geometry.

| Feature | Source-controlled value | Geometry actually represented |
|---|---|---|
| Cylinder bore | 83 mm | Four bored surfaces in the block; no separate liners |
| Stroke | 92 mm | 46 mm crank throw; true slider-crank equation |
| Cylinder pitch | 90 mm | Four axes at 270, 360, 450, 540 mm X; first station assumed |
| Compression ratio | 17.5:1 | Equivalent clearance volume and cylindrical piston bowl |
| Firing sequence | 1–3–4–2 | Power TDC at 0°, 180°, 360°, 540° respectively |
| Main bearings | Five | Five bearing and cap positions |
| Valvetrain | DOHC, 16 valves | 8 intake/8 exhaust; idealized lift sequence |
| Cam topology | One chain-driven cam; second gear-driven | Two counter-rotating cams at half crank speed |
| Reduction ratio | 1.69:1, three gears | 100/50/169-tooth **assumed spur** demonstration |
| Propeller flange | 6 × 12.75 mm holes, PCD101.6, OD127 | Explicit through holes; remaining flange details assumed |
| Engine mounts | Four Table6.1 coordinates | Exact datum points, generic pads/support arms |
| EECU reference envelope | 58.5 × 247 × 226 mm | Bare case/receptacles; mating harness and screw projections excluded |

The engine's documentary envelope is **738 × 855 × 574 mm**. The reconstructed
assembly's measured extents are recorded independently in `validation.json`; they
do not equal the full OEM envelope. Accessories and contours are not adequately
dimensioned in the manuals to claim a surface-identical envelope. The separate
aircraft integration layout deliberately lies outside the engine envelope.

The connecting-rod length (147 mm), piston clearance, pin diameter, cam lift
(7.5 mm), ideal timing windows, gear tooth counts/module, housing walls, manifold
paths, spring constants and exact sensor threads have not been verified as AE300
manufacturing dimensions. They are editable reconstruction values, not hidden OEM
claims. The actual gearbox illustrated in the manual uses helical gears; this
package's sampled involute spur profiles illustrate the transmission ratio.

R3 adds spring seats/retainers, 10 cam-bearing caps, toothed cam gears, conceptual
20:40 timing sprockets, chain guides/tensioner, an accessory crank pulley, driven
alternator/water-pump pulleys, a parked starter pinion/solenoid, a generic pump
impeller, and separately selectable service-line/routing concepts. These additions
are reconstruction dimensions; none introduces new verified OEM dimensions.

The chain and accessory-belt paths are static and schematic; their engagement and
wrap geometry are not validated. Cam lobes and follower geometry are schematic;
the valve animation is prescribed by an ideal lift law,
not solved from cam contact. The model does not include proprietary injector
internals, full oil/coolant galleries, exact turbo blade geometry, all fasteners,
all shaft seals, OEM material specifications, fits, GD&T or fatigue design.
Spring compression uses local axial mesh scaling: it is a visual kinematic proxy,
not a constant-wire-section deformation or a spring-force calculation. STEP
contains the undeformed spring solids in the static assembly pose.

`13_Routing_Concepts` contains external demonstration circuits to the separately
located radiator/intercooler and fuel interfaces. These routes are not aircraft
installation drawings; they are hidden in engine-only views. Pipe walls are hollow
solids, but OEM port bores and internal passage continuity are not fully modelled.

## Sensor plan for the SIH requirement

`sensor_map.json` contains 32 bindings with object names, proposed mounting
positions, directions, units, source status and channel availability. Orange
sensor objects represent the documented sensor inventory; violet objects are SIH
instrumentation concepts. **Their generic bosses and thread envelopes are not
installation-approved hardware designs.**

| Measurement | Representation | Data status |
|---|---|---|
| RPM/position | CRS1/2 and CAS1/2 | Crank/cam sensors; base log gives propeller RPM |
| Boost and intake temperature | BPS1/2 and IAT1/2 | Documented redundant ECU channels |
| Oil pressure, temperature/level | OPS and MOK | Log channels803,811,814 |
| Coolant temperature | CTS | Log channel806 |
| Glow controller coolant temperature | CTS_GPC, B50/6 | Separate GPC input; not base16 log channel |
| Fuel and rail pressure | FPS and RPS | Log channels809 and804 |
| Fuel temperature | FTS | Documented sensor; not one of the decoder's base channels |
| Gearbox oil temperature | GBTS | Log channel810 |
| Ambient pressure/battery voltage | EECU signal markers | Log channels801/808; not separate new OEM sensors |
| Power lever | PLS1/2 | Aircraft-side controls; base channel805 |
| CHT/head-metal temperature | Four proposed head probes | Added sensors; coolant temperature is not CHT |
| EGT | Four proposed exhaust probes | Added sensors; not in base16 log |
| Vibration | Block and gearbox mounting concepts | Added accelerometers, higher-rate acquisition required |
| Fuel flow | External flow-sensor concept | Added measurement; not in base16 log |
| Alternator current | Current-sensing marker | Added measurement; voltage alone is not full alternator health |
| Injection timing | Injector objects / crank phase | Future EECU signal or simulation; not fabricated as measured telemetry |

No real telemetry or RUL model is connected to these CAD objects. Each starts with
`telemetry_quality=unbound`. Sensor positioning and signal observability need
confirmation on a real engine/test rig before acquisition hardware is specified.

## Validation and limits

**2026-09-19 export-check limitation:** the final R4 generator previously completed
619 build-time B-rep checks and the selected hardware-clearance checks. During
resume, Windows Application Control blocked the OCP DLL import, so the geometric
STEP read-back and moving-solid overlap script could not be rerun. The earlier
attempt had started before export finished and did not pass. Do not treat R3
read-back results as R4 validation. `export_structure_validation.json` records
only STEP text-level completeness, units and solid/entity counts. The original
`validation.json` retains `step_roundtrip: pending`; `release_validation.json`
reports geometric read-back as unavailable, not successful.

Visual exports use CPU Cycles rendering after the previous NVIDIA/OpenGL crash.
Blender and GLB motion checks are independent of the blocked CAD library; their
actual results are recorded in the corresponding validation files.

`validation.json` records build-time B-rep validity, positive volume and connected-solid
count for every component. Its STEP read-back status remains pending. The unavailable
`check_cad.py` checks include bore/flange read-back and sampled moving-interface checks.
`blender_validation.json` checks driven piston positions
against the same analytic model used for CAD poses, rod-end closure, valve and
spring-retainer positions, and reduction/accessory rotation ratios.

The independent mechanism check uses 721 angle samples over 720°. It checks 92 mm
stroke, rod joint closure and idealized axial valve/piston clearance. The currently
unavailable STEP moving-interface checks are designed to sample C1 every30° for
piston/block and rod/crank intersections. Even when run, they do **not** replace
exhaustive dynamic contact, bearing clearance, thermal
expansion, accessory interference or structural checks. CAD volume is not an
engine mass estimate. The geometry cannot establish real engine health, remaining
life, safe limits or mission reliability without validated models and data.

## Regenerate

Sources are in `cad/ae300_v4/`: `parameters.json`, `kinematics.py`, `occ.py`,
`build_engine.py`, `check_cad.py`, and `blender_scene.py`.

```powershell
& 'C:\aerotrace\.venv-cad\Scripts\python.exe' 'C:\aerotrace\cad\ae300_v4\build_engine.py'
& 'C:\aerotrace\.venv-cad\Scripts\python.exe' 'C:\aerotrace\cad\ae300_v4\check_cad.py'
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python 'C:\aerotrace\cad\ae300_v4\blender_scene.py'
```

The generator uses `cadquery-ocp==7.9.3.1.1` directly. CadQuery/VTK is not imported.
Blender5.2.1 was used to export the animated deliverables. A new installation needs
the OpenCascade Python bindings and Blender, not the entire project virtual
environment copied into the deliverable.

In the ZIP, scripts are under `AE300_R4/source/`. Run `build_engine.py`, then
`check_cad.py` with an environment containing the requirements, and run
`blender_scene.py` using Blender's `--background --python` option. `paths.py`
automatically writes into the containing `AE300_R4` directory when unpacked;
repository runs write to `output/ae300_r4/`. These scripts regenerate outputs in
place. Keep copies of any manually edited deliverables before rebuilding.

For the complete release checks and preview, then reopen the generated `.blend`
with Blender and run `review_motion.py`; run `verify_glb_import.py` in a fresh
background Blender process; run `validate_delivery.py` with Python; and run
`package_delivery.py` with Python/Pillow. The last script generates the preview
GIF, SVG reference sheet, and ZIP. `release_validation.json` summarizes the
results, including a one-clip GLB check and a reimported baked-motion joint check.

Further fidelity requires OEM dimensioned component drawings, the selected E4
configuration/serial baseline, verified rod/cam data, supplier sensor drawings and
measured exterior references. These inputs can replace assumptions in the source
registry and regenerate the downstream CAD and visualization consistently.
