"""Validate animated GLB structure and compile a candid release summary."""
import json, struct, math
from pathlib import Path
from paths import OUT

raw=(OUT/'AE300_R4_Animated.glb').read_bytes()
magic,version,total=struct.unpack_from('<4sII',raw)
assert magic==b'glTF' and version==2 and total==len(raw)
size,kind=struct.unpack_from('<I4s',raw,12)
assert kind==b'JSON'
doc=json.loads(raw[20:20+size])
assert len(doc.get('animations',[]))==1,'Deliver one synchronized mechanism clip, not per-object animations'
nodes={n['name']:i for i,n in enumerate(doc['nodes']) if 'name' in n}
channels={(c['target']['node'],c['target']['path']) for a in doc.get('animations',[]) for c in a['channels']}
required=[('Crankshaft_4Throws_5Mains','rotation'),('Gear_Output_169T','rotation'),
          ('Alternator_Pulley','rotation'),('Water_Pump_Pulley','rotation')]
for i in range(1,5):
    required.extend([(f'Piston_C{i}','translation'),(f'Connecting_Rod_C{i}','translation'),(f'Connecting_Rod_C{i}','rotation')])
    for j in range(1,5):required.append((f'Valve_Spring_C{i}_{j}','scale'))
missing=[f'{n}:{p}' for n,p in required if n not in nodes or (nodes[n],p) not in channels]
assert not missing,missing
for mesh in doc['meshes']:
    for primitive in mesh['primitives']:
        assert doc['accessors'][primitive['attributes']['POSITION']]['count']>0
for accessor in doc['accessors']:
    for field in ['min','max']:
        assert all(math.isfinite(x) for x in accessor.get(field,[]))
cad=json.loads((OUT/'validation.json').read_text())
motion=json.loads((OUT/'blender_validation.json').read_text())
glb_check=json.loads((OUT/'glb_validation.json').read_text())
hardware=json.loads((OUT/'hardware_validation.json').read_text())
connections=json.loads((OUT/'connection_map.json').read_text())
sensors=json.loads((OUT/'sensor_map.json').read_text())
step_roundtrip_pass=isinstance(cad.get('step_roundtrip'),dict) and cad['step_roundtrip'].get('valid',False)
structure=None
if not step_roundtrip_pass:
    structure=json.loads((OUT/'export_structure_validation.json').read_text())
    assert structure['structure_checks_pass']
    assert not cad['invalid_parts'] and not cad['errors']
else:
    assert cad['checks_pass']
assert len(set(s['id'] for s in sensors))==len(sensors)
assert all(s['object'] in nodes for s in sensors)
assert motion['max_joint_error_mm']<.001
assert glb_check['max_joint_error_mm']<.001
assert hardware['check_pass'] and hardware['eecu_extent_pass']
assert next(s for s in sensors if s['id']=='CTS_GPC')['network']=='GPC'
assert all(s.get('network')=='SIH_DAQ' for s in sensors if s['category']=='SIH')
assert all(c['route'] in nodes for c in connections)
summary={
    'release':'R4 hardware-expanded functional reconstruction; NOT OEM production CAD',
    'parts':cad['part_count'],'sensor_bindings':len(sensors),
    'glb_meshes':len(doc['meshes']),'glb_animations':len(doc.get('animations',[])),
    'glb_animated_node_paths':len(channels),'required_motion_channels_checked':len(required),
    'missing_required_motion_channels':missing,'step_roundtrip_pass':True if step_roundtrip_pass else None,
    'step_validation_status':'Geometric read-back passed' if step_roundtrip_pass else structure['geometric_step_roundtrip'],
    'step_structure_checks_pass':True if structure else None,
    'engine_extents_mm':cad['engine_extents_mm'],'reference_envelope_mm':cad['reference_envelope_mm'],
    'blender_joint_error_mm':motion['max_joint_error_mm'],
    'reimported_glb_joint_error_mm':glb_check['max_joint_error_mm'],
    'selected_hardware_interface_checks_pass':hardware['check_pass'],'bare_eecu_extents_mm':hardware['bare_eecu_extents_mm'],
    'connection_registry_count':len(connections),'sih_and_oem_networks_separate':True,
    'scope_limits':['Not exact exterior geometry or manufacturing drawings',
        'No exhaustive all-parts interference check',
        'Static schematic chain and belt paths; prescribed valve motion, no cam contact solver',
        'No validated combustion, thermal, fatigue, vibration or fluid simulation',
        'No live telemetry connection; additional SIH signals need sensors/data'],
}
(OUT/'release_validation.json').write_text(json.dumps(summary,indent=2))
coverage=[
    ('Block/head/sump','Bored B-rep solids with removable housings','Casting contours, jackets and port geometry approximate'),
    ('Crank/rods/pistons/rings','Analytic linked mechanism, 83 mm bore / 92 mm stroke','Rod length, journals, tolerances and bowl shape assumed'),
    ('Reduction gearbox/flange','Three rotating gears; 1.69 ratio; source flange holes','Spur demo replaces OEM helical geometry; no bearing loads'),
    ('Cam/valve train','Counter-rotating cams; 16 prescribed valves; moving retainers/followers/springs','No conjugate cam contact or spring force solution'),
    ('Timing chain','Sprockets, chain paths, guides, tensioner concept','Chain static; assumed pitch and route'),
    ('Accessory drive','Crank/alternator/pump pulleys and pump impeller animate','Static schematic belt; assumed drive ratios; starter parked'),
    ('Air/exhaust/turbo','Hollow manifolds, turbo envelopes, wastegate concept','Turbo blade aerodynamics/rotor not modelled'),
    ('Fuel injection','Pump, metering unit, rail, injectors, pipes, glow plugs','No nozzle needle/injector internals or EECU injection solver'),
    ('Cooling/lubrication','Pump/filter/cooler/thermostat and hollow route concepts','Not continuous OEM internal galleries or a fluid simulation'),
    ('Installation','Four documented mount datums and flange hole pattern','Mount bracket/support designs conceptual; envelope not exact'),
    ('Electronics/sensors','32 named signal bindings incl. CTS_GPC; family-specific shapes','Exact supplier dimensions and threads unavailable; no live data'),
    ('EECU','Shell, backplate, fins, vent, 3 connectors, ECU A/B conceptual boards','No real PCB traces, firmware, connector pinout or controller simulation'),
    ('Harness/electrics','GPC, BPA, external regulator; sensor and actuator branch registry; separate SIH loom','Unvalidated routes; no conductor gauge, wire list or electrical safety qualification'),
]
(OUT/'functional_coverage.json').write_text(json.dumps([dict(system=s,implemented=i,limitation=l) for s,i,l in coverage],indent=2))
lines=['# AE300 R4 — start here','',
       'A parametric engineering reconstruction for SIH Digital Twin development. Not a complete OEM manufacturing definition.','',
       f'**{cad["part_count"]} separate valid CAD solids · {len(sensors)} sensor bindings · animated linked mechanism.**','',
       '## Open','',
       '- `AE300_R4_Functional.blend`: fully assembled engine and separately located aircraft electronics; press Space for slow-motion playback.',
       '- `AE300_R4_Cutaway.blend`: the same model with outer housings hidden for mechanism inspection.',
       '- `AE300_R4_Assembly.step`: static named B-rep assembly, millimetres, for a STEP-compatible CAD application.',
       '- `AE300_R4_Animated.glb` / `.fbx`: baked animation for viewers and downstream integration.',
       '- `AE300_R4_motion.gif`: quick motion preview without CAD software.',
       '- `parts/`: subsystem STEP files and selected individual parts.',
       '- `source/` (ZIP) or `cad/ae300_v4/` (workspace): editable generator and parameter registry.','',
       '## What is functional','',
       '| System | Implemented | Limitation |','|---|---|---|']
lines.extend(f'| {s} | {i} | {l} |' for s,i,l in coverage)
lines += ['', '## Checked','',
          f'- Build-time OpenCascade checks recorded {cad["solid_count"]} valid connected solids before export.',
          '- Four 83 mm bores and six 12.75 mm flange holes are source-controlled generator parameters.',
          '- 721 analytic crank-angle samples: 92 mm stroke, rod closure and ideal axial valve clearance.',
          '- R4 STEP geometric read-back and sampled moving-solid checks could not be rerun: Windows Application Control blocks OCP. Text-level STEP structure/count/units checks passed; this is not geometric reimport validation.',
          f'- Reopened Blender: maximum rod/piston joint error {motion["max_joint_error_mm"]:.8f} mm.',
          '- Valve positions, spring-retainer closure and gear/accessory driver ratios.',
          '- Baked GLB reimported into a fresh Blender scene; rod/piston positions checked at nine frames.',
          '- Selected housing/shaft/cam/ECU static clearances checked. Bare EECU reference envelope checked separately from harness plugs and mounting screws.',
          f'- GLB contains {len(channels)} animated node/path channels; required mechanism channels and sensor names checked.',
          '', 'Read `DESIGN_NOTES.md` before using geometry or sensor placement for engineering decisions.',
          'Known source dimensions and assumptions are separated in `parameters.json`. No real engine telemetry is connected.',
          '', '## R4 hardware audit','',
          'See `hardware_audit.json` for added components and remaining unavailable OEM inputs. `connection_map.json` identifies conceptual cable routes, NOT installation pinouts.',
          'The previous EECU depth transcription (246 mm) was corrected to 226 mm from IM Fig14.7; 48.5 mm main-body height is distinguished from 58.5 mm raised overall height.',
          'A full OEM-complete model still requires the applicable configuration/serial baseline, IPC, dimensioned casting and part drawings, supplier sensor/connector drawings, and approved harness data.']
(OUT/'START_HERE.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(summary,indent=2))
