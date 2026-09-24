"""Shared analytic mechanism. Millimetres, radians internally; no CAD dependency."""
import json
import math
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name('parameters.json').read_text())
def v(key): return CONFIG['verified'][key]['value']
def a(key): return CONFIG['assumed'][key]['value']
R = v('stroke') / 2
L = a('rod_length')
BANK = math.radians(a('bank_angle'))
FIRE = [0, 540, 180, 360]
DECK = R + L + a('pin_to_crown') + a('deck_gap')

def bank_point(p):
    x,y,z = p
    return (x, y*math.cos(BANK)-z*math.sin(BANK),
            y*math.sin(BANK)+z*math.cos(BANK)+a('crank_z'))

def cylinder_state(theta_deg, index):
    theta = math.radians(theta_deg - FIRE[index])
    x = a('cylinder_x0') + v('pitch') * index
    y,z = R*math.sin(theta), R*math.cos(theta)
    wrist = z + math.sqrt(L*L-y*y)
    rod_angle = math.atan2(y, wrist-z)
    cycle = (theta_deg - FIRE[index]) % 720
    def lift(start):
        t = (cycle-start)/180
        return a('valve_lift') * math.sin(math.pi*t)**2 if 0 < t < 1 else 0.0
    return dict(pin=bank_point((x,y,z)), wrist=bank_point((x,0,wrist)),
                wrist_local=wrist, rod_rx=math.degrees(BANK+rod_angle),
                intake=lift(360), exhaust=lift(180), cycle=cycle,
                phase=['POWER','EXHAUST','INTAKE','COMPRESSION'][int(cycle//180)])

def clearance_volume_mm3():
    return math.pi*(v('bore')/2)**2*v('stroke')/(v('compression_ratio')-1)

def validate():
    errors=[]; distance_err=0; sample=[]
    for angle in range(721):
        for i in range(4):
            s=cylinder_state(angle,i)
            d=math.dist(s['pin'],s['wrist'])
            distance_err=max(distance_err,abs(d-L))
            crown=s['wrist_local']+a('pin_to_crown')
            # Valve bottom is 1.2 mm above deck when seated.
            gap=DECK+1.2-max(s['intake'],s['exhaust'])-crown
            if gap < -1e-8: errors.append(f'Valve/piston axial clearance {angle} C{i+1}: {gap}')
        sample.append(cylinder_state(angle,0)['wrist_local'])
    stroke=max(sample)-min(sample)
    if abs(stroke-v('stroke'))>1e-8: errors.append('Stroke mismatch')
    if distance_err>1e-8: errors.append('Rod joint closure mismatch')
    return {'samples':721,'cylinders':4,'stroke_mm':stroke,
            'max_rod_joint_error_mm':distance_err,'valve_piston_axial_clearance_pass':not errors,
            'displacement_cm3_from_bore_stroke':math.pi*(v('bore')/2)**2*v('stroke')*4/1000,
            'clearance_volume_cm3_equivalent':clearance_volume_mm3()/1000,
            'gear_ratio':a('gear_teeth')[2]/a('gear_teeth')[0],
            'firing_sequence':[1,3,4,2], 'errors':errors,
            'scope':'Analytic joint closure and axial clearance under assumed rod and valve geometry; not exhaustive assembly collision or dynamics validation'}

if __name__=='__main__': print(json.dumps(validate(),indent=2))
