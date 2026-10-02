import bpy, os, sys, math
from mathutils import Matrix, Quaternion

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(argv) < 3:
    raise SystemExit("usage: target.glb walk.bvh out.glb [start end step]")
target_path,bvh_path,out_path=argv[:3]
fstart=int(argv[3]) if len(argv)>3 else 300
fend=int(argv[4]) if len(argv)>4 else 360
fstep=int(argv[5]) if len(argv)>5 else 2

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

bpy.ops.import_scene.gltf(filepath=os.path.abspath(target_path))
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No target armature")

# Remove all generated/fallback animation. We are building a fresh mocap walk only.
arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
arm.animation_data.action=None

before=set(bpy.data.objects)
bpy.ops.import_anim.bvh(filepath=os.path.abspath(bvh_path),axis_forward='-Z',axis_up='Y',use_fps_scale=False)
src=next((o for o in bpy.data.objects if o not in before and o.type=='ARMATURE'),None)
if src is None:
    raise SystemExit("No BVH armature")
src_action=src.animation_data.action if src.animation_data else None
if src_action is None:
    raise SystemExit("BVH has no action")

# Exact 100STYLE Neutral_FW hierarchy -> MakeHuman game_engine rig.
MAP={
    "pelvis":"Hips",
    "spine_01":"Chest",
    "spine_02":"Chest2",
    "spine_03":"Chest4",
    "neck_01":"Neck",
    "head":"Head",
    "clavicle_l":"LeftCollar",
    "upperarm_l":"LeftShoulder",
    "lowerarm_l":"LeftElbow",
    "clavicle_r":"RightCollar",
    "upperarm_r":"RightShoulder",
    "lowerarm_r":"RightElbow",
    "thigh_l":"LeftHip",
    "calf_l":"LeftKnee",
    "foot_l":"LeftAnkle",
    "ball_l":"LeftToe",
    "thigh_r":"RightHip",
    "calf_r":"RightKnee",
    "foot_r":"RightAnkle",
    "ball_r":"RightToe",
}
pairs={t:s for t,s in MAP.items() if t in arm.pose.bones and s in src.pose.bones}
missing=[f"{t}->{s}" for t,s in MAP.items() if t not in arm.pose.bones or s not in src.pose.bones]
print("RETARGET_PAIRS",len(pairs),sorted(pairs.items()))
if missing:
    print("RETARGET_MISSING",missing)

# Precompute source/target REST orientations in actual world coordinates.
src_obj_rot=src.matrix_world.to_3x3()
tgt_obj_rot=arm.matrix_world.to_3x3()
src_rest_world={}
tgt_rest_world={}
for tb,sb in pairs.items():
    src_rest_world[tb]=src_obj_rot @ src.data.bones[sb].matrix_local.to_3x3()
    tgt_rest_world[tb]=tgt_obj_rot @ arm.data.bones[tb].matrix_local.to_3x3()

def depth(b):
    d=0
    while b.parent is not None:
        d+=1
        b=b.parent
    return d

# Parents first because PoseBone.matrix is an armature-space/world-hierarchy matrix.
order=sorted(pairs.keys(),key=lambda n: depth(arm.data.bones[n]))

walk=bpy.data.actions.new("walk")
walk.use_fake_user=True
arm.animation_data.action=walk

for b in arm.pose.bones:
    b.location=(0,0,0)
    b.scale=(1,1,1)
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)

out_fr=1
deps=bpy.context.evaluated_depsgraph_get()
for fr in range(fstart,fend+1,fstep):
    bpy.context.scene.frame_set(fr)
    bpy.context.view_layer.update()
    se=src.evaluated_get(deps)

    for tb in order:
        sb=pairs[tb]
        # Copy the source bone's *world orientation delta from its own rest pose*.
        # This is independent of different local bone axes/rest poses in the two rigs.
        s_pose_world=src_obj_rot @ se.pose.bones[sb].matrix.to_3x3()
        d_world=s_pose_world @ src_rest_world[tb].inverted()
        t_pose_world=d_world @ tgt_rest_world[tb]

        # PoseBone.matrix expects armature-object space.
        t_pose_arm=tgt_obj_rot.inverted() @ t_pose_world
        p=arm.pose.bones[tb]
        pos=p.matrix.to_translation()
        p.matrix=Matrix.Translation(pos) @ t_pose_arm.to_4x4()
        bpy.context.view_layer.update()
        p.rotation_mode='QUATERNION'
        p.keyframe_insert("rotation_quaternion",frame=out_fr)

    out_fr += 1

# Constant interpolation mode is wrong for mocap; use Bezier/auto-clamped handles.
for fc in walk.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation='BEZIER'
        kp.handle_left_type='AUTO_CLAMPED'
        kp.handle_right_type='AUTO_CLAMPED'

# Clean source BVH object/action before export.
bpy.data.objects.remove(src,do_unlink=True)
if src_action is not None:
    try:
        bpy.data.actions.remove(src_action)
    except Exception:
        pass

# Export only target + its mocap walk.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
tr=arm.animation_data.nla_tracks.new()
tr.name="walk"
st=tr.strips.new("walk",1,walk)
st.action_frame_start=walk.frame_range[0]
st.action_frame_end=walk.frame_range[1]
arm.animation_data.action=None

bpy.context.scene.render.fps=30
bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=max(2,out_fr-1)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out_path),export_format='GLB',
                          export_animations=True,export_animation_mode='ACTIONS',
                          export_yup=True,export_materials='EXPORT',export_apply=False)
print("RETARGET_DONE",os.path.abspath(out_path),"source",fstart,fend,fstep,
      "target_frames",tuple(round(x,2) for x in walk.frame_range))
