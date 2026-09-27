import bpy, os, sys, math, mathutils
from mathutils import Vector, Matrix

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1]; walk_bvh=argv[2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No target armature")

# Remove the rough generated actions. V11 rebuilds only a clean idle + a MakeHuman-native walk.
if arm.animation_data:
    arm.animation_data_clear()
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)

pb=arm.pose.bones
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

def target_bone(*names):
    for n in names:
        if n in pb: return n
    return None

pelvis=target_bone("pelvis")
uaL=target_bone("upperarm_l"); uaR=target_bone("upperarm_r")
laL=target_bone("lowerarm_l"); laR=target_bone("lowerarm_r")
handL=target_bone("hand_l"); handR=target_bone("hand_r")
thL=target_bone("thigh_l"); thR=target_bone("thigh_r")
caL=target_bone("calf_l"); caR=target_bone("calf_r")
foL=target_bone("foot_l"); foR=target_bone("foot_r")
sp2=target_bone("spine_02","spine_01")
head=target_bone("head")
if any(x is None for x in [pelvis,uaL,uaR,laL,laR,thL,thR,caL,caR]):
    raise SystemExit("Required target bones missing")

bones=arm.data.bones
allpts=[]
for b in bones:
    allpts += [b.head_local,b.tail_local]
zmin=min(p.z for p in allpts); zmax=max(p.z for p in allpts); H=max(.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*.5
left_sign=1.0 if bones[uaL].head_local.x > bones[uaR].head_local.x else -1.0
right_sign=-left_sign
print("V11 TARGET H",H,"left_sign",left_sign)

# ---------- relaxed IDLE made from this exact rig ----------
def arm_local_to_world(v):
    return arm.matrix_world @ Vector(v)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.empty_display_type='PLAIN_AXES'
    e.empty_display_size=H*.03
    e.location=arm_local_to_world(local)
    return e

def add_ik(bone,target,pole):
    c=pb[bone].constraints.new('IK')
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False

# Use thigh spacing as a body-aware guide, not a guessed absolute hand position.
leg_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))
hand_x=leg_half + H*.105
hand_z=hip_z-H*.17
hand_y=-H*.018
tL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
tR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
pL=empty("idle_elbow_L",(left_sign*(hand_x+H*.12),-H*.08,shoulder_z-H*.10))
pR=empty("idle_elbow_R",(right_sign*(hand_x+H*.12),-H*.08,shoulder_z-H*.10))
add_ik(laL,tL,pL); add_ik(laR,tR,pR)

idle=bpy.data.actions.new("idle")
arm.animation_data_create().action=idle
# Small breathing motion, hands remain comfortably outside the thighs.
for fr,breathe in [(1,0.0),(30,H*.004),(60,0.0)]:
    tL.location=arm_local_to_world((left_sign*hand_x,hand_y,hand_z+breathe))
    tR.location=arm_local_to_world((right_sign*hand_x,hand_y,hand_z+breathe))
    tL.keyframe_insert("location",frame=fr)
    tR.keyframe_insert("location",frame=fr)
    if sp2:
        pb[sp2].rotation_mode='XYZ'
        pb[sp2].rotation_euler=(0.015 if fr==30 else 0.0,0,0)
        pb[sp2].keyframe_insert("rotation_euler",frame=fr)

bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
if arm.animation_data and arm.animation_data.action:
    arm.animation_data.action.name="idle"
    idle=arm.animation_data.action
idle.use_fake_user=True
arm.animation_data.action=None
for o in [tL,tR,pL,pR]:
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

# Relax fingers in idle so palms do not look broken/spread.
finger_axes={}
for side in ("l","r"):
    for f in ("index","middle","ring","pinky"):
        for seg,amt in (("01",-0.14),("02",-0.30),("03",-0.24)):
            n=f"{f}_{seg}_{side}"
            if n in pb: finger_axes[n]=amt
if finger_axes:
    arm.animation_data.action=idle
    for fr in (1,30,60):
        for n,amt in finger_axes.items():
            pb[n].rotation_mode='XYZ'
            pb[n].rotation_euler=(0,0,amt)
            pb[n].keyframe_insert("rotation_euler",frame=fr)
    arm.animation_data.action=None


# ---------- clean procedural walk/run on THIS exact rig ----------
# No BVH retargeting: targets stay in the character's own skeleton space, eliminating sideways lean.

def pose_world(v):
    return arm.matrix_world @ Vector(v)

# Arm targets are further from the thighs than V10/V11 initial attempts.
base_hand_x=leg_half + H*.145
base_hand_z=hip_z-H*.165
base_hand_y=-H*.015

# Foot rest positions from the actual skeleton.
footL_rest=bones[caL].tail_local.copy()
footR_rest=bones[caR].tail_local.copy()
knee_z=(bones[thL].tail_local.z+bones[thR].tail_local.z)*.5

def key_loc(obj,frame,local):
    obj.location=pose_world(local)
    obj.keyframe_insert("location",frame=frame)

def make_targets(prefix):
    hL=empty(prefix+"_hand_L",(left_sign*base_hand_x,base_hand_y,base_hand_z))
    hR=empty(prefix+"_hand_R",(right_sign*base_hand_x,base_hand_y,base_hand_z))
    eL=empty(prefix+"_elbow_L",(left_sign*(base_hand_x+H*.16),-H*.10,shoulder_z-H*.12))
    eR=empty(prefix+"_elbow_R",(right_sign*(base_hand_x+H*.16),-H*.10,shoulder_z-H*.12))
    fL=empty(prefix+"_foot_L",footL_rest)
    fR=empty(prefix+"_foot_R",footR_rest)
    kL=empty(prefix+"_knee_L",(bones[thL].head_local.x,-H*.42,knee_z))
    kR=empty(prefix+"_knee_R",(bones[thR].head_local.x,-H*.42,knee_z))
    add_ik(laL,hL,eL); add_ik(laR,hR,eR)
    add_ik(caL,fL,kL); add_ik(caR,fR,kR)
    return [hL,hR,eL,eR,fL,fR,kL,kR]

def bake_motion(name,end_frame,stride,lift,hand_swing,run=False):
    # reset all rotations/locations before creating targets
    for b in pb:
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)
        b.location=(0,0,0)
        b.scale=(1,1,1)

    targets=make_targets(name)
    hL,hR,eL,eR,fL,fR,kL,kR=targets

    action=bpy.data.actions.new(name)
    arm.animation_data_create().action=action

    # Seamless four-phase cycle: contact -> pass -> opposite contact -> pass -> contact.
    phases=[(1,1.0),(1+end_frame//4,0.0),(1+end_frame//2,-1.0),
            (1+3*end_frame//4,0.0),(1+end_frame,1.0)]
    for fr,p in phases:
        # feet move ONLY along local Y (forward/back), never sideways
        l=footL_rest.copy(); r=footR_rest.copy()
        l.y += -stride*p
        r.y += stride*p
        # lift swing foot during pass phases
        if abs(p)<0.01:
            if fr < 1+end_frame//2:
                r.z += lift
                r.y -= stride*.12
            else:
                l.z += lift
                l.y -= stride*.12
        key_loc(fL,fr,l); key_loc(fR,fr,r)

        # hands stay outside thighs, counter-swing gently along Y
        key_loc(hL,fr,(left_sign*base_hand_x,base_hand_y+hand_swing*p,base_hand_z))
        key_loc(hR,fr,(right_sign*base_hand_x,base_hand_y-hand_swing*p,base_hand_z))

        # knee poles remain straight forward and slightly outward
        key_loc(kL,fr,(bones[thL].head_local.x,-H*.42,knee_z))
        key_loc(kR,fr,(bones[thR].head_local.x,-H*.42,knee_z))

    # Keep torso vertical; only tiny forward pitch for run, no roll/yaw.
    if sp2:
        pb[sp2].rotation_mode='XYZ'
        for fr in [1,1+end_frame//2,1+end_frame]:
            pb[sp2].rotation_euler=(0.035 if run else 0.012,0,0)
            pb[sp2].keyframe_insert("rotation_euler",frame=fr)

    # Keep pelvis centered: no lateral roll at all.
    if pelvis:
        pb[pelvis].rotation_mode='XYZ'
        for fr in [1,1+end_frame//2,1+end_frame]:
            pb[pelvis].rotation_euler=(0,0,0)
            pb[pelvis].keyframe_insert("rotation_euler",frame=fr)
            pb[pelvis].location=(0,0,0)
            pb[pelvis].keyframe_insert("location",frame=fr)

    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=1,frame_end=1+end_frame,step=1,only_selected=False,
                     visual_keying=True,clear_constraints=True,clear_parents=False,
                     use_current_action=True,bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')

    baked=arm.animation_data.action
    baked.name=name
    baked.use_fake_user=True

    # Relax all fingers in every clip and hold wrists neutral.
    for fr in [1,1+end_frame//4,1+end_frame//2,1+3*end_frame//4,1+end_frame]:
        for side in ("l","r"):
            for fng in ("index","middle","ring","pinky"):
                for seg,amt in (("01",-0.12),("02",-0.24),("03",-0.18)):
                    n=f"{fng}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode='XYZ'
                        pb[n].rotation_euler=(0,0,amt)
                        pb[n].keyframe_insert("rotation_euler",frame=fr)
            hn="hand_"+side
            if hn in pb:
                pb[hn].rotation_mode='XYZ'
                pb[hn].rotation_euler=(0,0,0)
                pb[hn].keyframe_insert("rotation_euler",frame=fr)

    arm.animation_data.action=None
    for o in targets:
        if o and o.name in bpy.data.objects:
            bpy.data.objects.remove(o,do_unlink=True)
    return baked

walk=bake_motion("walk",32,H*.095,H*.038,H*.050,False)
run=bake_motion("run",24,H*.145,H*.060,H*.080,True)

# NLA tracks keep all three clips attached for deterministic glTF export.
for act in (idle,walk,run):
    tr=arm.animation_data.nla_tracks.new()
    tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]

# Clean rest frame before export.
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V11_PROCEDURAL_ANIMATED",os.path.abspath(out))
