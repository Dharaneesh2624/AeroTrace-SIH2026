"""Independent export and mechanism checks on reopened STEP geometry."""
import json
import math
from pathlib import Path
import occ as o
from kinematics import a,v,R,L,FIRE,validate
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.TopoDS import TopoDS
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

from paths import OUT
report=json.loads((OUT/'validation.json').read_text())
full=o.read_step(OUT/'AE300_R4_Assembly.step')
count=o.solid_count(full);ok=o.valid(full)
report['step_roundtrip']={'valid':ok,'solid_count':count,'expected':report['solid_count'],'bbox_mm':o.bounds(full)}
assert ok and count==report['solid_count'], 'STEP did not roundtrip'

def read(name):return o.read_step(OUT/'parts'/f'{name}.step')
crank=read('Crankshaft_4Throws_5Mains');block=read('Crankcase_4x83mm_Bores')
piston=read('Piston_C1');rod=read('Connecting_Rod_C1')
flange=read('Propeller_Flange_6x12_75_PCD101_6')
assert o.solid_count(crank)==1,'Crankshaft must be connected'

def cylinder_radii(s):
    radii=[];ex=TopExp_Explorer(s,TopAbs_FACE)
    while ex.More():
        surf=BRepAdaptor_Surface(TopoDS.Face_s(ex.Current()))
        if surf.GetType()==GeomAbs_Cylinder:radii.append(surf.Cylinder().Radius())
        ex.Next()
    return radii
radii=cylinder_radii(flange)
holes=sum(abs(r-v('flange_hole_diameter')/2)<1e-7 for r in radii)
assert holes==6, f'Expected six flange bores, got {holes}'
assert any(abs(r-v('bore')/2)<1e-7 for r in cylinder_radii(block))
assert sum(abs(r-v('bore')/2)<1e-7 for r in cylinder_radii(block))==4
report['dimension_checks']={'flange_12_75_mm_holes':holes,'block_83_mm_bore_count':4,'crankshaft_connected_solid':True}

checks=[]
for theta in range(0,360,30):
    t=math.radians(theta);yy=R*math.sin(t);zz=R*math.cos(t);h=math.sqrt(L*L-yy*yy);x=a('cylinder_x0')
    p=o.move(piston,(x,0,zz+h));r=o.move(rod,(x,yy,zz),math.degrees(math.atan2(yy,h)))
    c=o.move(crank,rx=-theta)
    # Narrow scope: major moving interfaces. This does not certify all accessory
    # packaging, bearing contact, cam/roller contact or thermal expansion.
    checks.append({'angle_deg':theta,'piston_block_overlap_mm3':max(0,o.volume(o.common(p,block))),
                   'rod_crank_overlap_mm3':max(0,o.volume(o.common(r,c)))})
report['sampled_moving_interface_checks']=checks
report['max_piston_block_overlap_mm3']=max(x['piston_block_overlap_mm3'] for x in checks)
report['max_rod_crank_overlap_mm3']=max(x['rod_crank_overlap_mm3'] for x in checks)
report['moving_interface_check_scope']='C1 sampled every 30 degrees; all cylinders share these profiles. Full static accessory clash check and cam contact not included.'
report['checks_pass']=(ok and report['max_piston_block_overlap_mm3']<1e-4 and report['max_rod_crank_overlap_mm3']<1e-4)
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:report[k] for k in ['step_roundtrip','dimension_checks','max_piston_block_overlap_mm3','max_rod_crank_overlap_mm3','checks_pass']},indent=2))
if not report['checks_pass']:raise SystemExit('Moving interface intersection needs correction')
