"""Reopen the saved Blender assembly, verify drivers and render a short preview."""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from kinematics import cylinder_state,BANK,DECK,a,bank_point,v
from paths import OUT
scene=bpy.context.scene
root=bpy.data.objects['AE300_CONTROL__animate_crank_angle']
checks=[]; valve_checks=[]; transmission_checks=[]
for frame in [1,31,61,91,121,151,181,211,241,32,74,168,209]:
    scene.frame_set(frame);theta=root['crank_angle_deg']
    for i in range(4):
        st=cylinder_state(theta,i);p=bpy.data.objects[f'Piston_C{i+1}'];r=bpy.data.objects[f'Connecting_Rod_C{i+1}']
        small=r.matrix_world@Vector((0,0,a('rod_length')/1000))
        checks.append(dict(frame=frame,angle_deg=theta,cylinder=i+1,
            piston_error_mm=math.dist([c*1000 for c in p.location],st['wrist']),
            rod_big_end_error_mm=math.dist([c*1000 for c in r.location],st['pin']),
            rod_small_end_error_mm=math.dist([c*1000 for c in small],st['wrist'])))
        for j,(dx,y) in enumerate([(-16,-17),(16,-17),(-16,17),(16,17)]):
            typ='intake' if dx*y<0 else 'exhaust'
            lift=st[typ];x=a('cylinder_x0')+i*v('pitch')
            valve=bpy.data.objects[f'Valve_C{i+1}_{typ}_{j+1}']
            spring=bpy.data.objects[f'Valve_Spring_C{i+1}_{j+1}']
            retainer=bpy.data.objects[f'Spring_Retainer_C{i+1}_{j+1}']
            target=bank_point((x+dx,y,DECK+1.2-lift))
            tip=spring.matrix_world@Vector((0,0,.022))
            valve_checks.append(dict(frame=frame,cylinder=i+1,valve=j+1,lift_mm=lift,
                valve_position_error_mm=math.dist([c*1000 for c in valve.location],target),
                spring_length_error_mm=abs(spring.scale.z*22-(22-lift)),
                spring_retainer_error_mm=math.dist(tip,retainer.location)*1000))
    for name,ratio,phase in [('Gear_Input_100T',1,90),('Gear_Idler_50T',-2,-86.4),('Gear_Output_169T',1/v('gear_ratio'),-90),
                              ('Alternator_Pulley',46/26,0),('Water_Pump_Pulley',46/32,0)]:
        actual=bpy.data.objects[name].rotation_euler.x
        expected=math.radians(phase-theta*ratio)
        transmission_checks.append(dict(frame=frame,object=name,error_radians=abs(actual-expected)))
maximum=max(max(c[k] for k in ['piston_error_mm','rod_big_end_error_mm','rod_small_end_error_mm']) for c in checks)
assert maximum<0.001,f'Blender mechanism mismatch: {maximum}'
max_valve=max(c['valve_position_error_mm'] for c in valve_checks)
max_spring=max(c['spring_retainer_error_mm'] for c in valve_checks)
max_transmission=max(c['error_radians'] for c in transmission_checks)
assert max_valve<.001 and max_spring<.001 and max_transmission<1e-5
report=dict(reopened_blend=True,check_count=len(checks),max_joint_error_mm=maximum,checks=checks,
    max_valve_position_error_mm=max_valve,max_spring_retainer_error_mm=max_spring,
    max_transmission_error_radians=max_transmission,valve_checks=valve_checks,transmission_checks=transmission_checks,
    scope='Prescribed kinematic motion only. Cam contact, chain engagement, spring stress and fluid dynamics not simulated.')
(OUT/'blender_validation.json').write_text(json.dumps(report,indent=2))
print('REOPENED DRIVER CHECK',maximum,flush=True)

# CPU Cycles avoids the graphics-driver failure; denoising is unavailable here.
scene.render.engine='CYCLES'
scene.cycles.device='CPU';scene.cycles.samples=4;scene.cycles.use_denoising=False
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
scene.display.shading.cavity_type='BOTH';scene.display.shading.show_specular_highlight=True
scene.display.shading.background_type='WORLD';scene.world.color=(.035,.045,.060)
scene.render.resolution_x=1000;scene.render.resolution_y=680;scene.render.resolution_percentage=100
for obj in scene.objects:
    if obj.get('cad_solid'):
        hide=obj.get('subsystem') not in ['02_Cranktrain','03_Reduction','06_Valvetrain']
        obj.hide_render=hide;obj.hide_set(hide)
scene.camera.data.ortho_scale=1.12
scene.camera.location=(-.78,-1.12,.70)
scene.camera.rotation_euler=(Vector((.38,-.07,-.13))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
for ob in scene.objects:
    if ob.name=='Studio_Ground':ob.hide_render=True
frames=OUT/'motion_frames';frames.mkdir(exist_ok=True)
for index,frame in enumerate(range(1,241,4)):
    scene.frame_set(frame);scene.render.filepath=str(frames/f'{index:03}.png');bpy.ops.render.render(write_still=True)
print('Motion preview frames complete',flush=True)
