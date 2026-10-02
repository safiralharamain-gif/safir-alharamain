import bpy, os, sys, math, json
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src, out = argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm is None:
    raise SystemExit("No armature")
arm.animation_data_create()
pb=arm.pose.bones
bones=arm.data.bones

for need in ("pelvis","lowerarm_l","lowerarm_r","hand_l","hand_r","thumb_01_l","thumb_01_r"):
    if need not in pb:
        raise SystemExit("Missing bone "+need)

actions=list(bpy.data.actions)
if not actions:
    raise SystemExit("No imported BVH action found")

# Prefer the longest imported action as the walk cycle.
walk=max(actions, key=lambda a: (a.frame_range[1]-a.frame_range[0], len(a.fcurves)))
print("IMPORTED_ACTIONS", [(a.name, tuple(round(x,2) for x in a.frame_range), len(a.fcurves)) for a in actions])
walk.name="walk"
walk.use_fake_user=True
arm.animation_data.action=walk

# Remove armature object root motion if imported.
for fc in list(walk.fcurves):
    if fc.data_path in ("location","rotation_euler","rotation_quaternion","rotation_axis_angle"):
        walk.fcurves.remove(fc)

# Make pelvis in-place horizontally: preserve vertical bounce and all rotations.
pel_loc=f'pose.bones["pelvis"].location'
for fc in list(walk.fcurves):
    if fc.data_path == pel_loc and fc.array_index in (0,1):
        base=fc.evaluate(walk.frame_range[0])
        for kp in fc.keyframe_points:
            kp.co.y=base
            kp.handle_left.y=base
            kp.handle_right.y=base

# Protect current accepted hand solution by removing imported hand/finger rotations,
# then recompute wrist orientation from forearm + thumb geometry at every frame.
def remove_rotation_curves(action,bn):
    paths={
        f'pose.bones["{bn}"].rotation_quaternion',
        f'pose.bones["{bn}"].rotation_euler',
        f'pose.bones["{bn}"].rotation_axis_angle'
    }
    for fc in list(action.fcurves):
        if fc.data_path in paths:
            action.fcurves.remove(fc)

def orient_wrists_inward(action):
    f0=int(math.floor(action.frame_range[0])); f1=int(math.ceil(action.frame_range[1]))
    configs=[]
    forward=Vector((0.0,-1.0,0.0))
    for hand_bn,fore_bn,side in (("hand_l","lowerarm_l","l"),("hand_r","lowerarm_r","r")):
        thumb_bn=f"thumb_01_{side}"
        rest_rot=bones[hand_bn].matrix_local.to_3x3()
        local_y=Vector((0,1,0))
        thumb_arm=bones[thumb_bn].head_local-bones[hand_bn].head_local
        thumb_local=rest_rot.inverted() @ thumb_arm
        local_x=thumb_local-local_y*thumb_local.dot(local_y)
        if local_x.length < 1e-6: raise RuntimeError("Degenerate thumb axis "+hand_bn)
        local_x.normalize()
        local_z=local_x.cross(local_y); local_z.normalize()
        local_x=local_y.cross(local_z); local_x.normalize()
        local_basis=Matrix((local_x,local_y,local_z)).transposed()
        remove_rotation_curves(action,hand_bn)
        configs.append((hand_bn,fore_bn,local_basis))
    for fr in range(f0,f1+1):
        bpy.context.scene.frame_set(fr); bpy.context.view_layer.update()
        for hand_bn,fore_bn,local_basis in configs:
            fore=pb[fore_bn]; hand=pb[hand_bn]
            target_y=(fore.tail-fore.head)
            if target_y.length<1e-6: continue
            target_y.normalize()
            target_x=forward-target_y*forward.dot(target_y)
            if target_x.length<1e-6:
                target_x=Vector((1,0,0))-target_y*target_y.x
            target_x.normalize()
            target_z=target_x.cross(target_y); target_z.normalize()
            target_x=target_y.cross(target_z); target_x.normalize()
            target_basis=Matrix((target_x,target_y,target_z)).transposed()
            desired_rot=target_basis @ local_basis.inverted()
            pos=hand.matrix.to_translation()
            hand.matrix=Matrix.Translation(pos) @ desired_rot.to_4x4()
            bpy.context.view_layer.update()
            hand.rotation_mode='QUATERNION'
            hand.keyframe_insert("rotation_quaternion",frame=fr)

def relax_fingers(action):
    f0=int(math.floor(action.frame_range[0])); f1=int(math.ceil(action.frame_range[1]))
    curl={"01":-0.12,"02":-0.24,"03":-0.18}
    thumb={"01":-0.04,"02":-0.07,"03":-0.05}
    for side in ("l","r"):
        for finger in ("index","middle","ring","pinky"):
            for seg,ang in curl.items():
                bn=f"{finger}_{seg}_{side}"
                if bn not in pb: continue
                remove_rotation_curves(action,bn)
                pb[bn].rotation_mode='QUATERNION'
                q=Quaternion(Vector((0,0,1)),ang)
                pb[bn].rotation_quaternion=q
                pb[bn].keyframe_insert("rotation_quaternion",frame=f0)
                pb[bn].rotation_quaternion=q
                pb[bn].keyframe_insert("rotation_quaternion",frame=f1)
        for seg,ang in thumb.items():
            bn=f"thumb_{seg}_{side}"
            if bn not in pb: continue
            remove_rotation_curves(action,bn)
            pb[bn].rotation_mode='QUATERNION'
            q=Quaternion(Vector((0,0,1)),ang)
            pb[bn].rotation_quaternion=q
            pb[bn].keyframe_insert("rotation_quaternion",frame=f0)
            pb[bn].rotation_quaternion=q
            pb[bn].keyframe_insert("rotation_quaternion",frame=f1)

orient_wrists_inward(walk)
relax_fingers(walk)

# Create a quiet idle from the first walk frame without root translation.
bpy.context.scene.frame_set(int(walk.frame_range[0]))
bpy.context.view_layer.update()
idle=bpy.data.actions.new("idle")
idle.use_fake_user=True
arm.animation_data.action=idle
for b in pb:
    b.rotation_mode='QUATERNION'
    b.keyframe_insert("location",frame=1)
    b.keyframe_insert("rotation_quaternion",frame=1)
    b.keyframe_insert("scale",frame=1)
    b.keyframe_insert("location",frame=60)
    b.keyframe_insert("rotation_quaternion",frame=60)
    b.keyframe_insert("scale",frame=60)

# Restore walk and make NLA strips.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
arm.animation_data.action=None
for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,int(act.frame_range[0]),act)
    st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]

bpy.context.scene.render.fps=30
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out), export_format='GLB',
    export_animations=True, export_animation_mode='ACTIONS',
    export_yup=True, export_materials='EXPORT', export_apply=False)
print("BVH_WALK_PREVIEW_READY", os.path.abspath(out), walk.frame_range[:])
