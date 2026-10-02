import bpy, os, sys
from mathutils import Matrix, Vector, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if len(argv) < 3:
    raise SystemExit("usage: fix_animations.py input.glb output.glb walk1.bvh")
src_path, out_path, bvh_path = argv[:3]

# Load the generated MakeHuman character.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src_path))

arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm is None:
    raise SystemExit("No target armature")
arm.animation_data_create()
pb = arm.pose.bones

# Remove any animation exported by the character generator. We rebuild walk correctly below.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
arm.animation_data.action = None
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

# Import the MakeHuman walk BVH. This BVH uses MakeHuman names (UpArm_L, UpLeg_L, ...),
# not the CMU names used by the old retargeter. The old name mismatch was the root cause
# of the broken arms, wrists and gait.
before = set(bpy.data.objects)
bpy.ops.import_anim.bvh(
    filepath=os.path.abspath(bvh_path),
    axis_forward='-Z',
    axis_up='Y',
    use_fps_scale=False,
)
src = next((o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE'), None)
if src is None or src.animation_data is None or src.animation_data.action is None:
    raise SystemExit("BVH import failed")
src_action = src.animation_data.action

MAP = {
    "pelvis": "Root",
    "spine_01": "Spine1",
    "spine_02": "Spine2",
    "spine_03": "Spine3",
    "neck_01": "Neck",
    "head": "Head",
    "clavicle_l": "Clavicle_L",
    "upperarm_l": "UpArm_L",
    "lowerarm_l": "LoArm_L",
    "hand_l": "Hand_L",
    "clavicle_r": "Clavicle_R",
    "upperarm_r": "UpArm_R",
    "lowerarm_r": "LoArm_R",
    "hand_r": "Hand_R",
    "thigh_l": "UpLeg_L",
    "calf_l": "LoLeg_L",
    "foot_l": "Foot_L",
    "ball_l": "Toe_L",
    "thigh_r": "UpLeg_R",
    "calf_r": "LoLeg_R",
    "foot_r": "Foot_R",
    "ball_r": "Toe_R",
}
pairs = {tb: sb for tb, sb in MAP.items() if tb in pb and sb in src.pose.bones}
for req in ("upperarm_l","lowerarm_l","hand_l","upperarm_r","lowerarm_r","hand_r",
            "thigh_l","calf_l","foot_l","thigh_r","calf_r","foot_r"):
    if req not in pairs:
        raise SystemExit("Missing retarget pair: " + req)

def depth(bone):
    d = 0
    while bone.parent is not None:
        d += 1
        bone = bone.parent
    return d

order = sorted(pairs.keys(), key=lambda n: depth(arm.data.bones[n]))
src_rest = {tb: src.data.bones[sb].matrix_local.to_3x3().copy() for tb, sb in pairs.items()}
tgt_rest = {tb: arm.data.bones[tb].matrix_local.to_3x3().copy() for tb in pairs}

def clear_target_pose():
    for b in pb:
        b.location = (0,0,0)
        b.scale = (1,1,1)
        b.rotation_mode = 'QUATERNION'
        b.rotation_quaternion = (1,0,0,0)

def apply_source_frame(frame, allowed=None):
    """Apply source global rotation deltas onto target rest orientations."""
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    se = src.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for tb in order:
        if allowed is not None and tb not in allowed:
            continue
        sb = pairs[tb]
        source_pose = se.pose.bones[sb].matrix.to_3x3()
        desired_rot = source_pose @ src_rest[tb].inverted() @ tgt_rest[tb]
        p = pb[tb]
        # Preserve target joint position; transfer only semantic orientation.
        p.matrix = Matrix.Translation(p.matrix.to_translation()) @ desired_rot.to_4x4()
        bpy.context.view_layer.update()

def key_target_rotations(action, frame, allowed=None):
    arm.animation_data.action = action
    for tb in order:
        if allowed is not None and tb not in allowed:
            continue
        p = pb[tb]
        p.rotation_mode = 'QUATERNION'
        p.keyframe_insert("rotation_quaternion", frame=frame)

def remove_rotation_channels(action, bone_name):
    paths = {
        f'pose.bones["{bone_name}"].rotation_quaternion',
        f'pose.bones["{bone_name}"].rotation_euler',
        f'pose.bones["{bone_name}"].rotation_axis_angle',
    }
    for fc in list(action.fcurves):
        if fc.data_path in paths:
            action.fcurves.remove(fc)

def relax_fingers(action, start, end):
    # Verified MakeHuman game-engine finger curl axis.
    arm.animation_data.action = action
    curl = {"01": -0.28, "02": -0.52, "03": -0.38}
    thumb = {"01": -0.08, "02": -0.15, "03": -0.10}
    for side in ("l","r"):
        for finger in ("index","middle","ring","pinky"):
            for seg, ang in curl.items():
                bn = f"{finger}_{seg}_{side}"
                if bn not in pb:
                    continue
                remove_rotation_channels(action, bn)
                pb[bn].rotation_mode = 'XYZ'
                pb[bn].rotation_euler = (0.0, 0.0, ang)
                pb[bn].keyframe_insert("rotation_euler", frame=start)
                pb[bn].keyframe_insert("rotation_euler", frame=end)
        for seg, ang in thumb.items():
            bn = f"thumb_{seg}_{side}"
            if bn not in pb:
                continue
            remove_rotation_channels(action, bn)
            pb[bn].rotation_mode = 'XYZ'
            pb[bn].rotation_euler = (0.0, 0.0, ang)
            pb[bn].keyframe_insert("rotation_euler", frame=start)
            pb[bn].keyframe_insert("rotation_euler", frame=end)
    arm.animation_data.action = None

# ---------- Correct full-body walk from MakeHuman BVH ----------
clear_target_pose()
walk = bpy.data.actions.new("walk")
walk.use_fake_user = True
arm.animation_data.action = walk

f0 = int(round(src_action.frame_range[0]))
f1 = int(round(src_action.frame_range[1]))
out_frame = 1
for sf in range(f0, f1 + 1):
    clear_target_pose()
    apply_source_frame(sf)
    key_target_rotations(walk, out_frame)
    out_frame += 1

# Exact loop seam: copy frame 1 pose to the frame after the final BVH frame.
arm.animation_data.action = walk
bpy.context.scene.frame_set(1)
first_q = {}
for tb in order:
    p = pb[tb]
    first_q[tb] = p.rotation_quaternion.copy()
for tb in order:
    pb[tb].rotation_mode = 'QUATERNION'
    pb[tb].rotation_quaternion = first_q[tb]
    pb[tb].keyframe_insert("rotation_quaternion", frame=out_frame)
walk_end = out_frame
relax_fingers(walk, 1, walk_end)

# ---------- Neutral idle using the BVH frame where both hands are closest to neutral ----------
# Pick the source frame with the least fore/aft hand displacement relative to source rest.
best_frame = f0
best_score = 1e30
for sf in range(f0, f1 + 1):
    bpy.context.scene.frame_set(sf)
    bpy.context.view_layer.update()
    se = src.evaluated_get(bpy.context.evaluated_depsgraph_get())
    hl = se.pose.bones["Hand_L"].matrix.translation
    hr = se.pose.bones["Hand_R"].matrix.translation
    rl = src.data.bones["Hand_L"].head_local
    rr = src.data.bones["Hand_R"].head_local
    score = abs(hl.y - rl.y) + abs(hr.y - rr.y)
    if score < best_score:
        best_score = score
        best_frame = sf

clear_target_pose()
idle = bpy.data.actions.new("idle")
idle.use_fake_user = True
arm.animation_data.action = idle
upper = {
    n for n in order
    if n.startswith(("spine_","neck_","head","clavicle_","upperarm_","lowerarm_","hand_"))
}
apply_source_frame(best_frame, upper)
for fr in (1, 30, 60):
    key_target_rotations(idle, fr, upper)
# Legs/pelvis remain in their anatomical rest pose; add explicit identity keys for stability.
for bn in ("pelvis","thigh_l","calf_l","foot_l","ball_l","thigh_r","calf_r","foot_r","ball_r"):
    if bn in pb:
        pb[bn].rotation_mode = 'QUATERNION'
        pb[bn].rotation_quaternion = (1,0,0,0)
        for fr in (1,30,60):
            pb[bn].keyframe_insert("rotation_quaternion", frame=fr)
relax_fingers(idle, 1, 60)

# Remove BVH helper armature + its action after retarget.
raw_bvh_action = src_action
bpy.data.objects.remove(src, do_unlink=True)
if raw_bvh_action and raw_bvh_action.name in bpy.data.actions:
    bpy.data.actions.remove(raw_bvh_action)

# Keep exactly idle + walk in NLA so Godot imports both clips.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle, walk):
    tr = arm.animation_data.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    st.action_frame_start = act.frame_range[0]
    st.action_frame_end = act.frame_range[1]
arm.animation_data.action = None

bpy.context.scene.render.fps = 24
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = max(60, walk_end)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=os.path.abspath(out_path),
    export_format='GLB',
    export_animations=True,
    export_animation_mode='ACTIONS',
    export_yup=True,
    export_materials='EXPORT',
    export_apply=False,
)
print("V16_CORRECT_MAKEHUMAN_BVH_RETARGET", os.path.abspath(out_path),
      "source_frames", f0, f1, "walk_end", walk_end, "idle_source", best_frame)
