import bpy, os, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src, out = argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm is None:
    raise SystemExit("No armature")
arm.animation_data_create()
pb = arm.pose.bones
bones = arm.data.bones


def find(*names):
    for n in names:
        if n in pb:
            return n
    return None


pelvis = find("pelvis")
spine = find("spine_02", "spine_01")
head = find("head")
uaL = find("upperarm_l")
uaR = find("upperarm_r")
laL = find("lowerarm_l")
laR = find("lowerarm_r")
handL = find("hand_l")
handR = find("hand_r")
thL = find("thigh_l")
thR = find("thigh_r")
caL = find("calf_l")
caR = find("calf_r")
footL = find("foot_l")
footR = find("foot_r")
required = [pelvis, uaL, uaR, laL, laR, handL, handR, thL, thR, caL, caR, footL, footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

# IMPORTANT V14 CHARACTER FIX:
# The source GLB already contains a real MakeHuman/CMU retargeted walk. Previous versions deleted it
# and rebuilt a hand-keyed gait; that is what made the legs look stiff/sideways. Keep the mocap walk
# and only repair the idle pose + hands. Also NEVER zero hand_l/hand_r after IK baking: doing that
# overwrote the solved wrist orientation and was the cause of the visibly twisted hand.
walk = next((a for a in bpy.data.actions if a.name.lower() == "walk"), None)
if walk is None:
    walk = next((a for a in bpy.data.actions if a.name.lower().startswith("walk")), None)
if walk is None:
    raise SystemExit("Source GLB has no walk action")
walk.name = "walk"
walk.use_fake_user = True

pts = [p for b in bones for p in (b.head_local, b.tail_local)]
zmin = min(p.z for p in pts)
zmax = max(p.z for p in pts)
H = max(0.1, zmax - zmin)
hip_z = bones[pelvis].head_local.z
shoulder_z = (bones[uaL].head_local.z + bones[uaR].head_local.z) * 0.5
left_sign = 1.0 if bones[uaL].head_local.x > bones[uaR].head_local.x else -1.0
right_sign = -left_sign
hip_half = max(abs(bones[thL].head_local.x), abs(bones[thR].head_local.x))


def world(local):
    return arm.matrix_world @ Vector(local)


def empty(name, local):
    e = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(e)
    e.location = world(local)
    return e


def key_obj(obj, fr, local):
    obj.location = world(local)
    obj.keyframe_insert("location", frame=fr)


def add_ik(bone, target, pole, chain=2):
    c = pb[bone].constraints.new("IK")
    c.target = target
    c.pole_target = pole
    c.chain_count = chain
    c.use_rotation = False


def reset_pose():
    for b in pb:
        b.rotation_mode = 'QUATERNION'
        b.rotation_quaternion = (1, 0, 0, 0)
        b.location = (0, 0, 0)
        b.scale = (1, 1, 1)


def set_relaxed_fingers(action, frames):
    """Mild finger curl only. Do not touch hand_l/hand_r wrist rotations."""
    arm.animation_data.action = action
    curl = {"01": -0.10, "02": -0.22, "03": -0.16}
    for fr in frames:
        bpy.context.scene.frame_set(fr)
        for side in ("l", "r"):
            for finger in ("index", "middle", "ring", "pinky"):
                for seg, amt in curl.items():
                    n = f"{finger}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode = 'XYZ'
                        pb[n].rotation_euler = (0.0, 0.0, amt)
                        pb[n].keyframe_insert("rotation_euler", frame=fr)
            n = f"thumb_01_{side}"
            if n in pb:
                pb[n].rotation_mode = 'XYZ'
                pb[n].rotation_euler = (0.0, 0.0, -0.025)
                pb[n].keyframe_insert("rotation_euler", frame=fr)
    arm.animation_data.action = None


def make_loop_seam(action):
    """Append the first evaluated Euler pose so the mocap loops without changing its rotation mode."""
    arm.animation_data.action = action
    f0 = int(round(action.frame_range[0]))
    f1 = int(round(action.frame_range[1]))
    for b in pb:
        b.rotation_mode = 'XYZ'
    bpy.context.scene.frame_set(f0)
    bpy.context.view_layer.update()
    first = {b.name: b.rotation_euler.copy() for b in pb}
    close_fr = f1 + 1
    for b in pb:
        b.rotation_mode = 'XYZ'
        b.rotation_euler = first[b.name]
        b.keyframe_insert("rotation_euler", frame=close_fr)
    arm.animation_data.action = None
    return f0, close_fr


old_idle = next((a for a in bpy.data.actions if a.name.lower() == "idle"), None)
if old_idle is not None and old_idle != walk:
    bpy.data.actions.remove(old_idle)

reset_pose()
hand_x = hip_half + H * 0.10
hand_z = hip_z - H * 0.18
hand_y = -H * 0.010
hL = empty("idle_hand_L", (left_sign * hand_x, hand_y, hand_z))
hR = empty("idle_hand_R", (right_sign * hand_x, hand_y, hand_z))
eL = empty("idle_elbow_L", (left_sign * (hand_x + H * 0.075), -H * 0.050, shoulder_z - H * 0.115))
eR = empty("idle_elbow_R", (right_sign * (hand_x + H * 0.075), -H * 0.050, shoulder_z - H * 0.115))
add_ik(laL, hL, eL)
add_ik(laR, hR, eR)
idle = bpy.data.actions.new("idle")
arm.animation_data.action = idle
for fr, breathe in ((1, 0.0), (30, H * 0.0020), (60, 0.0)):
    key_obj(hL, fr, (left_sign * hand_x, hand_y, hand_z + breathe))
    key_obj(hR, fr, (right_sign * hand_x, hand_y, hand_z + breathe))
    if spine:
        pb[spine].rotation_mode = 'XYZ'
        pb[spine].rotation_euler = (0.004 if fr == 30 else 0.0, 0.0, 0.0)
        pb[spine].keyframe_insert("rotation_euler", frame=fr)
    if head:
        pb[head].rotation_mode = 'XYZ'
        pb[head].rotation_euler = (0.0, 0.0, 0.0)
        pb[head].keyframe_insert("rotation_euler", frame=fr)

bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1, frame_end=60, step=1, only_selected=False,
                 visual_keying=True, clear_constraints=True, clear_parents=False,
                 use_current_action=True, bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle = arm.animation_data.action
idle.name = "idle"
idle.use_fake_user = True
set_relaxed_fingers(idle, (1, 30, 60))
for o in (hL, hR, eL, eR):
    if o and o.name in bpy.data.objects:
        bpy.data.objects.remove(o, do_unlink=True)

f0, fend = make_loop_seam(walk)
mid = f0 + max(1, (fend - f0) // 2)
set_relaxed_fingers(walk, (f0, mid, fend))

for a in list(bpy.data.actions):
    if a not in (idle, walk):
        bpy.data.actions.remove(a)

if arm.animation_data is None:
    arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle, walk):
    tr = arm.animation_data.nla_tracks.new()
    tr.name = act.name
    st = tr.strips.new(act.name, int(act.frame_range[0]), act)
    st.action_frame_start = act.frame_range[0]
    st.action_frame_end = act.frame_range[1]
arm.animation_data.action = None

bpy.context.scene.render.fps = 30
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = max(60, int(walk.frame_range[1]))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=os.path.abspath(out),
    export_format='GLB',
    export_animations=True,
    export_animation_mode='ACTIONS',
    export_yup=True,
    export_materials='EXPORT',
    export_apply=False,
)
print("V14_MOCAP_WALK_WRIST_SAFE_HANDS", os.path.abspath(out), "walk_frames", tuple(walk.frame_range))
