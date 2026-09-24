"""Text-level STEP checks when geometric read-back is unavailable.

This is deliberately NOT a replacement for OpenCascade B-rep validation.
It never marks a STEP geometric roundtrip as passed.
"""
import json,re,hashlib
from paths import OUT
cad=json.loads((OUT/'validation.json').read_text())
path=OUT/'AE300_R4_Assembly.step'
raw=path.read_bytes();text=raw.decode('ascii')
manifolds=len(re.findall(r'=\s*MANIFOLD_SOLID_BREP\s*\(',text))
with_voids=len(re.findall(r'=\s*BREP_WITH_VOIDS\s*\(',text))
solids=manifolds+with_voids
ids=re.findall(r'^#(\d+)\s*=',text,re.M)
assert text.lstrip().startswith('ISO-10303-21;')
assert text.rstrip().endswith('END-ISO-10303-21;')
assert len(ids)==len(set(ids))
assert solids==cad['solid_count']
assert 'SI_UNIT(.MILLI.,.METRE.)' in text
assert all(p['valid'] and p['solids']==1 and p['volume_mm3']>0 for p in cad['parts'])
report=dict(structure_checks_pass=True,byte_length=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
    solid_records=solids,manifold_solid_records=manifolds,breps_with_voids=with_voids,unique_entity_ids=len(ids),millimetre_units=True,
    build_time_geometry_checks='619 valid positive-volume single solids recorded by generator before STEP export',
    geometric_step_roundtrip='NOT RERUN: Windows Application Control blocked OCP import on 2026-09-19',
    scope='STEP header/footer, unique entity IDs, solid record count and units only. Does not prove imported B-rep validity or collisions.')
(OUT/'export_structure_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
