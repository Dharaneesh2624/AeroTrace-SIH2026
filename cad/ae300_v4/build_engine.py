"""Build AE300 R4 B-rep solids, CAD assembly, metadata and shared render meshes.

Run with .venv-cad/Scripts/python.exe. Only dimensions in parameters.json/verified
are documentary dimensions; all other shape construction is reconstruction.
"""
import csv
import json
import math
import time
from pathlib import Path
import occ as o
from kinematics import CONFIG, v, a, R, L, BANK, DECK, FIRE, bank_point, cylinder_state, clearance_volume_mm3, validate

from paths import OUT
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'parts').mkdir(exist_ok=True)
PARTS=[]; SENSORS=[]
PALETTE={'iron':(0.17,0.19,0.21),'alloy':(0.56,0.61,0.65),'steel':(0.32,0.37,0.42),
         'black':(0.055,0.065,0.08),'blue':(0.12,0.37,0.56),'gold':(0.65,0.44,0.13),
         'fuel':(0.19,0.55,0.48),'coolant':(0.035,0.48,0.65),'exhaust':(0.39,0.28,0.22),
         'sensor':(0.95,0.37,0.065),'sih':(0.66,0.22,0.85)}
X=[a('cylinder_x0')+i*v('pitch') for i in range(4)]

def add(name,shape,group,mat='alloy',pos=(0,0,0),rx=0,motion=None,source='Reconstructed geometry; dimensions not OEM',section=False):
    if not o.valid(shape) or o.solid_count(shape)!=1 or o.volume(shape)<=0:
        raise ValueError('Invalid solid: '+name)
    p=dict(name=name,shape=shape,world=o.move(shape,pos,rx),group=group,color=PALETTE[mat],
           pos=list(pos),rx=rx,motion=motion,source=source,section=section)
    PARTS.append(p);return p

def bank(name,shape,group,mat='alloy',**kw):
    return add(name,shape,group,mat,pos=(0,0,a('crank_z')),rx=a('bank_angle'),**kw)

def bolt_pattern(prefix,points,axis=(0,0,1),r=4,h=7,group='Fasteners',banked=False):
    for i,p in enumerate(points):
        shape=o.cyl(r,h,p,axis)
        (bank if banked else add)(f'{prefix}_{i+1:02}',shape,group,'steel')

def flange(ro,ri,h,axis=(1,0,0)):
    return o.cut(o.cyl(ro,h,axis=axis),o.cyl(ri,h+2,(0,0,-1),axis)) if axis==(0,0,1) else o.cut(o.cyl(ro,h,axis=axis),o.cyl(ri,h+2,(-1,0,0),axis))

def build_block():
    print('Building drilled crankcase and cylinder head',flush=True)
    shell=o.rounded_xy(448,170,280,16,(405,0,87))
    shell=o.cut(shell,o.box(422,146,141,(405,0,-6)))
    shell=o.cut(shell,o.cyl(25.3,452,(179,0,0),(1,0,0)))
    for x in X:
        shell=o.cut(shell,o.cyl(v('bore')/2,200,(x,0,45)))
        # Two abstract jacket passages, not a claim of OEM passage geometry.
        for y in [-61,61]:shell=o.cut(shell,o.cyl(6,178,(x,y,52)))
    # Five main bearing bores through cap pads represented in separate solids below.
    bank('Crankcase_4x83mm_Bores',shell,'01_Housings','iron',section=True,
         source='MM01-9/01-12: 83 mm bores, 90 mm pitch, cast iron, no separate cylinder liners. Exterior and coolant paths reconstructed.')
    for j,x in enumerate([225,315,405,495,585]):
        cap=o.cut(o.box(17,116,38,(x,0,-14)),o.cyl(25.3,20,(x-10,0,0),(1,0,0)))
        bank(f'Main_Bearing_Cap_{j+1}',cap,'02_Cranktrain','iron')
        bearing=o.cut(o.cyl(28,16,(x-8,0,0),(1,0,0)),o.cyl(25.15,18,(x-9,0,0),(1,0,0)))
        bank(f'Main_Bearing_{j+1}',bearing,'02_Cranktrain','gold',source='MM01-11 five mains; journal diameters assumed')
    sump=o.rounded_xy(435,188,86,19,(405,0,-101))
    sump=o.cut(sump,o.rounded_xy(422,175,89,14,(405,0,-90)))
    bank('Wet_Oil_Sump',sump,'01_Housings','gold',section=True)
    # Flanged joint with through holes and matching screw heads.
    sump_rim=o.cut(o.rounded_xy(450,205,8,16,(405,0,-61)),o.box(416,162,12,(405,0,-61)))
    bank('Sump_Rim',sump_rim,'01_Housings','alloy',section=True)
    for xx in range(215,620,45):
        for yy in [-92,92]:
            bank(f'Sump_Screw_{xx}_{yy}',o.cyl(4,8,(xx,yy,-65)),'Fasteners','steel')
    head=o.rounded_xy(444,190,100,15,(405,0,DECK+50))
    head=o.cut(head,o.box(426,164,47,(405,0,DECK+81.5)))
    for yy in [-30,30]:head=o.cut(head,o.cyl(9.3,448,(181,yy,DECK+80),(1,0,0)))
    for x in X:
        head=o.cut(head,o.cyl(6,108,(x,0,DECK-1)))
        for dx in [-16,16]:
            for y in [-17,17]:
                head=o.cut(head,o.cyl(3.8,105,(x+dx,y,DECK-1)),o.cyl(11.5,6,(x+dx,y,DECK-1)),
                    o.cyl(5.6,37,(x+dx,y,DECK+24)),o.cyl(9.2,66,(x+dx,y,DECK+40)))
        head=o.cut(head,o.cyl(3.7,75,(x+10,6,DECK+11)))
        # Abstract inlet/exhaust port pairs terminating at the valve areas.
        for y in [-1,1]:head=o.cut(head,o.cyl(15,80,(x,100*y,DECK+22),(0,-y,0)))
    bank('Cylinder_Head_16Valve_Injector_Ports',head,'01_Housings','alloy',section=True,
         source='MM01-12 aluminium head, 16 valves, central direct injectors; ports/seats reconstructed')
    cover=o.rounded_xy(439,190,39,17,(405,0,DECK+124))
    cover=o.cut(cover,o.rounded_xy(428,179,42,13,(405,0,DECK+116)))
    bank('DOHC_Cover',cover,'01_Housings','blue',section=True)
    for x in X:
        bank(f'Cover_Rib_{x}',o.box(8,182,6,(x,0,DECK+146)),'01_Housings','blue',section=True)
    bolt_pattern('HeadCover_Screw',[(xx,yy,DECK+145) for xx in [203,270,360,450,540,608] for yy in [-80,80]],banked=True)

def build_cranktrain():
    print('Building crank throws, ringed pistons and closed rods',flush=True)
    pieces=[]
    for i,x in enumerate(X):
        phase=-math.radians(FIRE[i]);yy=R*math.sin(phase);zz=R*math.cos(phase)
        pieces.append(o.cyl(23,34,(x-17,yy,zz),(1,0,0)))
        for sx in [-1,1]:
            xx=x+sx*24
            web=o.fuse(o.cyl(35,16,(xx-8,0,0),(1,0,0)),o.cyl(29,16,(xx-8,yy,zz),(1,0,0)),
                       o.box(16,45,abs(zz)+10,(xx,yy/2,zz/2)))
            # Counterweight opposite each throw.
            web=o.fuse(web,o.cyl(39,16,(xx-8,-yy,-zz*0.65),(1,0,0)))
            pieces.append(web)
    for left,right in [(185,239),(301,329),(391,419),(481,509),(571,650)]:
        pieces.append(o.cyl(25,right-left,(left,0,0),(1,0,0)))
    crank=o.fuse(*pieces)
    bank('Crankshaft_4Throws_5Mains',crank,'02_Cranktrain','steel',motion={'kind':'crank'},
         source='92 mm stroke fixes 46 mm throw. Journals, counterweights, oil holes assumed; MM Fig01-7 reference.')
    for i,x in enumerate(X):
        s=cylinder_state(0,i)
        pr=a('piston_diameter')/2
        piston=o.cyl(pr,55,(0,0,-23))
        piston=o.cut(piston,o.cyl(34,40,(0,0,-24)))
        bowl_depth=(clearance_volume_mm3()-math.pi*(v('bore')/2)**2*a('deck_gap'))/(math.pi*20**2)
        piston=o.cut(piston,o.cyl(20,bowl_depth+1,(0,0,32-bowl_depth)),o.cyl(10.12,100,(-50,0,0),(1,0,0)))
        for z in [21,25,29]:
            piston=o.cut(piston,o.cut(o.cyl(42,1.5,(0,0,z)),o.cyl(pr-1.6,2,(0,0,z-.2))))
        add(f'Piston_C{i+1}',piston,'02_Cranktrain','alloy',s['wrist'],a('bank_angle'),{'kind':'piston','cylinder':i},
            '83 mm bore / 92 mm stroke. Diameter clearance, crown and pin size assumed; equivalent bowl volume matches 17.5:1.')
        for j,z in enumerate([21,25,29]):
            ring=o.cut(o.cyl(pr+0.045,1.2,(0,0,z+.15)),o.cyl(pr-1.4,1.6,(0,0,z)))
            ring=o.cut(ring,o.box(1.2,8,3,(0,pr,z+.5)))
            add(f'Piston_Ring_C{i+1}_{j+1}',ring,'02_Cranktrain','steel',s['wrist'],a('bank_angle'),{'kind':'piston','cylinder':i})
        pin=o.cut(o.cyl(10,70,(-35,0,0),(1,0,0)),o.cyl(5.5,72,(-36,0,0),(1,0,0)))
        add(f'Wrist_Pin_C{i+1}',pin,'02_Cranktrain','steel',s['wrist'],a('bank_angle'),{'kind':'piston','cylinder':i})
        big=o.cut(o.cyl(29,25,(-12.5,0,0),(1,0,0)),o.cyl(23.2,27,(-13.5,0,0),(1,0,0)))
        small=o.cut(o.cyl(15,22,(-11,0,L),(1,0,0)),o.cyl(10.12,24,(-12,0,L),(1,0,0)))
        web=o.extrude([(-7,-12,23),(-7,12,23),(-7,8,L-10),(-7,-8,L-10)],(14,0,0))
        rod=o.fuse(big,small,web)
        # Recesses create a visible I-section without severing either eye.
        rod=o.cut(rod,o.box(6,9,L-60,(-6,0,(L+10)/2)),o.box(6,9,L-60,(6,0,(L+10)/2)))
        add(f'Connecting_Rod_C{i+1}',rod,'02_Cranktrain','steel',s['pin'],s['rod_rx'],{'kind':'rod','cylinder':i},
            '147 mm joint-to-joint length is assumed; analytic slider-crank constraint preserves it at all frames')
    # Two separate damper masses and spring pockets.
    for j,xx in enumerate([157,175]):
        disk=o.cut(o.cyl(83,14,(xx,0,0),(1,0,0)),o.cyl(26,16,(xx-1,0,0),(1,0,0)))
        hub=o.cut(o.cyl(30,14,(xx,0,0),(1,0,0)),o.cyl(15.9,16,(xx-1,0,0),(1,0,0)))
        disk=o.fuse(disk,hub)
        for k in range(6):
            t=k*math.tau/6; disk=o.cut(disk,o.cyl(13,16,(xx-1,54*math.cos(t),54*math.sin(t)),(1,0,0)))
        bank(f'TVD_Mass_{j+1}',disk,'02_Cranktrain','steel',motion={'kind':'crank'},source='MM01-11 two-mass torsional damper; dimensions and stiffness undisclosed')

def involute_gear(teeth,module,width,bore_radius=16):
    rp=teeth*module/2;rb=rp*math.cos(math.radians(a('pressure_angle')));ra=rp+module;rf=rp-1.25*module
    inv=lambda rr: math.sqrt(max(0,(rr/rb)**2-1))-math.acos(min(1,rb/rr))
    hp=math.pi/(2*teeth); ip=inv(rp);points=[]
    for i in range(teeth):
        centre=math.tau*i/teeth
        flank=[]
        for k in range(5):
            rr=max(rb,rf)+(ra-max(rb,rf))*k/4
            half=hp+ip-inv(rr);flank.append((rr,half))
        candidates=[(rf,-math.pi/teeth),(rf,-flank[0][1])]
        candidates += [(rr,-hh) for rr,hh in flank]
        candidates += [(rr,hh) for rr,hh in reversed(flank)]
        candidates += [(rf,flank[0][1]),(rf,math.pi/teeth-1e-6)]
        for rr,ang in candidates:points.append((0,rr*math.cos(centre+ang),rr*math.sin(centre+ang)))
    return o.cut(o.extrude(points,(width,0,0)),o.cyl(bore_radius,width+2,(-1,0,0),(1,0,0)))

def build_gearbox():
    print('Building offset reduction gearbox and involute gears',flush=True)
    n1,n2,n3=a('gear_teeth');mod=a('gear_module');z1=a('crank_z');z2=-(n2+n3)*mod/2
    for name,n,z,ratio,phase in [('Input',n1,z1,1,90),('Idler',n2,z2,-n1/n2,-90+180/n2),('Output',n3,0,1/v('gear_ratio'),-90)]:
        gear=involute_gear(n,mod,24)
        add(f'Gear_{name}_{n}T',gear,'03_Reduction','steel',pos=(68,0,z),rx=phase,
            motion={'kind':'gear','ratio':ratio,'phase':phase},source='3 gears and 1.69 ratio documented. Tooth counts, module and spur profile are demonstration geometry; OEM gears are helical.')
        shaft=o.cyl(15.7,180 if name=='Input' else 115,(5,0,z),(1,0,0))
        add(f'Shaft_{name}',shaft,'03_Reduction','steel',motion={'kind':'shaft','ratio':ratio,'pivot':[0,0,z]})
    outline=[(-84,95),(-123,62),(-137,10),(-121,-116),(-99,-238),(-54,-290),(28,-301),(83,-266),(111,-180),(123,-44),(104,59),(51,107)]
    shell=o.extrude([(25,y,z) for y,z in outline],(128,0,0))
    inner=[(y*.88,(z+85)*.94-85) for y,z in outline]
    shell=o.cut(shell,o.extrude([(32,y,z) for y,z in inner],(115,0,0)),o.cyl(30,145,(20,0,0),(1,0,0)))
    for zz in [z1,z2]:shell=o.cut(shell,o.cyl(16.2,145,(20,0,zz),(1,0,0)))
    add('Gearbox_Cast_Case',shell,'01_Housings','iron',section=True,source='MM Fig01-6 and IM Fig4.4.1 outline reference; contour/centre distances reconstructed')
    rim=o.cut(o.extrude([(149,y*1.025,(z+85)*1.02-85) for y,z in outline],(9,0,0)),o.extrude([(148,y,z) for y,z in inner],(12,0,0)))
    add('Gearbox_Rear_Rim',rim,'01_Housings','alloy',section=True)
    bolt_pattern('Gearcase_Screw',[(20,y*.93,(z+85)*.94-85) for y,z in outline],axis=(1,0,0),r=5.5,h=8)
    flange_shape=o.cut(o.cyl(v('flange_outer_diameter')/2,12,(0,0,0),(1,0,0)),o.cyl(27,14,(-1,0,0),(1,0,0)))
    flange_hub=o.cut(o.cyl(35,17,(8,0,0),(1,0,0)),o.cyl(15.9,19,(7,0,0),(1,0,0)))
    flange_shape=o.fuse(flange_shape,flange_hub)
    for i in range(6):
        ang=i*math.tau/6;flange_shape=o.cut(flange_shape,o.cyl(v('flange_hole_diameter')/2,14,(-1,v('flange_pcd')/2*math.cos(ang),v('flange_pcd')/2*math.sin(ang)),(1,0,0)))
    add('Propeller_Flange_6x12_75_PCD101_6',flange_shape,'03_Reduction','alloy',motion={'kind':'gear','ratio':1/v('gear_ratio'),'phase':0},source='IM15.4 six 12.75 holes on 101.6 PCD; rim and centre bore reconstructed')
    add('Governor_Interface',o.cyl(29,68,(105,0,95)),'04_Accessories','alloy',source='Governor location/type interface from MM01-10; aircraft governor envelope schematic')
    add('Governor_Setpoint_Motor',o.cyl(14,48,(105,36,128),(0,1,0)),'04_Accessories','black')
    # Source datum coordinates have no arbitrary Z offset.
    for name,p in zip(['Front_Left','Front_Right','Rear_Left','Rear_Right'],v('mounts')):
        dx,dy=(60,50) if name=='Front_Left' else (60,60)
        pad=o.box(dx+22,dy+22,12)
        pad=o.cut(pad,o.cyl(13,14,(0,0,-7)))
        for sx in [-1,1]:
            for sy in [-1,1]:pad=o.cut(pad,o.cyl(4.5,14,(sx*dx/2,sy*dy/2,-7)))
        add('Mount_'+name,pad,'05_Installation','alloy',p,source='IM Table6.1 datum position verified; rear pad/hole shapes reconstructed')
        # Clearly schematic support arm, not a certified engine mounting bracket.
        anchor=(185 if 'Front' in name else 612, -90 if p[1]<0 else 75,-160)
        add('Mount_Support_'+name,o.pipe([anchor,p],11),'05_Installation','iron')

def build_valvetrain():
    print('Building 16-valve train, cams and timing drive',flush=True)
    spring=o.coil(7,1.0,22,5)
    cam_height=DECK+80
    for side in [-1,1]:
        components=[o.cyl(9,478,(186,side*30,cam_height),(1,0,0))]
        for i,x in enumerate(X):
            for dx in [-16,16]:
                # Lobe is an explicit approximate profile; follower lift follows ideal cycle law.
                kind='intake' if (dx*side)<0 else 'exhaust'
                angle=(FIRE[i]+(450 if kind=='intake' else 270))/2
                theta=math.radians(angle)
                components.append(o.cyl(13,10,(x+dx-5,side*30+4*math.sin(theta),cam_height+4*math.cos(theta)),(1,0,0)))
        bank('Camshaft_'+('ChainDriven' if side==-1 else 'GearDriven'),o.fuse(*components),'06_Valvetrain','steel',
             motion={'kind':'cam','side':side,'pivot':list(bank_point((0,side*30,cam_height)))},source='MM01-12: each cam drives 1 intake + 1 exhaust per cylinder; lobe shapes approximate')
    for i,x in enumerate(X):
        for j,(dx,y) in enumerate([(-16,-17),(16,-17),(-16,17),(16,17)]):
            kind='intake' if dx*y<0 else 'exhaust'
            valve=o.fuse(o.cyl(a('valve_head_radius'),3,(0,0,0)),o.cyl(3.45,73,(0,0,2)))
            pos=bank_point((x+dx,y,DECK+1.2))
            add(f'Valve_C{i+1}_{kind}_{j+1}',valve,'06_Valvetrain','steel',pos,a('bank_angle'),{'kind':'valve','cylinder':i,'type':kind,'base':list(pos)},source='16 valves documented; sizes/lift/seat arrangement reconstruction')
            bank(f'Valve_Guide_C{i+1}_{j+1}',o.cut(o.cyl(5.5,36,(x+dx,y,DECK+24)),o.cyl(3.65,38,(x+dx,y,DECK+23))),'06_Valvetrain','gold')
            mo={'kind':'valve','cylinder':i,'type':kind}
            sp=bank_point((x+dx,y,DECK+42))
            add(f'Valve_Spring_C{i+1}_{j+1}',spring,'06_Valvetrain','steel',sp,a('bank_angle'),
                mo|{'kind':'spring','base':list(sp),'free_height':22},source='Generic 22 mm spring; animated axial compression, not a stress or contact solution')
            for label,z,ro,ri in [('Spring_Seat',40,9,5.6),('Spring_Retainer',64,9,3.5)]:
                pp=bank_point((x+dx,y,DECK+z))
                shape=o.cut(o.cyl(ro,2),o.cyl(ri,4,(0,0,-1)))
                add(f'{label}_C{i+1}_{j+1}',shape,'06_Valvetrain','steel',pp,a('bank_angle'),
                    mo|{'base':list(pp)} if label=='Spring_Retainer' else None)
            fp=bank_point((x+dx,y,DECK+77))
            add(f'Follower_C{i+1}_{j+1}',o.box(11,23,5),'06_Valvetrain','alloy',fp,a('bank_angle'),mo|{'base':list(fp)},
                source='Prescribed translating follower proxy; actual hydraulic roller contact not solved')
    for side in [-1,1]:
        for idx,xx in enumerate([205,315,405,495,602]):
            cap=o.cut(o.box(16,29,21,(xx,side*30,cam_height+4)),o.cyl(9.2,18,(xx-9,side*30,cam_height),(1,0,0)))
            bank(f'Cam_Bearing_Cap_{side}_{idx}',cap,'06_Valvetrain','alloy',section=True)
            bolt_pattern(f'CamCap_Bolt_{side}_{idx}',[(xx,side*30+yy,cam_height+15) for yy in [-11,11]],r=2.5,h=4,banked=True)
    # Chain drive goes to only one cam; opposite cam receives direct gear.
    for y in [-30,30]:
        gear=involute_gear(24,2.5,11,bore_radius=9.15)
        gear=o.fuse(gear,o.cut(o.cyl(12,25,(-12,0,0),(1,0,0)),o.cyl(9.15,27,(-13,0,0),(1,0,0))))
        gear=o.move(gear,(636,y,cam_height),0 if y<0 else 7.5)
        bank(f'Cam_DriveGear_{y}_24T',gear,'06_Valvetrain','steel',
             motion={'kind':'cam','side':-1 if y<0 else 1},source='Direct 1:1 counter-rotation verified; 24 teeth/module 2.5 assumed')
    # Conceptual chain sprockets; the 20:40 count reproduces half crank speed.
    for label,n,yy,zz,mo in [('Crank',20,0,0,{'kind':'crank'}),('Cam',40,-30,cam_height,{'kind':'cam','side':-1})]:
        pr=5/(2*math.sin(math.pi/n))
        shape=o.cut(o.cyl(pr+1.1,12,(650,yy,zz),(1,0,0)),o.cyl(9.15,14,(649,yy,zz),(1,0,0)))
        for j in range(n):
            ang=j*math.tau/n
            shape=o.cut(shape,o.cyl(1.75,14,(649,yy+pr*math.cos(ang),zz+pr*math.sin(ang)),(1,0,0)))
        bank(f'Timing_Sprocket_{label}_{n}T',shape,'06_Valvetrain','steel',motion=mo,
             source='20:40 sprocket topology; 5 mm pitch and tooth cuts assumed, chain engagement not validated')
    chain_pts=[(655,0,-23),(655,-55,30),(655,-67,cam_height),(655,-30,cam_height+38),(655,7,cam_height),(655,30,15),(655,0,-23)]
    for off in [-3.5,3.5]:
        bank(f'Double_Timing_Chain_{off}',o.pipe([(x+off,y,z) for x,y,z in chain_pts],2.5),'06_Valvetrain','steel',source='Double-chain path schematic; sprocket pitch and chain motion not modelled')
    for yy,z0,z1 in [(-62,40,cam_height-25),(21,25,cam_height-35)]:
        bank(f'Timing_Guide_{yy}',o.pipe([(655,yy,z0),(655,yy,z1)],5),'06_Valvetrain','black')
    bank('Chain_Tensioner_Concept',o.cyl(12,40,(655,24,150),(0,1,0)),'06_Valvetrain','alloy')

def build_systems():
    print('Building fuel, turbo, cooling and accessories',flush=True)
    # Bankside plenums and separate hollow runners.
    for y,mat,label in [(-119,'blue','Intake'),(119,'exhaust','Exhaust')]:
        plenum=o.rounded_xy(345,60,55,12,(410,y,DECK+35))
        plenum=o.cut(plenum,o.box(335,48,43,(410,y,DECK+35)))
        bank(label+'_Plenum',plenum,'07_Air_Exhaust',mat)
        for i,x in enumerate(X):
            bank(f'{label}_Runner_C{i+1}',o.pipe([(x,y,DECK+35),(x,y*.68,DECK+22),(x,y*.5,DECK+22)],19,15),'07_Air_Exhaust',mat)
    rail=o.cut(o.cyl(15,390,(210,-76,DECK+113),(1,0,0)),o.cyl(7,392,(209,-76,DECK+113),(1,0,0)))
    bank('HighPressure_Common_Rail',rail,'08_Fuel','fuel')
    for i,x in enumerate(X):
        injector=o.fuse(o.cyl(5.4,110,(x,0,DECK-4)),o.cyl(10,54,(x,0,DECK+63)),o.box(23,20,21,(x,0,DECK+126)))
        bank(f'Injector_C{i+1}',injector,'08_Fuel','steel',source='MM01-12/15 central direct injection; injector shape/nozzle internal geometry unknown')
        bank(f'Injection_Pipe_C{i+1}',o.pipe([(x,-76,DECK+113),(x-15,-35,DECK+135),(x,0,DECK+107)],3.5,2),'08_Fuel','steel')
        bank(f'Glow_Plug_C{i+1}',o.cyl(3.5,70,(x+10,6,DECK+12)),'08_Fuel','gold')
    bank('HighPressure_Pump',o.fuse(o.cyl(37,63,(640,30,137),(1,0,0)),o.box(55,85,68,(659,30,137))),'08_Fuel','alloy')
    bank('Fuel_Metering_Unit',o.cyl(15,45,(657,75,150),(0,1,0)),'08_Fuel','black')
    bank('Rail_Pressure_Control_Valve',o.cyl(14,42,(204,-76,DECK+113),(1,0,0)),'08_Fuel','black')
    # Detailed turbo envelopes: hollow toroids with connected ducts; no claimed impeller aerofoil.
    tpos=bank_point((608,-205,DECK+30))
    for xx,mat,label in [(-40,'alloy','Compressor'),(38,'exhaust','Turbine')]:
        volute=o.cut(o.torus(43,22,axis=(1,0,0)),o.torus(43,16,axis=(1,0,0)))
        add('Turbo_'+label+'_Volute',volute,'07_Air_Exhaust',mat,(tpos[0]+xx,tpos[1],tpos[2]))
    add('Turbo_Bearing_Core',o.cyl(24,95,(tpos[0]-45,tpos[1],tpos[2]),(1,0,0)),'07_Air_Exhaust','steel')
    add('Turbo_Inlet_60_4_ID',o.cut(o.cyl(35,36,(tpos[0]-76,tpos[1],tpos[2]),(1,0,0)),o.cyl(30.2,38,(tpos[0]-77,tpos[1],tpos[2]),(1,0,0))),'07_Air_Exhaust','alloy',source='IM8.4.1 60.4 ID / 70 OD; placement reconstructed')
    add('Wastegate_Actuator',o.cyl(24,40,(tpos[0]+15,tpos[1]+38,tpos[2]+52),(1,0,0)),'07_Air_Exhaust','gold')
    add('Wastegate_Link',o.pipe([(tpos[0]+55,tpos[1]+38,tpos[2]+52),(tpos[0]+73,tpos[1]+10,tpos[2])],3),'07_Air_Exhaust','steel')
    # Rear belt accessories. Pulleys, vents, mounting ears and hose ports.
    for label,loc,r,h in [('Alternator',(582,129,-202),57,98),('Water_Pump',(624,-84,-83),39,42),('Starter',(205,142,-114),37,155)]:
        housing=o.cut(o.cyl(r,h,loc,(1,0,0)),o.cyl(r-7,h-12,(loc[0]+6,loc[1],loc[2]),(1,0,0)))
        if label!='Starter':housing=o.cut(housing,o.cyl(7.2,h+2,(loc[0]-1,loc[1],loc[2]),(1,0,0)))
        add(label+'_Housing',housing,'04_Accessories','alloy')
        cap=o.cyl(r-2,8,(loc[0]-3,loc[1],loc[2]),(1,0,0))
        if label!='Starter':cap=o.cut(cap,o.cyl(7.2,10,(loc[0]-4,loc[1],loc[2]),(1,0,0)))
        add(label+'_Endcap',cap,'04_Accessories','black')
        if label!='Starter':
            radius=26 if label=='Alternator' else 32
            pulley=o.cut(o.cyl(radius,12,(680,loc[1],loc[2]),(1,0,0)),o.cyl(7.2,14,(679,loc[1],loc[2]),(1,0,0)))
            for j in range(6):
                t=j*math.tau/6
                pulley=o.cut(pulley,o.cyl(3,14,(679,loc[1]+radius*.63*math.cos(t),loc[2]+radius*.63*math.sin(t)),(1,0,0)))
            mo={'kind':'shaft','ratio':46/radius,'pivot':[0,loc[1],loc[2]]}
            add(label+'_Pulley',pulley,'04_Accessories','steel',motion=mo,source='Illustrative belt drive ratio from assumed pulley radii; not OEM accessory RPM')
            add(label+'_Rotor_Shaft',o.cyl(7,692-loc[0],loc,(1,0,0)),'04_Accessories','steel',motion=mo)
        else:
            add('Starter_Pinion_Parked',o.move(involute_gear(14,1.5,12,bore_radius=4),(loc[0]+h,loc[1],loc[2])),'04_Accessories','steel',source='Starter is parked, not continuously driven; clutch/engagement mechanism schematic')
            add('Starter_Solenoid',o.cyl(18,62,(loc[0]+50,loc[1]+45,loc[2]),(1,0,0)),'04_Accessories','black')
        for k in range(8):
            t=k*math.tau/8;add(f'{label}_TieRod_{k}',o.cyl(2.5,h,(loc[0],loc[1]+(r-4)*math.cos(t),loc[2]+(r-4)*math.sin(t)),(1,0,0)),'Fasteners','steel')
    pulley=o.cut(o.cyl(46,12,(680,0,a('crank_z')),(1,0,0)),o.cyl(9.2,14,(679,0,a('crank_z')),(1,0,0)))
    add('Crank_Accessory_Pulley',pulley,'04_Accessories','steel',motion={'kind':'shaft','ratio':1,'pivot':[0,0,a('crank_z')]})
    add('Rear_Crank_Extension_Concept',o.cyl(9,42,(650,0,a('crank_z')),(1,0,0)),'04_Accessories','steel',motion={'kind':'shaft','ratio':1,'pivot':[0,0,a('crank_z')]})
    belt=[(686,0,a('crank_z')-47),(686,151,-216),(686,151,-187),(686,-65,-57),(686,-108,-61),(686,-108,-103),(686,0,a('crank_z')-47)]
    add('Rear_Accessory_Belt_Path',o.pipe(belt,4),'04_Accessories','black',source='MM01-12 rear V-ribbed drive topology; belt section/path approximate and static')
    for label,loc,r,h,mat in [('Oil_Filter',(521,71,-28),32,115,'alloy'),('Oil_Cooler',(414,92,-111),30,85,'alloy'),('Thermostat',(564,-61,-55),24,55,'coolant')]:
        add(label,o.cyl(r,h,loc),'09_Fluids',mat)
        add(label+'_Cap',o.cyl(r+2,8,(loc[0],loc[1],loc[2]+h)),'09_Fluids','black')
    add('Coolant_Hose',o.pipe([(645,-84,-83),(565,-60,-55),(480,-20,-52),(270,-35,-60)],17,13),'09_Fluids','coolant')
    add('Oil_Filter_Feed',o.pipe([(500,85,-240),(520,70,-180),(521,71,-28)],7,4.5),'09_Fluids','gold')

def build_connections():
    """External routing concepts, not assertions of OEM hydraulic passages."""
    print('Adding service lines and separable aircraft integration circuits',flush=True)
    route_source='System topology concept only; endpoints, bend radii and clearance require OEM/test-rig verification; no fluid solution'
    # Engine-mounted pipework. Deliberately external and separately selectable.
    engine_routes=[
        ('Pump_to_Common_Rail',[bank_point((685,30,157)),bank_point((709,-40,DECK+113)),bank_point((599,-76,DECK+113))],4.5,2.5,'08_Fuel','steel'),
        ('Injector_Leakoff_Return',[bank_point((235,10,DECK+126)),bank_point((575,10,DECK+126)),bank_point((689,95,145))],4,2.5,'08_Fuel','fuel'),
        ('Oil_Cooler_to_Filter',[(414,92,-111),(463,102,-70),(521,71,-28)],8,5,'09_Fluids','gold'),
        ('Crankcase_Breather',[bank_point((598,48,DECK+134)),bank_point((670,83,DECK+134)),(704,91,-50)],8,5.5,'09_Fluids','black'),
    ]
    for name,pts,ro,ri,group,mat in engine_routes:add(name,o.pipe(pts,ro,ri),group,mat,source=route_source)
    tp=bank_point((608,-205,DECK+30))
    routes=[
        ('Exhaust_Collector_to_Turbine',[bank_point((582,119,DECK+35)),(711,24,70),(711,-218,87),(tp[0]+38,tp[1]+43,tp[2])],21,17,'exhaust'),
        ('Compressor_to_Intercooler',[(tp[0]-40,tp[1]-43,tp[2]),(713,-412,22),(815,-366,22)],22,18,'blue'),
        ('Intercooler_to_Intake',[(815,-282,95),(750,-230,120),bank_point((581,-119,DECK+35))],22,18,'blue'),
        ('Radiator_Hot_Return',[(564,-61,0),(753,-36,24),(883,-70,-3)],17,13,'coolant'),
        ('Radiator_Cooled_Supply',[(883,73,-190),(750,42,-233),(645,-84,-83)],17,13,'coolant'),
        ('External_Fuel_Supply',[(750,65,-68),(704,65,-68),bank_point((691,83,145))],6,4,'fuel'),
        ('External_Fuel_Return',[bank_point((689,95,145)),(730,110,-78),(754,110,-78)],5,3,'fuel'),
    ]
    for name,pts,ro,ri,mat in routes:add(name,o.pipe(pts,ro,ri),'13_Routing_Concepts',mat,source=route_source)
    # Schematic water pump impeller, separate from its housing for inspection.
    loc=(632,-84,-83)
    rotor=[o.cyl(23,4,loc,(1,0,0)),o.cyl(9,22,(627,loc[1],loc[2]),(1,0,0))]
    for i in range(8):
        blade=o.box(9,18,2,(638,13,0))
        rotor.append(o.move(blade,(0,loc[1],loc[2]),i*45))
    impeller=o.cut(o.fuse(*rotor),o.cyl(7.15,25,(626,loc[1],loc[2]),(1,0,0)))
    add('Water_Pump_Impeller_Concept',impeller,'04_Accessories','alloy',motion={'kind':'shaft','ratio':46/32,'pivot':[0,loc[1],loc[2]]},
        source='Generic eight-vane demonstration, not AE300 hydraulically qualified impeller')

def sensor(name,loc,signal,unit,category='OEM',source='MM01-24/25 sensor inventory; proposed CAD location',axis=(0,0,1),channel=None,host=None):
    from details import sensor_geometry
    boss,stem,family=sensor_geometry(name)
    group='10_OEM_Sensors' if category=='OEM' else '11_SIH_Additions'
    mat='sensor' if category=='OEM' else 'sih'
    add('Boss_'+name,o.orient(boss,axis),group,'alloy',loc,source=source)
    add('Sensor_'+name,o.orient(stem,axis),group,mat,loc,source=source)
    SENSORS.append(dict(id=name,object='Sensor_'+name,signal=signal,unit=unit,category=category,position_mm=loc,
                        axis=axis,source=source,telemetry_channel=channel,host=host,
                        family=family,geometry_status='Family-specific reconstructed envelope; exact OEM dimensions and threads unavailable'))

def build_sensors():
    print('Building OEM sensor locations and SIH instrumentation concepts',flush=True)
    for index in [1,2]:
        x=290 if index==1 else 500
        sensor(f'BPS{index}',bank_point((x,-134,DECK+45)),'boost_pressure','hPa',channel=800,host='Intake_Plenum')
        sensor(f'IAT{index}',bank_point((x+22,-134,DECK+45)),'intake_air_temperature','degC',channel=807,host='Intake_Plenum')
        sensor(f'CRS{index}',(641,index*24-36,a('crank_z')+29),'crankshaft_speed','rpm',host='Crankcase_4x83mm_Bores')
        sensor(f'CAS{index}',bank_point((620,-30 if index==1 else 30,DECK+80)),'camshaft_phase','deg',host='Cylinder_Head_16Valve_Injector_Ports',axis=(1,0,0))
    for name,p,signal,unit,ch,host in [
        ('RPS',bank_point((595,-76,DECK+113)),'rail_pressure','bar',804,'HighPressure_Common_Rail'),
        ('FPS',(670,60,-80),'fuel_supply_pressure','hPa',809,'HighPressure_Pump'),
        ('FTS',(648,63,-80),'fuel_temperature','degC',None,'HighPressure_Pump'),
        ('CTS',bank_point((530,70,DECK-5)),'coolant_temperature','degC',806,'Crankcase_4x83mm_Bores'),
        ('OPS',(490,79,-119),'engine_oil_pressure','hPa',803,'Oil_Cooler'),
        ('MOK',bank_point((427,88,-108)),'oil_temperature_and_level','degC/mm','811/814','Wet_Oil_Sump'),
        ('GBTS',(137,95,-160),'gearbox_oil_temperature','degC',810,'Gearbox_Cast_Case')]:
        sensor(name,p,signal,unit,channel=ch,host=host)
    # Required SIH measurements unavailable in the base 16-channel .ae3 recorder.
    for i,x in enumerate(X):
        sensor(f'EGT_C{i+1}',bank_point((x,121,DECK+52)),'exhaust_temperature','degC','SIH',host=f'Exhaust_Runner_C{i+1}')
        sensor(f'CHT_C{i+1}',bank_point((x,69,DECK+50)),'head_metal_temperature','degC','SIH',host='Cylinder_Head_16Valve_Injector_Ports')
    for name,p in [('VIB_Block',bank_point((398,84,75))),('VIB_Gearbox',(95,105,-112))]:
        bracket=o.cut(o.box(32,26,5),o.cyl(2.8,7,(-11,0,-4)),o.cyl(2.8,7,(11,0,-4)))
        add('Bracket_'+name,bracket,'11_SIH_Additions','sih',p)
        sensor(name,p,'vibration_xyz','m/s2','SIH',host='Crankcase_4x83mm_Bores' if 'Block' in name else 'Gearbox_Cast_Case')
    sensor('FuelFlow',(708,65,-68),'fuel_flow','L/h','SIH',host='fuel_supply_external')
    sensor('Alternator_Current',(650,179,-186),'alternator_current','A','SIH',host='Alternator_Housing')
    sensor('CTS_GPC',(561,-44,-4),'glow_control_coolant_temperature','degC',host='Thermostat',source='MM71-5/PDF109 B50/6 CTS_GPC; missing in R3, generic temperature probe shape')

def integration():
    # Externally mounted avionics and cooling are independently hideable.
    from details import build_eecu
    build_eecu(globals())
    for i in [1,2]:sensor(f'PLS{i}',(828,345+i*28,-65),'power_lever_position','percent',channel=805,host='aircraft_power_lever')
    add('Intercooler_Core',o.box(160,95,175),'12_Aircraft_Integration','alloy',(815,-325,40))
    for i in range(16):add(f'Intercooler_Fin_{i+1}',o.box(159,102,1.5),'12_Aircraft_Integration','steel',(815,-325,-35+i*10))
    add('Radiator_Concept',o.box(32,245,235),'12_Aircraft_Integration','black',(900,-10,-102))
    for i in range(20):add(f'Radiator_Fin_{i+1}',o.box(35,240,1.5),'12_Aircraft_Integration','steel',(900,-10,-210+i*11))

def export():
    report=validate(); report['parts']=[]
    render=[];groups={};bad=[]
    print('Validating and tessellating',len(PARTS),'parts',flush=True)
    for i,p in enumerate(PARTS):
        b=o.bounds(p['world']);vol=o.volume(p['world']);ok=o.valid(p['world'])
        if not ok:bad.append(p['name'])
        row=dict(name=p['name'],group=p['group'],valid=ok,solids=o.solid_count(p['world']),volume_mm3=round(vol,3),bbox_mm=b,source=p['source'])
        report['parts'].append(row)
        verts,tri=o.mesh(p['shape'])
        render.append({k:p[k] for k in ['name','group','color','pos','rx','motion','source','section']}|{'vertices':verts,'triangles':tri})
        groups.setdefault(p['group'],[]).append(p)
        if i%35==0:print('Processed',i,'/',len(PARTS),flush=True)
    report['invalid_parts']=bad
    engine=[p for p in PARTS if p['group'] not in ['12_Aircraft_Integration','13_Routing_Concepts','14_EECU','17_Aircraft_Electrics'] and 'EECU_' not in p['name'] and 'PLS' not in p['name']]
    b=o.bounds(o.compound([p['world'] for p in engine]));report['engine_bbox_mm']=b
    report['engine_extents_mm']=[b[i+3]-b[i] for i in range(3)]
    report['reference_envelope_mm']=[v('length'),v('width'),v('height')]
    report['envelope_note']='Actual reconstructed extents reported, not forced to match OEM outer surfaces. Aircraft integration is outside engine envelope.'
    report['part_count']=len(PARTS);report['solid_count']=sum(r['solids'] for r in report['parts'])
    if bad or report['errors']:raise ValueError('Validation failed')
    print('Exporting named STEP assembly',flush=True)
    o.assembly_step(PARTS,OUT/'AE300_R4_Assembly.step')
    o.assembly_step([p for p in PARTS if p['group'] in ['02_Cranktrain','03_Reduction','06_Valvetrain']],OUT/'AE300_R4_Mechanism.step')
    for g,ps in groups.items():o.assembly_step(ps,OUT/'parts'/f'{g}.step')
    for name in ['Piston_C1','Connecting_Rod_C1','Crankshaft_4Throws_5Mains','Propeller_Flange_6x12_75_PCD101_6','Crankcase_4x83mm_Bores','Cylinder_Head_16Valve_Injector_Ports']:
        part=next(p for p in PARTS if p['name']==name);o.step(part['shape'],OUT/'parts'/f'{name}.step')
    (OUT/'render_meshes.json').write_text(json.dumps(render,separators=(',',':')))
    (OUT/'sensor_map.json').write_text(json.dumps(SENSORS,indent=2))
    (OUT/'parameters.json').write_text(json.dumps(CONFIG,indent=2))
    report['step_roundtrip']='pending'
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    with (OUT/'bill_of_materials.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['name','subassembly','solid_count','volume_mm3','provenance'])
        for p in report['parts']:w.writerow([p['name'],p['group'],p['solids'],p['volume_mm3'],p['source']])
    print('Completed:',len(PARTS),'parts;',len(SENSORS),'sensor bindings',flush=True)

if __name__=='__main__':
    start=time.time()
    for fn in [build_block,build_cranktrain,build_gearbox,build_valvetrain,build_systems,build_sensors,integration,build_connections]:fn()
    from details import complete_hardware,validate_hardware
    complete_hardware(globals())
    validate_hardware(globals())
    export();print('Build seconds',round(time.time()-start,1),flush=True)
