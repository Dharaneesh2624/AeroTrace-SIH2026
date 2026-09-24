"""R4 hardware completion. Documentary topology; most detail geometry assumed.

Do not infer production dimensions, pinouts, material grades, certified routing,
firmware, or physical engine performance from the illustrative parts here.
"""
import math,json
import occ as o
from kinematics import a,v,DECK,bank_point
from paths import OUT

def hexagon(radius,height,z=0):
    return o.extrude([(radius*math.cos(i*math.tau/6),radius*math.sin(i*math.tau/6),z) for i in range(6)],(0,0,height))

def sensor_geometry(name):
    """Different envelopes for different sensing principles; not supplier CAD."""
    boss=o.cut(o.cyl(12,5),o.cyl(4.4,7,(0,0,-1)))
    if name.startswith(('CRS','CAS')):
        body=o.fuse(o.cyl(5,24,(0,0,-18)),o.rounded_xy(31,17,5,4,(8,0,2.5)),o.cyl(8,17,(0,0,3)),o.box(17,13,12,(5,0,23)))
        body=o.cut(body,o.cyl(2.8,7,(18,0,-1)))
        family='speed_phase_pickup'
    elif name.startswith(('BPS','OPS','FPS','RPS')):
        body=o.fuse(o.cyl(4,15,(0,0,-12)),hexagon(11,8),o.cyl(9,19,(0,0,7)),o.box(15,14,13,(0,0,30)))
        family='pressure_transducer'
    elif name.startswith(('EGT','CHT')):
        body=o.fuse(o.cyl(2,42,(0,0,-34)),hexagon(7,7),o.cyl(4.5,14,(0,0,6)),o.cyl(2.5,14,(0,0,18)))
        family='proposed_thermocouple'
    elif name.startswith('VIB'):
        body=o.fuse(o.box(20,20,15,(0,0,7.5)),o.cyl(3,6,(0,0,-5)),o.cyl(5,12,(0,0,14)))
        family='proposed_accelerometer'
    elif name.startswith('PLS'):
        body=o.fuse(o.cyl(16,16),o.cyl(5,10,(0,0,14)),o.box(17,16,10,(16,0,8)))
        family='rotary_hall_lever_sensor'
    elif name=='Alternator_Current':
        body=o.cut(o.cyl(17,12),o.cyl(10,14,(0,0,-1)))
        body=o.fuse(body,o.box(18,13,12,(19,0,6)))
        family='proposed_current_transducer'
    elif name=='FuelFlow':
        body=o.fuse(o.cyl(12,40,(0,0,-18)),hexagon(15,10,-5),o.box(20,15,17,(0,0,23)))
        body=o.cut(body,o.cyl(4,61,(0,0,-20)))
        family='proposed_flow_transducer'
    elif name=='MOK':
        body=o.fuse(o.cyl(4,38,(0,0,-30)),o.cyl(15,7),o.box(23,17,20,(0,0,16)))
        family='oil_combinant_envelope'
    else:
        body=o.fuse(o.cyl(3,32,(0,0,-25)),hexagon(9,8),o.cyl(7,14,(0,0,7)),o.box(13,12,11,(0,0,25)))
        family='temperature_probe'
    return boss,body,family

def build_eecu(ctx):
    add=ctx['add']; group='14_EECU';src='IM14.7.1/Fig14.7 PDF81. Controlled plan/height/pitch; remaining details reconstructed. Position is exploded aircraft-side placement.'
    # Displayed upright: X is thickness, Y width, Z plan depth.
    x0=796.; y0=220.; z0=70.; height,width,depth=v('eecu_box')
    # Reserve 8 mm of the reference plan depth for bare receptacle projection.
    # The split between shell and receptacle is reconstructed, not dimensioned.
    body_depth=depth-8; body_z=z0+4
    case=o.orient(o.rounded_xy(body_depth,width,41.5,5),(1,0,0),(823.75,y0,body_z))
    case=o.fuse(case,o.box(10,237,71.2,(849.5,y0,.6)))
    case=o.cut(case,o.box(39,239,body_depth-8,(821,y0,body_z)))
    centres=[]
    for label,dy in [('G115_ECU_A',-v('eecu_connector_pitch')),('G121_POWER',0),('G116_ECU_B',v('eecu_connector_pitch'))]:
        p=(x0+v('eecu_connector_height'),y0+dy,z0-depth/2+8)
        centres.append((label,p))
        case=o.cut(case,o.cyl(18,18,(p[0],p[1],p[2]-2)))
    add('EECU_Main_Shell',case,group,'alloy',source=src)
    back=o.orient(o.rounded_xy(body_depth,width,7,5),(1,0,0),(799.5,y0,body_z))
    for yy,zz in [(112,-24),(328,-24),(108,50),(332,50),(116,162),(324,162)]:
        back=o.cut(back,o.cyl(2,6.01,(795.99,yy,zz),(1,0,0)))
    add('EECU_Backplate_6xM4_Envelope',back,group,'alloy',source=src+' Six M4x6 mounting holes documented; hole coordinates and thread envelopes assumed.')
    for j in range(28):
        add(f'EECU_Heat_Fin_{j+1:02}',o.box(6,2,139,(847.5,111+j*8,104.5)),group,'alloy',source=src)
    for j,(yy,zz) in enumerate([(103,-33),(337,-33),(103,172),(337,172),(103,65),(337,65)]):
        add(f'EECU_Case_Screw_{j+1}',o.cyl(3,4,(793,yy,zz),(1,0,0)),group,'steel',source=src)
    for label,p in centres:
        plate=o.cut(o.box(40,40,3,(p[0],p[1],p[2]-1.5)),o.cyl(17,5,(p[0],p[1],p[2]-4)))
        for dx in [-16,16]:
            for dy in [-16,16]:plate=o.cut(plate,o.cyl(1.7,5,(p[0]+dx,p[1]+dy,p[2]-4)))
        ring=o.cut(o.cyl(19,12,(p[0],p[1],p[2]-8)),o.cyl(16,14,(p[0],p[1],p[2]-9)))
        add('EECU_'+label+'_Flange',plate,group,'alloy',source=src)
        add('EECU_'+label+'_Receptacle',ring,group,'steel',source=src+' Connector labels per MM71-5; shell diameter assumed; no invented pin layout.')
        add('EECU_'+label+'_Insert',o.cyl(15.8,4,(p[0],p[1],p[2]-7)),group,'black',source='Blank insulating insert; actual pin count, keying and pinout intentionally unspecified')
        # Strain relief and bundled lead continue from mating plug; pin internals omitted.
        add('EECU_'+label+'_Backshell',o.cut(o.cyl(18,16,(p[0],p[1],p[2]-24)),o.cyl(9,18,(p[0],p[1],p[2]-25))),group,'black',source=src)
    vent=o.cut(o.cyl(7,5,(844.5,139,154),(1,0,0)),o.cyl(2,7,(843.5,139,154),(1,0,0)))
    add('EECU_Venting_Element',vent,group,'steel',source=src+' Vent documented; ambient measurement physically internal, not an external bolt-on pressure sensor.')
    # These boards illustrate the documented redundant architecture, not PCB CAD.
    for channel,xx in [('A',814),('B',830)]:
        add('EECU_'+channel+'_Concept_Board',o.box(1.6,214,173,(xx,220,72)),group,'fuel',source='MM01-23/26 dual ECU architecture. Board dimensions/layout are conceptual, NOT actual PCB design.')
        for j in range(5):
            add(f'EECU_{channel}_Concept_Module_{j}',o.box(4,27,22,(xx+2.8,148+j*35,92)),group,'black',source='Functional block placeholder; not chip, memory or firmware identification')
        for yy in [119,321]:
            for zz in [-10,153]:
                add(f'EECU_{channel}_Standoff_{yy}_{zz}',o.cut(o.cyl(3,8,(xx-8,yy,zz),(1,0,0)),o.cyl(1.3,10,(xx-9,yy,zz),(1,0,0))),group,'gold',source=src)
    for sid,obj,signal,unit,ch,p in [('EECU_Baro','EECU_Venting_Element','ambient_pressure','hPa',801,(844.5,139,154)),
             ('EECU_BatteryVoltage','EECU_G121_POWER_Receptacle','battery_voltage','V',808,centres[1][1])]:
        ctx['SENSORS'].append(dict(id=sid,object=obj,signal=signal,unit=unit,category='OEM',position_mm=list(p),axis=[1,0,0],
            source='Internal EECU signal represented on related housing/interface, NOT an additional external sensor',telemetry_channel=ch,host='EECU_Main_Shell',
            family='internal_signal_binding',geometry_status='Signal attachment only; internal sensor/electrical layout not available'))

def complete_hardware(ctx):
    add,bank,parts,sensors=ctx['add'],ctx['bank'],ctx['PARTS'],ctx['SENSORS']
    src='R4 reference-based reconstruction; no OEM dimensioned drawing for this detail'
    print('Adding timing case, casing ribs, electronics, harness and service hardware',flush=True)
    # Timing cavity closes the previously exposed rear chain while retaining its
    # independent cover and gasket. Not a chain-contact solution.
    outline=[(-42,-40),(-74,15),(-92,270),(-91,350),(-22,366),(90,350),(95,250),(53,18),(34,-40)]
    inner=[(y*.86,(z-150)*.962+150) for y,z in outline]
    case=o.cut(o.extrude([(630,y,z) for y,z in outline],(42,0,0)),o.extrude([(634,y,z) for y,z in inner],(42,0,0)))
    for yy,zz in [(0,0),(-30,DECK+80),(30,DECK+80)]:case=o.cut(case,o.cyl(9.3 if zz==0 else 12.3,46,(628,yy,zz),(1,0,0)))
    bank('Timing_Case_Body',case,'01_Housings','alloy',section=True,source=src)
    cover=o.extrude([(673,y,z) for y,z in outline],(3,0,0))
    cover=o.cut(cover,o.cyl(9.3,5,(672,0,0),(1,0,0)))
    bank('Timing_Case_Removable_Cover',cover,'01_Housings','alloy',section=True,source=src)
    gasket=o.cut(o.extrude([(672,y,z) for y,z in outline],(1,0,0)),o.extrude([(671,y,z) for y,z in inner],(3,0,0)))
    bank('Timing_Case_Gasket_Envelope',gasket,'01_Housings','black',section=True,source=src)
    for j,(yy,zz) in enumerate(outline):
        bank(f'Timing_Cover_Screw_{j}',o.cyl(3.2,5,(676,yy*.95,(zz-150)*.975+150),(1,0,0)),'01_Housings','steel',section=True,source=src)
    # Casting ribs on the exterior rather than another opaque enclosing box.
    for xx in [245,305,395,485,575]:
        for yy in [-85,85]:
            bank(f'Block_Cast_Rib_{xx}_{yy}',o.box(8,9,134,(xx,yy,125)),'01_Housings','iron',section=True,source=src)
    for zz in [75,155]:
        for yy in [-87,87]:bank(f'Block_Long_Rib_{yy}_{zz}',o.box(400,7,7,(405,yy,zz)),'01_Housings','iron',section=True,source=src)
    # Engine oil service points and crankcase ventilation components.
    bank('Oil_Filler_Neck',o.cut(o.cyl(20,22,(237,40,DECK+140)),o.cyl(15,24,(237,40,DECK+139))),'09_Fluids','alloy',source=src)
    bank('Oil_Filler_Cap',o.fuse(o.cyl(23,6,(237,40,DECK+162)),o.box(35,9,5,(237,40,DECK+170))),'09_Fluids','black',source=src)
    bank('Sump_Drain_Plug',o.move(hexagon(9,7),(585,0,-151)),'09_Fluids','steel',source=src)
    bank('Dipstick_Tube',o.pipe([(205,79,-100),(205,94,34),(222,101,173)],5,3),'09_Fluids','steel',source=src)
    bank('Dipstick_Pull_Loop',o.torus(10,3,(222,101,187),(1,0,0)),'09_Fluids','gold',source=src)
    sep=o.fuse(o.rounded_xy(157,41,23,9,(455,52,DECK+123)),o.cyl(21,34,(503,52,DECK+90)))
    sep=o.cut(sep,o.cyl(14,29,(503,52,DECK+91)))
    bank('Oil_Separator',sep,'09_Fluids','black',source='MM79-10/PDF176 oil separator architecture; under-cover placement and proportions reconstructed')
    bank('Oil_Separator_Bypass',o.cyl(8,18,(465,52,DECK+133)),'09_Fluids','gold',source='MM79-9/10; valve internals not known')
    bank('Oil_Separator_Return',o.pipe([(503,52,DECK+93),(515,68,DECK+85),(609,68,95)],5,3),'09_Fluids','black',source=src)
    # GPC and pneumatic BPA are distinct from the EECU and wastegate diaphragm.
    gpc=o.rounded_xy(98,73,30,5)
    gpc=o.cut(gpc,o.box(88,63,23,(0,0,-2)))
    bank('Glow_Plug_Control_Box',o.move(gpc,(325,-117,95)),'15_Engine_Electrics','black',source='MM76-3/PDF159 Fig76-1; four-mount box and connector, dimensions assumed')
    bank('GPC_Baseplate',o.box(107,80,3,(325,-117,78.5)),'15_Engine_Electrics','alloy',source=src)
    bank('GPC_Electrical_Connector',o.box(30,18,19,(325,-162,95)),'15_Engine_Electrics','black',source=src)
    for xx in [283,367]:
        for yy in [-148,-86]:bank(f'GPC_Fastener_{xx}_{yy}',o.cyl(3,5,(xx,yy,109)),'15_Engine_Electrics','steel',source=src)
    bp=bank_point((584,-175,DECK+48))
    bpa=o.fuse(o.cyl(18,54),o.box(41,18,8,(0,0,6)),o.box(19,15,16,(14,0,47)))
    add('Boost_Pressure_Actuator_BPA',bpa,'15_Engine_Electrics','black',bp,source='MM81-3/4, later manifold-fed BPA arrangement chosen; this is not the wastegate diaphragm')
    for j,p in enumerate([(bp[0]-10,bp[1],bp[2]+52),(bp[0]+10,bp[1],bp[2]+52)]):
        add(f'BPA_Hose_Port_{j}',o.cut(o.cyl(5,13,p),o.cyl(3,15,(p[0],p[1],p[2]-1))),'15_Engine_Electrics','alloy',source=src)
    tp=bank_point((608,-205,DECK+30))
    add('BPA_Manifold_Reference_Hose',o.pipe([bank_point((578,-119,DECK+35)),(bp[0]-10,bp[1]-12,bp[2]+75),(bp[0]-10,bp[1],bp[2]+64)],5,3),'15_Engine_Electrics','black',source='MM81-4 topology only; hose route reconstructed')
    add('BPA_Wastegate_Hose',o.pipe([(bp[0]+10,bp[1],bp[2]+64),(bp[0]+55,bp[1],bp[2]+79),(tp[0]+35,tp[1]+38,tp[2]+76)],5,3),'15_Engine_Electrics','black',source=src)
    # Airframe-mounted regulator, dual supply pumps and a separate SIH DAQ concept.
    ag='17_Aircraft_Electrics'
    add('Alternator_External_Regulator',o.box(30,94,77),(ag),'black',(810,355,76),source='MM01-23/PDF45 external regulator documented; envelope and placement assumed')
    for j in range(8):add(f'Regulator_Fin_{j}',o.box(7,87,2),ag,'alloy',(828,355,44+j*9),source=src)
    add('SIH_DAQ_Concept',o.box(45,97,52),ag,'sih',(813,355,-120),source='Proposed extra-sensor acquisition enclosure; not an AE300 engine component')
    for j,yy in enumerate([150,210]):
        add(f'Aircraft_Fuel_Pump_{chr(65+j)}',o.cyl(19,78,(735,yy,-262),(1,0,0)),ag,'steel',source='MM01-24 supply pumps A/B architecture; airframe-supplied, generic geometry')
    # Engine harness family routing. No pin assignments or conductor gauges guessed.
    hg='16_Engine_Harness';connections=[]
    for channel,yy in [('A',-146),('B',-158),('Shared',-152),('SIH_DAQ',-174)]:
        points=[bank_point((202,yy,DECK+153)),bank_point((622,yy,DECK+153))]
        add('Harness_Backbone_'+channel,o.pipe(points,4 if channel!='Shared' else 5),hg,'sih' if channel=='SIH_DAQ' else 'black',source='MM71-4/5 OEM harness topology; SIH loom additional; routes, diameters and separation conceptual')
    for s in sensors:
        if s['family']=='internal_signal_binding' or s['id'].startswith('PLS'):continue
        pos=s['position_mm'];end=tuple(pos[k]+s['axis'][k]*33 for k in range(3))
        channel='SIH_DAQ' if s['category']=='SIH' else ('A' if s['id'].endswith('1') else 'B' if s['id'].endswith('2') else 'Shared')
        if s['id']=='CTS_GPC':channel='GPC'
        xx=max(205,min(620,pos[0]));route_y=-146 if channel=='A' else -158 if channel=='B' else -174 if channel=='SIH_DAQ' else -152
        dest=bank_point((325,-162,95)) if channel=='GPC' else bank_point((xx,route_y,DECK+153))
        mid=(end[0]+8,end[1],dest[2]+9)
        add('Harness_Branch_'+s['id'],o.pipe([end,mid,dest],2.0),hg,'sih' if channel=='SIH_DAQ' else 'black',source='Concept route only; SIH branch is not an OEM ECU input or certified harness')
        connections.append(dict(id=s['id'],object=s['object'],network=channel,route='Harness_Branch_'+s['id'],pinout='UNSPECIFIED',status='Unvalidated routing concept'))
        s['network']=channel
    for i,xx in enumerate([240,330,420,510,600]):
        pp=bank_point((xx,-152,DECK+153))
        add(f'Harness_Clamp_{i}',o.cut(o.cyl(11,8,(pp[0]-4,pp[1],pp[2]),(1,0,0)),o.cyl(9,10,(pp[0]-5,pp[1],pp[2]),(1,0,0))),hg,'alloy',source=src)
    for label,loc in [('GPC',bank_point((325,-162,95))),('BPA',bp),('FMU',bank_point((657,100,150))),('PCV',bank_point((204,-76,DECK+113))),('GOV',(105,78,128))]:
        dest=bank_point((min(620,loc[0]),-152,DECK+153))
        add('Harness_Actuator_'+label,o.pipe([loc,(loc[0]+8,loc[1],dest[2]+12),dest],2.5),hg,'black',source='MM71-5 named actuator connection; unvalidated route, pinout unspecified')
        connections.append(dict(id=label,network='Shared_actuator',route='Harness_Actuator_'+label,pinout='UNSPECIFIED'))
    for i,xx in enumerate(ctx['X']):
        for label,loc,dst in [('INJ',bank_point((xx,0,DECK+136)),bank_point((xx,-152,DECK+153))),
                              ('GP',bank_point((xx+10,6,DECK+82)),bank_point((325,-162,95)))]:
            add(f'Harness_{label}_{i+1}',o.pipe([loc,(loc[0],loc[1]-18,loc[2]+14),dst],2.2),hg,'black',source=src)
            connections.append(dict(id=f'{label}{i+1}',network='GPC' if label=='GP' else 'Shared_actuator',route=f'Harness_{label}_{i+1}',pinout='UNSPECIFIED'))
    for channel,yy in [('A',142.75),('Power',220),('B',297.25)]:
        start=(810,355,76) if channel=='Power' else bank_point((622,-146 if channel=='A' else -158,DECK+153))
        add('Airframe_Harness_to_ECU_'+channel,o.pipe([start,(727,yy,-90),(826.7,yy,-87),(826.7,yy,-59)],7),ag,'black',source='External loom concept. EECU belongs outside engine fire zone; not an installation-ready layout')
    add('Airframe_Harness_to_SIH_DAQ',o.pipe([bank_point((622,-174,DECK+153)),(722,355,-158),(813,355,-146)],5),ag,'sih',source='Separate acquisition network for added SIH sensors; NOT connected to OEM ECU inputs')
    add('Generator_to_Regulator_Loom',o.pipe([(680,129,-202),(732,270,-202),(810,355,39)],5),ag,'black',source='Alternator/external regulator topology, routing only; conductor gauge and pinout not specified')
    for i,yy in [(1,142.75),(2,297.25)]:
        add(f'Power_Lever_Loom_{i}',o.pipe([(828,345+i*28,-41),(851,yy,-96),(826.7,yy,-59)],3),ag,'black',source='PLS channel association only; wire count and pinout unspecified')
    (OUT/'connection_map.json').write_text(json.dumps(connections,indent=2))
    (OUT/'hardware_audit.json').write_text(json.dumps(dict(
        added=['CTS_GPC','Family-specific sensors','Three circular ECU interfaces','ECU shell/backplate/fins/vent','Conceptual ECU A/B boards',
            'Timing enclosure','Casing ribs','Oil service points','Oil separator and bypass','Glow plug controller','BPA and hoses',
            'External regulator','Named sensor/actuator harness branches','Aircraft pump concepts'],
        corrections=['R3 EECU depth246 replaced by226 mm; raised overall height58.5 distinguished from main48.5',
            'Internal barometric and voltage signals no longer depicted as extra external probes'],
        missing_OEM_data=['IPC/configuration/serial baseline','Casting surfaces and full oil/coolant galleries','Sensor supplier drawings',
            'ECU PCB/firmware/connector pinout','Harness wire list and approved route','Full fits/tolerances/contact validation'],
        completeness='Expanded subsystem representation; NOT complete OEM manufacturing or engine-control definition'),indent=2))

def validate_hardware(ctx):
    """Selected static interfaces, explicitly narrower than an all-parts audit."""
    byname={p['name']:p for p in ctx['PARTS']}; checks=[]
    pairs=[('Camshaft_ChainDriven','Cylinder_Head_16Valve_Injector_Ports'),
           ('Camshaft_GearDriven','Cylinder_Head_16Valve_Injector_Ports'),
           ('Shaft_Input','Gearbox_Cast_Case'),('Shaft_Idler','Gearbox_Cast_Case'),
           ('EECU_A_Concept_Board','EECU_Main_Shell'),('EECU_B_Concept_Board','EECU_Main_Shell'),
           ('Timing_Sprocket_Cam_40T','Timing_Case_Body'),('Cam_DriveGear_30_24T','Timing_Case_Body'),
           ('Cam_DriveGear_-30_24T','Timing_Case_Body'),('Double_Timing_Chain_3.5','Timing_Case_Body'),
           ('Crankshaft_4Throws_5Mains','Crankcase_4x83mm_Bores')]
    for left,right in pairs:
        overlap=max(0,o.volume(o.common(byname[left]['world'],byname[right]['world'])))
        checks.append(dict(a=left,b=right,overlap_mm3=overlap))
    bare=[p['world'] for p in ctx['PARTS'] if p['group']=='14_EECU' and 'Backshell' not in p['name'] and 'Screw' not in p['name']]
    b=o.bounds(o.compound(bare));ext=[b[i+3]-b[i] for i in range(3)]
    report=dict(scope='Selected static housing and ECU interfaces, not comprehensive motion/installation clash certification',
        checks=checks,bare_eecu_extents_mm=ext,eecu_reference_mm=v('eecu_box'),
        check_pass=all(c['overlap_mm3']<1e-4 for c in checks),eecu_extent_pass=all(abs(x-y)<1e-5 for x,y in zip(ext,v('eecu_box'))))
    (OUT/'hardware_validation.json').write_text(json.dumps(report,indent=2))
    print('HARDWARE CHECK',json.dumps(report),flush=True)
    if not report['check_pass'] or not report['eecu_extent_pass']:raise ValueError('Hardware clearance/ECU extent check failed; inspect hardware_validation.json')
