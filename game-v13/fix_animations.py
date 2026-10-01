import bpy, os, sys, math
from mathutils import Vector, Matrix, Quaternion

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

pelvis=find("pelvis")
uaL=find("upperarm_l"); uaR=find("upperarm_r")
laL=find("lowerarm_l"); laR=find("lowerarm_r")
handL=find("hand_l"); handR=find("hand_r")
thL=find("thigh_l"); thR=find("thigh_r")
caL=find("calf_l"); caR=find("calf_r")
footL=find("foot_l"); footR=find("foot_r")
head=find("head")\nspine=find("spine_02","spine_01")
required=[pelvis,uaL,uaR,laL,laR,handL,handR,thL,thR,caL,caR,footL,footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

# We intentionally rebuild ONLY idle + walk from anatomical IK targets.
# This avoids guessing bone Euler axes, which caused the broken wrists and sideways/stiff legs.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)
arm.animation_data.action=None

pts=[p for b in bones for p in (b.head_local,b.tail_local)]
H=max(0.1,max(p.z for p in pts)-min(p.z for p in pts))
forward=Vector((0.0,-1.0,0.0))

def local_head(bn):
    return bones[bn].head_local.copy()

def world_point(v):
    return arm.matrix_world @ Vector(v)

def make_target(name,bone_name=None):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    if bone_name:
        e.matrix_world=arm.matrix_world @ bones[bone_name].matrix_local
    return e

def set_target_local(obj,v,frame=None):
    obj.location=world_point(v)
    if frame is not None:
        obj.keyframe_insert("location",frame=frame)

def add_ik(end_bone,target,pole):
    c=pb[end_bone].constraints.new("IK")
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False
    c.iterations=64
    return c

def add_copy_world_rotation(bone_name,target):
    c=pb[bone_name].constraints.new("COPY_ROTATION")
    c.target=target
    c.target_space='WORLD'
    c.owner_space='WORLD'
    c.mix_mode='REPLACE'
    return c

def clear_pose():
    for b in pb:
        b.location=(0,0,0)
        b.scale=(1,1,1)
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)

def local_axis_for_world(bn,axis):
    v=bones[bn].matrix_local.to_3x3().inverted() @ Vector(axis)
    v.normalize()
    return v

def set_bone_axis_angle(bn,world_axis,angle,frame):
    if not bn:
        return
    pb[bn].rotation_mode='QUATERNION'
    pb[bn].rotation_quaternion=Quaternion(local_axis_for_world(bn,world_axis),angle)
    pb[bn].keyframe_insert("rotation_quaternion",frame=frame)

def prepare_target_rotation(obj):
    obj.rotation_mode='QUATERNION'
    return obj.rotation_quaternion.copy()

def set_target_pitch(obj,rest_q,angle,frame):
    obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=Quaternion(Vector((1.0,0.0,0.0)),angle) @ rest_q
    obj.keyframe_insert("rotation_quaternion",frame=frame)

def finger_relax(action,frames):
    # MakeHuman game-engine rig uses local Z as the anatomical finger curl axis.
    arm.animation_data.action=action
    curl={"01":-0.16,"02":-0.30,"03":-0.22}
    for fr in frames:
        bpy.context.scene.frame_set(fr)
        for side in ("l","r"):
            for finger in ("index","middle","ring","pinky"):
                for seg,ang in curl.items():
                    bn=f"{finger}_{seg}_{side}"
                    if bn in pb:
                        pb[bn].rotation_mode='XYZ'
                        pb[bn].rotation_euler=(0.0,0.0,ang)
                        pb[bn].keyframe_insert("rotation_euler",frame=fr)
            for seg,ang in (("01",-0.055),("02",-0.10),("03",-0.075)):
                bn=f"thumb_{seg}_{side}"
                if bn in pb:
                    pb[bn].rotation_mode='XYZ'
                    pb[bn].rotation_euler=(0.0,0.0,ang)
                    pb[bn].keyframe_insert("rotation_euler",frame=fr)
    arm.animation_data.action=None

def build_constraints(prefix):
    # Wrist / ankle targets keep their REST world orientation while their positions move.
    hL=make_target(prefix+"_HandL",handL)
    hR=make_target(prefix+"_HandR",handR)
    fL=make_target(prefix+"_FootL",footL)
    fR=make_target(prefix+"_FootR",footR)
    eL=make_target(prefix+"_ElbowPoleL")
    eR=make_target(prefix+"_ElbowPoleR")
    kL=make_target(prefix+"_KneePoleL")
    kR=make_target(prefix+"_KneePoleR")

    add_ik(laL,hL,eL); add_ik(laR,hR,eR)
    # Let the hands inherit the solved forearm orientation. Keeping the T-pose wrist
    # rotation in world space was what made the palms look broken/open.
    add_ik(caL,fL,kL); add_ik(caR,fR,kR)
    add_copy_world_rotation(footL,fL); add_copy_world_rotation(footR,fR)
    return hL,hR,fL,fR,eL,eR,kL,kR

def bake_action(name,start,end):
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=False,
                     visual_keying=True,clear_constraints=True,clear_parents=False,
                     use_current_action=True,bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act=arm.animation_data.action
    act.name=name
    act.use_fake_user=True
    return act

# ---------- Neutral idle ----------
clear_pose()
idle=bpy.data.actions.new("idle")
arm.animation_data.action=idle
hL,hR,fL,fR,eL,eR,kL,kR=build_constraints("Idle")

wristL=local_head(handL); wristR=local_head(handR)
ankleL=local_head(footL); ankleR=local_head(footR)
shoulderL=local_head(uaL); shoulderR=local_head(uaR)
hipL=local_head(thL); hipR=local_head(thR)
kneeL=local_head(caL); kneeR=local_head(caR)
left_sign=1.0 if hipL.x > hipR.x else -1.0
right_sign=-left_sign

# Put the hands beside the thighs instead of reusing the T-pose wrist positions.
hand_side=H*0.020
hand_drop=H*0.140
idle_hL=Vector((hipL.x + left_sign*hand_side, hipL.y-H*0.015, hipL.z-hand_drop))
idle_hR=Vector((hipR.x + right_sign*hand_side, hipR.y-H*0.015, hipR.z-hand_drop))
pole_out=H*0.038
pole_back=H*0.022
idle_eL=Vector((shoulderL.x+left_sign*pole_out, shoulderL.y+pole_back, shoulderL.z-H*0.095))
idle_eR=Vector((shoulderR.x+right_sign*pole_out, shoulderR.y+pole_back, shoulderR.z-H*0.095))

# Keep each foot almost directly below its own hip, avoiding the wide-legged stance.
foot_side=H*0.005
base_footL=Vector((hipL.x+left_sign*foot_side, ankleL.y, ankleL.z))
base_footR=Vector((hipR.x+right_sign*foot_side, ankleR.y, ankleR.z))
knee_forward=H*0.120
idle_kL=kneeL + Vector((0.0,-knee_forward,0.0))
idle_kR=kneeR + Vector((0.0,-knee_forward,0.0))

for fr,breathe in ((1,0.0),(30,H*0.003),(60,0.0)):
    set_target_local(hL,idle_hL+Vector((0,0,breathe)),fr)
    set_target_local(hR,idle_hR+Vector((0,0,breathe)),fr)
    set_target_local(fL,base_footL,fr); set_target_local(fR,base_footR,fr)
    set_target_local(eL,idle_eL,fr); set_target_local(eR,idle_eR,fr)
    set_target_local(kL,idle_kL,fr); set_target_local(kR,idle_kR,fr)
    pb[pelvis].location=(0.0,0.0,breathe*0.20)
    pb[pelvis].keyframe_insert("location",frame=fr)
    if spine:
        set_bone_axis_angle(spine,(1,0,0),math.radians(1.5),fr)
    if head:
        set_bone_axis_angle(head,(1,0,0),math.radians(-0.8),fr)

idle=bake_action("idle",1,60)
finger_relax(idle,(1,30,60))
for o in (hL,hR,fL,fR,eL,eR,kL,kR):
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

# ---------- Natural 8-phase in-place walk ----------
clear_pose()
walk=bpy.data.actions.new("walk")
arm.animation_data.action=walk
hL,hR,fL,fR,eL,eR,kL,kR=build_constraints("Walk")

# frame, left_y, right_y, left_lift, right_lift, body_bob
# Negative Y is forward for this MakeHuman asset.
step=H*0.105
lift=H*0.028
phases=[
    (1,  -step,      step*0.82, 0.000,      0.000,      0.000), # L contact
    (5,  -step*0.78, step*0.55, 0.000,      0.000,     -H*0.010), # down
    (9,  -step*0.22, 0.000,     0.000,      lift*0.72,  H*0.002), # R passing
    (13,  step*0.38,-step*0.62,  0.000,      lift,       H*0.010), # R swing/up
    (17,  step*0.82,-step,       0.000,      0.000,      0.000), # R contact
    (21,  step*0.55,-step*0.78,  0.000,      0.000,     -H*0.010), # down
    (25,  0.000,    -step*0.22,  lift*0.72,  0.000,      H*0.002), # L passing
    (29, -step*0.62, step*0.38,  lift,       0.000,      H*0.010), # L swing/up
    (33, -step,      step*0.82,  0.000,      0.000,      0.000), # loop
]

# Calm heel-strike -> flat -> toe-off roll, matching a normal slow walk.
# Negative pitch lifts the toe; positive pitch gives toe-off.
foot_pitch = {
    1:(math.radians(-7), math.radians(11)),
    5:(0.0, math.radians(6)),
    9:(0.0, math.radians(-4)),
    13:(math.radians(9), math.radians(-6)),
    17:(math.radians(11), math.radians(-7)),
    21:(math.radians(6), 0.0),
    25:(math.radians(-4), 0.0),
    29:(math.radians(-6), math.radians(9)),
    33:(math.radians(-7), math.radians(11)),
}
rest_foot_rot_L=prepare_target_rotation(fL)
rest_foot_rot_R=prepare_target_rotation(fR)

# Arms swing opposite the legs, but hands stay close to the torso.
hand_swing=H*0.045
for fr,ly,ry,llift,rlift,bob in phases:
    lf=base_footL + Vector((0.0,ly,llift))
    rf=base_footR + Vector((0.0,ry,rlift))
    set_target_local(fL,lf,fr); set_target_local(fR,rf,fr)
    lp,rp=foot_pitch[fr]
    set_target_pitch(fL,rest_foot_rot_L,lp,fr)
    set_target_pitch(fR,rest_foot_rot_R,rp,fr)

    # Knee pole follows the leg slightly so the knee bends forward rather than sideways/back.
    set_target_local(kL,Vector((kneeL.x,kneeL.y-knee_forward+ly*0.12,kneeL.z+llift*0.20)),fr)
    set_target_local(kR,Vector((kneeR.x,kneeR.y-knee_forward+ry*0.12,kneeR.z+rlift*0.20)),fr)

    # Contralateral arm swing.
    larm_y = -ly/step * hand_swing
    rarm_y = -ry/step * hand_swing
    arm_lift=H*0.006*max(abs(larm_y),abs(rarm_y))/max(hand_swing,1e-6)
    lh=idle_hL + Vector((0.0,larm_y,arm_lift))
    rh=idle_hR + Vector((0.0,rarm_y,arm_lift))
    set_target_local(hL,lh,fr); set_target_local(hR,rh,fr)
    set_target_local(eL,Vector((idle_eL.x,idle_eL.y+larm_y*0.52,idle_eL.z+arm_lift*0.35)),fr)
    set_target_local(eR,Vector((idle_eR.x,idle_eR.y+rarm_y*0.52,idle_eR.z+arm_lift*0.35)),fr)

    # Shift weight slightly toward the planted leg, with subtle counter-rotation.
    support = left_sign if llift <= rlift else right_sign
    side_shift = support * H*0.006
    pb[pelvis].location=(side_shift,0.0,bob)
    pb[pelvis].keyframe_insert("location",frame=fr)
    yaw = math.radians(1.8) * (-ly/step)
    set_bone_axis_angle(pelvis,(0,0,1),yaw,fr)
    if spine:
        set_bone_axis_angle(spine,(0,0,1),-yaw*0.70,fr)
    if head:
        set_bone_axis_angle(head,(0,0,1),yaw*0.15,fr)

walk=bake_action("walk",1,33)
finger_relax(walk,(1,5,9,13,17,21,25,29,33))
for o in (hL,hR,fL,fR,eL,eR,kL,kR):
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

# Keep only the two clips used by the game.
for a in list(bpy.data.actions):
    if a not in (idle,walk):
        bpy.data.actions.remove(a)
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new()
    tr.name=act.name
    st=tr.strips.new(act.name,int(act.frame_range[0]),act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]
arm.animation_data.action=None

bpy.context.scene.render.fps=30
bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
                          export_animations=True,export_animation_mode='ACTIONS',
                          export_yup=True,export_materials='EXPORT',export_apply=False)
print("V15_IK_WALK_NEUTRAL_WRISTS",os.path.abspath(out))
