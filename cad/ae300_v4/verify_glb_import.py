"""Roundtrip the baked GLB through a fresh Blender scene, then check joints."""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from paths import OUT
from kinematics import cylinder_state,a

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(OUT/'AE300_R4_Animated.glb'))
checks=[]
for frame in [1,31,61,91,121,151,181,211,241]:
    scene.frame_set(frame)
    theta=(frame-1)*3
    for i in range(4):
        st=cylinder_state(theta,i)
        piston=bpy.data.objects[f'Piston_C{i+1}']
        rod=bpy.data.objects[f'Connecting_Rod_C{i+1}']
        small=rod.matrix_world@Vector((0,0,a('rod_length')/1000))
        checks.append(dict(frame=frame,cylinder=i+1,
            piston_error_mm=math.dist([c*1000 for c in piston.matrix_world.translation],st['wrist']),
            rod_pin_error_mm=math.dist([c*1000 for c in rod.matrix_world.translation],st['pin']),
            rod_wrist_error_mm=math.dist([c*1000 for c in small],st['wrist'])))
max_error=max(row[k] for row in checks for k in ['piston_error_mm','rod_pin_error_mm','rod_wrist_error_mm'])
report=dict(glb_reimported=True,frames_checked=9,max_joint_error_mm=max_error,checks=checks)
(OUT/'glb_validation.json').write_text(json.dumps(report,indent=2))
assert max_error<.001,f'GLB baked motion differs from mechanism: {max_error} mm'
print('GLB REIMPORT JOINT CHECK PASSED',max_error,flush=True)
