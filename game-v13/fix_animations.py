import bpy, os, sys, math
from mathutils import Vector, Quaternion

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
uaL = find("upperarm_l"); uaR = find("upperarm_r")
laL = find("lowerarm_l"); laR = find("lowerarm_r")
handL = find("hand_l"); handR = find("hand_r")
thL = find("thigh_l"); thR = find("thigh_r")
caL = find("calf_l"); caR = find("calf_r")
footL = find("foot_l"); footR = find("foot_r")
required = [pelvis, uaL, uaR, laL, laR, handL, handR, thL, thR, caL, caR, footL, footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
arm.animation_data.action = None

pts = [p for b in bones for p in (b.head_local, b.tail_local)]
zmin = min(p.z for p in pts); zmax = max(p.z for p in pts); H = max(0.1, zmax-zmin)
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
        b.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        b.location = (0.0, 0.0, 0.0)
        b.scale = (1.0, 1.0, 1.0)

def lateral_axis_local(bn):
    axis = bones[bn].matrix_local.to_3x3().inverted() @ Vector((1, 0, 0))
    axis.normalize()
    return axis

def set_sagittal(bn, angle, frame):
    pb[bn].rotation_mode = 'QUATERNION'
    pb[bn].rotation_quaternion = Quaternion(lateral_axis_local(bn), angle)
    pb[bn].keyframe_insert("rotation_quaternion", frame=frame)

def set_finger_relax(action, frames):
    arm.animation_data.action = action
    zaxis = Vector((0,0,1))
    curl = {"01": -0.10, "02": -0.22, "03": -0.16}
    for fr in frames:
        for side in ("l", "r"):
            for finger in ("index", "middle", "ring", "pinky"):
                for seg, amt in curl.items():
                    n = f"{finger}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode = 'QUATERNION'
                        pb[n].rotation_quaternion = Quaternion(zaxis, amt)
                        pb[n].keyframe_insert("rotation_quaternion", frame=fr)
            n = f"thumb_01_{side}"
            if n in pb:
                pb[n].rotation_mode = 'QUATERNION'
                pb[n].rotation_quaternion = Quaternion(zaxis, -0.015)
                pb[n].keyframe_insert("rotation_quaternion", frame=fr)
    arm.animation_data.action = None

reset_pose()
hand_x = hip_half + H * 0.095
hand_z = hip_z - H * 0.175
hand_y = -H * 0.010
hL = empty("idle_hand_L", (left_sign*hand_x, hand_y, hand_z))
hR = empty("idle_hand_R", (right_sign*hand_x, hand_y, hand_z))
eL = empty("idle_elbow_L", (left_sign*(hand_x+H*0.070), -H*0.050, shoulder_z-H*0.115))
eR = empty("idle_elbow_R", (right_sign*(hand_x+H*0.070), -H*0.050, shoulder_z-H*0.115))
add_ik(laL, hL, eL); add_ik(laR, hR, eR)
idle = bpy.data.actions.new("idle"); arm.animation_data.action = idle
for fr, breathe in ((1,0.0),(30,H*0.0020),(60,0.0)):
    key_obj(hL, fr, (left_sign*hand_x, hand_y, hand_z+breathe))
    key_obj(hR, fr, (right_sign*hand_x, hand_y, hand_z+breathe))
    if spine:
        set_sagittal(spine, 0.008 if fr==30 else 0.0, fr)
    if head:
        pb[head].rotation_mode='QUATERNION'; pb[head].rotation_quaternion=(1,0,0,0)
        pb[head].keyframe_insert("rotation_quaternion", frame=fr)

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle=arm.animation_data.action; idle.name="idle"; idle.use_fake_user=True
set_finger_relax(idle,(1,30,60))
for o in (hL,hR,eL,eR):
    if o and o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

reset_pose()
walk = bpy.data.actions.new("walk"); arm.animation_data.action = walk

# Position-IK arms: hands stay close to the body and swing front/back, never sideways.
whL = empty("walk_hand_L", (left_sign*hand_x, hand_y, hand_z))
whR = empty("walk_hand_R", (right_sign*hand_x, hand_y, hand_z))
weL = empty("walk_elbow_L", (left_sign*(hand_x+H*0.085), -H*0.060, shoulder_z-H*0.110))
weR = empty("walk_elbow_R", (right_sign*(hand_x+H*0.085), -H*0.060, shoulder_z-H*0.110))
add_ik(laL, whL, weL); add_ik(laR, whR, weR)

poses = [
    (1,  0.40, -0.10,  0.07,  -0.38, -0.22, -0.12, -1.00),
    (5,  0.31, -0.22,  0.02,  -0.26, -0.34, -0.08, -0.72),
    (9,  0.15, -0.12, -0.02,  -0.06, -0.58,  0.09, -0.38),
    (13,-0.05, -0.08, -0.08,   0.23, -0.72,  0.16,  0.00),
    (17,-0.38, -0.22, -0.12,   0.40, -0.10,  0.07,  1.00),
    (21,-0.26, -0.34, -0.08,   0.31, -0.22,  0.02,  0.72),
    (25,-0.06, -0.58,  0.09,   0.15, -0.12, -0.02,  0.38),
    (29, 0.23, -0.72,  0.16,  -0.05, -0.08, -0.08,  0.00),
    (33, 0.40, -0.10,  0.07,  -0.38, -0.22, -0.12, -1.00),
]

for fr, rt, rk, rf, lt, lk, lf, phase in poses:
    for bn, ang in ((thR,rt),(caR,rk),(footR,rf),(thL,lt),(caL,lk),(footL,lf)):
        set_sagittal(bn, ang, fr)

    bob = H * (0.008 if abs(phase) < 0.15 else (0.003 if abs(phase) < 0.6 else -0.003))
    pb[pelvis].location = (0.0, 0.0, bob)
    pb[pelvis].keyframe_insert("location", frame=fr)
    pb[pelvis].rotation_mode='QUATERNION'; pb[pelvis].rotation_quaternion=(1,0,0,0)
    pb[pelvis].keyframe_insert("rotation_quaternion", frame=fr)

    if spine:
        set_sagittal(spine, 0.028, fr)

    swing = H * 0.085 * phase
    lift = H * 0.010 * abs(phase)
    key_obj(whL, fr, (left_sign*hand_x, hand_y + swing, hand_z + lift))
    key_obj(whR, fr, (right_sign*hand_x, hand_y - swing, hand_z + lift))

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=33,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
walk=arm.animation_data.action; walk.name="walk"; walk.use_fake_user=True
set_finger_relax(walk, tuple(p[0] for p in poses))
for o in (whL,whR,weL,weR):
    if o and o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

for fc in walk.fcurves:
    for kp in fc.keyframe_points:
        kp.interpolation='LINEAR'

for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]
arm.animation_data.action=None

bpy.context.scene.render.fps=30
bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V14_EIGHT_PHASE_WALK_WRIST_SAFE",os.path.abspath(out))
