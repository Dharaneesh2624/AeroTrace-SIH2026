"""Render the actual STEP tessellation and attach analytic mechanism drivers.
Run Blender --background --python this_file.py. No alternate proxy geometry.
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from kinematics import v,a,R,L,BANK,DECK,FIRE,cylinder_state,bank_point
from paths import OUT
data=json.loads((OUT/'render_meshes.json').read_text())
sensors=json.loads((OUT/'sensor_map.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.length_unit='MILLIMETERS'
scene.render.fps=30;scene.frame_start=1;scene.frame_end=241
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=16
scene.cycles.use_denoising=False
scene.render.resolution_x=1400;scene.render.resolution_y=972;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(0.14,0.17,0.21,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=0.35
root=bpy.data.objects.new('AE300_CONTROL__animate_crank_angle',None);scene.collection.objects.link(root)
root['crank_angle_deg']=0.0
root.id_properties_ui('crank_angle_deg').update(min=0,max=720,description='Master cycle angle; linked rods and valves follow. Preview time is slowed.')
root['model_status']='Engineering reconstruction R4. Exact bore/stroke/pitch/ratio; assumed rods/cams/gear teeth. See design notes.'
root['source_units']='STEP millimetres; meshes and translations metres'
root['firing_order']='1-3-4-2'
root['reference_dimensions_mm']='738 length / 855 width / 574 height; not claimed to be exact reconstructed bounds'
root.keyframe_insert(data_path='["crank_angle_deg"]',frame=1)
root['crank_angle_deg']=720.0;root.keyframe_insert(data_path='["crank_angle_deg"]',frame=241)
for layer in root.animation_data.action.layers:
    for strip in layer.strips:
        for cb in strip.channelbags:
            for curve in cb.fcurves:
                for k in curve.keyframe_points:k.interpolation='LINEAR'

collections={};materials={};objects={}
def coll(name):
    if name not in collections:
        c=bpy.data.collections.new(name);scene.collection.children.link(c);collections[name]=c
    return collections[name]

def mat(color):
    key=tuple(color)
    if key not in materials:
        m=bpy.data.materials.new('CAD_Material_'+str(len(materials)));m.diffuse_color=(*color,1);m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
        p.inputs['Metallic'].default_value=.65 if max(color)-min(color)<.2 else .28
        p.inputs['Roughness'].default_value=.32;materials[key]=m
    return materials[key]

for d in data:
    vertices=d['vertices'];motion=d['motion'];pos=d['pos'];rx=d['rx']
    if motion and motion['kind']=='cam':
        pivot=[0,motion['side']*30,DECK+80]
        # Direct cam gear centres are at same local pivot as camshafts.
        vertices=[[p[i]-pivot[i] for i in range(3)] for p in vertices];pos=bank_point(pivot)
    if motion and motion['kind']=='shaft':
        pivot=motion['pivot'];vertices=[[p[i]-pivot[i] for i in range(3)] for p in vertices];pos=pivot
    mesh=bpy.data.meshes.new(d['name']);mesh.from_pydata([[x/1000 for x in p] for p in vertices],[],d['triangles']);mesh.update()
    obj=bpy.data.objects.new(d['name'],mesh);coll(d['group']).objects.link(obj);obj.parent=root
    obj.location=[x/1000 for x in pos];obj.rotation_euler=(math.radians(rx),0,0);obj.data.materials.append(mat(d['color']))
    obj['source']=d['source'];obj['subsystem']=d['group'];obj['cad_solid']=True;obj['hide_for_section']=d['section']
    # CAD tessellation edges retain flat faces. Avoid globally smoothing bores onto planar decks.
    for p in mesh.polygons:p.use_smooth=False
    objects[d['name']]=obj

def drive(obj,path,index,expr):
    fc=obj.driver_add(path,index);dr=fc.driver;dr.type='SCRIPTED'
    var=dr.variables.new();var.name='t';var.type='SINGLE_PROP';var.targets[0].id=root;var.targets[0].data_path='["crank_angle_deg"]'
    dr.expression=expr

for d in data:
    obj=objects[d['name']];mo=d['motion']
    if not mo:continue
    kind=mo['kind']
    if kind=='crank':drive(obj,'rotation_euler',0,f'{BANK}-t*pi/180')
    elif kind in ['gear','shaft']:
        drive(obj,'rotation_euler',0,f'{math.radians(mo.get("phase",0))}-t*pi/180*{mo["ratio"]}')
    elif kind=='cam':
        drive(obj,'rotation_euler',0,f'{BANK}+t*pi/360*{mo["side"]}')
    elif kind in ['piston','rod']:
        i=mo['cylinder'];angle=f'((t-{FIRE[i]})*pi/180)'
        y=f'({R}*sin({angle}))';z=f'({R}*cos({angle}))';h=f'sqrt({L*L}-{y}**2)';w=f'({z}+{h})'
        if kind=='piston':
            drive(obj,'location',1,f'-{math.sin(BANK)}*{w}/1000')
            drive(obj,'location',2,f'({a("crank_z")}+{math.cos(BANK)}*{w})/1000')
        else:
            drive(obj,'location',1,f'({math.cos(BANK)}*{y}-{math.sin(BANK)}*{z})/1000')
            drive(obj,'location',2,f'({a("crank_z")}+{math.sin(BANK)}*{y}+{math.cos(BANK)}*{z})/1000')
            drive(obj,'rotation_euler',0,f'{BANK}+atan2({y},{h})')
    elif kind in ['valve','spring']:
        start=360 if mo['type']=='intake' else 180;cycle=f'((t-{FIRE[mo["cylinder"]]})%720)'
        lift=f'({a("valve_lift")}*sin(pi*({cycle}-{start})/180)**2 if {start}<{cycle}<{start+180} else 0)'
        if kind=='spring':
            drive(obj,'scale',2,f'({mo["free_height"]}-{lift})/{mo["free_height"]}')
        else:
            drive(obj,'location',1,f'({mo["base"][1]}+{math.sin(BANK)}*{lift})/1000')
            drive(obj,'location',2,f'({mo["base"][2]}-{math.cos(BANK)}*{lift})/1000')

for s in sensors:
    obj=objects[s['object']]
    for key in ['id','signal','unit','category','geometry_status','family']:obj[key]=s[key]
    obj['network']=s.get('network','internal_or_airframe')
    obj['telemetry_channel']=str(s['telemetry_channel'])
    obj['telemetry_value']=0.0;obj['telemetry_quality']='unbound'
    obj['sample_status']='No actual AE300 log connected'

# Useful opening state and repeatable studio render.
studio=coll('99_Presentation')
def put(obj):
    for c in list(obj.users_collection):c.objects.unlink(obj)
    studio.objects.link(obj)

bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.465));ground=bpy.context.object;ground.name='Studio_Ground';put(ground)
ground.data.materials.append(mat((.037,.048,.06)))
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Review_Camera';put(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=1.30
def camera(position,target,scale):
    cam.location=position;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale

def light(name,pos,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);studio.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector((.40,-.10,-.07))-ob.location).to_track_quat('-Z','Y').to_euler()

light('Large_Softbox',(-.4,-.9,1.3),110,1.0,(.87,.94,1))
light('Rim_Softbox',(1.1,.2,.8),135,.75,(1,.83,.60))
light('Front_Fill',(-.6,.6,.3),80,.85,(.62,.78,1))

def is_integration(obj):
    return obj.get('subsystem') in ['12_Aircraft_Integration','13_Routing_Concepts','14_EECU','17_Aircraft_Electrics'] or any(k in obj.name for k in ['EECU_Baro','EECU_BatteryVoltage','PLS1','PLS2'])
def mode(name):
    for obj in objects.values():
        hide=is_integration(obj) and name!='integration'
        if name=='section' and obj.get('hide_for_section'):hide=True
        if name=='mechanism': hide=obj['subsystem'] not in ['02_Cranktrain','03_Reduction','06_Valvetrain']
        if name in ['eecu','eecu_open']:hide=obj['subsystem']!='14_EECU'
        if name=='eecu_open' and (obj.name in ['EECU_Main_Shell','EECU_Backplate_6xM4_Envelope'] or obj.name.startswith(('EECU_Heat_Fin','EECU_Case_Screw','EECU_Venting'))):hide=True
        obj.hide_render=hide;obj.hide_set(hide)
    if name in ['section','mechanism']:
        for obj in objects.values():
            if obj.name.startswith(('HeadCover_Screw','Sump_Screw','Gearcase_Screw')):obj.hide_render=True;obj.hide_set(True)

def render(filename,view,position,target,scale):
    mode(view);camera(position,target,scale);scene.render.filepath=str(OUT/filename);bpy.ops.render.render(write_still=True)

scene.frame_set(36)
render('01_assembled.png','assembled',(-.85,-1.1,.65),(.38,-.07,-.13),1.22)
render('02_section.png','section',(-.78,-1.12,.70),(.38,-.07,-.13),1.22)
render('03_mechanism.png','mechanism',(-.72,-1.12,.70),(.37,-.06,-.1),1.1)
render('04_integration.png','integration',(-.85,-1.2,.88),(.52,-.05,-.09),1.57)
render('05_eecu_detail.png','eecu',(1.25,-.23,-.23),(.82,.22,.07),.49)
render('06_eecu_architecture.png','eecu_open',(1.25,-.23,-.23),(.82,.22,.07),.49)

# Export all engineering objects with names, material and custom properties; render
# helpers excluded. Drivers are baked by the exporters over the animated root.
mode('integration');scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for obj in objects.values():obj.select_set(True)
bpy.context.view_layer.objects.active=root
bpy.ops.export_scene.gltf(filepath=str(OUT/'AE300_R4_Animated.glb'),export_format='GLB',use_selection=True,
    export_extras=True,export_animations=True,export_animation_mode='SCENE',export_force_sampling=True,
    export_anim_scene_split_object=False)
bpy.ops.export_scene.fbx(filepath=str(OUT/'AE300_R4_Animated.fbx'),use_selection=True,bake_anim=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,add_leaf_bones=False,apply_unit_scale=True)

# Opening .blend shows engine in section with scene camera; all components are in
# their collections and can be restored through the supplied convenience script.
mode('integration');scene.frame_set(36);camera((-.85,-1.2,.88),(.52,-.05,-.09),1.57)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
        area.spaces.active.shading.type='MATERIAL'
        area.spaces.active.overlay.show_extras=False
        area.spaces.active.clip_end=100

text=bpy.data.texts.new('START_HERE.txt')
text.write('AE300 R4 engineering reconstruction\n\nSPACE: play slow 720-degree mechanism cycle.\nFunctional.blend opens fully assembled, including separately located aircraft electronics. Cutaway.blend opens with outer housings hidden.\nSelect AE300_CONTROL__animate_crank_angle and change crank_angle_deg to pose the mechanism.\nDrivers work without external Python files or auto-run scripts.\nSTEP is in millimetres; Blender and GLB in metres.\nDocumented geometry and assumptions are separate in parameters.json. Most contours, exact sensor hardware and ECU interior geometry are reconstructed.\nECU boards are conceptual architecture placeholders, not real PCB layouts. No firmware or operational ECU simulation is included.\nSee DESIGN_NOTES.md, hardware_audit.json and connection_map.json. No telemetry connected; values are unbound.\n')
text2=bpy.data.texts.new('SHOW_ASSEMBLED.py')
text2.write("import bpy\nfor obj in bpy.context.scene.objects:\n    if obj.get('cad_solid'):\n        obj.hide_set(False)\n        obj.hide_render=False\n")
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AE300_R4_Functional.blend'))
mode('section');camera((-.78,-1.12,.70),(.38,-.07,-.13),1.22)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'AE300_R4_Cutaway.blend'))

# Numeric Blender driver check at three nontrivial phases against shared model.
checks=[]
for theta in [0,93,287,540,720]:
    ff=1+theta/3
    scene.frame_set(int(ff),subframe=ff-int(ff))
    evaluated_theta=float(root['crank_angle_deg'])
    for i in range(4):
        obj=objects[f'Piston_C{i+1}'];s=cylinder_state(evaluated_theta,i)
        error=math.dist([x*1000 for x in obj.location],s['wrist'])
        checks.append({'angle_deg':evaluated_theta,'cylinder':i+1,'position_error_mm':error})
(OUT/'blender_validation.json').write_text(json.dumps({'driver_checks':checks,'max_error_mm':max(x['position_error_mm'] for x in checks),'objects':len(objects)},indent=2))
print('BLENDER COMPLETE',len(objects),'CAD objects',flush=True)
