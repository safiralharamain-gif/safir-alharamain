import bpy, os, sys, math
from mathutils import Vector, Quaternion

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src,out=argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")
arm.animation_data_create()
pb=arm.pose.bones
bones=arm.data.bones

def find(*names):
    for n in names:
        if n in pb: return n
    return None

pelvis=find("pelvis")
spine=find("spine_02","spine_01")
head=find("head")
uaL=find("upperarm_l"); uaR=find("upperarm_r")
laL=find("lowerarm_l"); laR=find("lowerarm_r")
handL=find("hand_l"); handR=find("hand_r")
thL=find("thigh_l"); thR=find("thigh_r")
caL=find("calf_l"); caR=find("calf_r")
footL=find("foot_l"); footR=find("foot_r")
ballL=find("ball_l"); ballR=find("ball_r")
required=[pelvis,uaL,uaR,laL,laR,handL,handR,thL,thR,caL,caR,footL,footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

# Remove imported animation actions. V13 authors a clean sagittal walk directly on this exact rig.
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

pts=[p for b in bones for p in (b.head_local,b.tail_local)]
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); H=max(0.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*0.5
left_sign=1.0 if bones[uaL].head_local.x>bones[uaR].head_local.x else -1.0
right_sign=-left_sign
hip_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))

def world(local):
    return arm.matrix_world @ Vector(local)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.location=world(local)
    return e

def key_obj(obj,fr,local):
    obj.location=world(local)
    obj.keyframe_insert("location",frame=fr)

def add_ik(bone,target,pole,chain=2):
    c=pb[bone].constraints.new("IK")
    c.target=target
    c.pole_target=pole
    c.chain_count=chain
    c.use_rotation=False

def reset_pose():
    for b in pb:
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)
        b.location=(0,0,0)
        b.scale=(1,1,1)

# Flexion/extension must rotate around the CHARACTER'S left-right axis, not an arbitrary
# bone-local X axis. Convert armature-space X into each bone's own local rest space.
def lateral_axis_local(bn):
    axis = bones[bn].matrix_local.to_3x3().inverted() @ Vector((1,0,0))
    axis.normalize()
    return axis

def set_sagittal_rotation(bn,angle,frame):
    pb[bn].rotation_mode='QUATERNION'
    pb[bn].rotation_quaternion=Quaternion(lateral_axis_local(bn),angle)
    pb[bn].keyframe_insert("rotation_quaternion",frame=frame)

def finger_flex_axis_local(bn):
    # Fingers extend sideways in the MakeHuman rest pose; flexion is around armature-space Y.
    axis=bones[bn].matrix_local.to_3x3().inverted() @ Vector((0,1,0))
    if axis.length<1e-6: axis=Vector((1,0,0))
    axis.normalize()
    return axis

def relax_hands(action,frames):
    arm.animation_data.action=action
    for fr in frames:
        bpy.context.scene.frame_set(fr)
        for side in ("l","r"):
            # Wrist neutral. Keep hand bone aligned with the forearm.
            hn=f"hand_{side}"
            if hn in pb:
                pb[hn].rotation_mode='QUATERNION'
                pb[hn].rotation_quaternion=(1,0,0,0)
                pb[hn].keyframe_insert("rotation_quaternion",frame=fr)
            # Natural loose curl, stronger at the middle phalanges.
            for finger in ("index","middle","ring","pinky"):
                for seg,amt in (("01",0.24),("02",0.46),("03",0.30)):
                    n=f"{finger}_{seg}_{side}"
                    if n in pb:
                        sign=1.0 if side=="l" else -1.0
                        pb[n].rotation_mode='QUATERNION'
                        pb[n].rotation_quaternion=Quaternion(finger_flex_axis_local(n),sign*amt)
                        pb[n].keyframe_insert("rotation_quaternion",frame=fr)
            # Thumb slightly folded toward the palm, not sticking out.
            for seg,amt in (("01",0.16),("02",0.22),("03",0.14)):
                n=f"thumb_{seg}_{side}"
                if n in pb:
                    sign=1.0 if side=="l" else -1.0
                    pb[n].rotation_mode='QUATERNION'
                    pb[n].rotation_quaternion=Quaternion(finger_flex_axis_local(n),sign*amt)
                    pb[n].keyframe_insert("rotation_quaternion",frame=fr)
    arm.animation_data.action=None


# ---------- relaxed idle ----------
reset_pose()
hand_x=hip_half+H*0.11
hand_z=hip_z-H*0.17
hand_y=-H*0.015
hL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
hR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
eL=empty("idle_elbow_L",(left_sign*(hand_x+H*0.095),-H*0.060,shoulder_z-H*0.12))
eR=empty("idle_elbow_R",(right_sign*(hand_x+H*0.095),-H*0.060,shoulder_z-H*0.12))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)
idle=bpy.data.actions.new("idle"); arm.animation_data.action=idle
for fr,breathe in ((1,0.0),(30,H*0.0025),(60,0.0)):
    key_obj(hL,fr,(left_sign*hand_x,hand_y,hand_z+breathe))
    key_obj(hR,fr,(right_sign*hand_x,hand_y,hand_z+breathe))
    if spine:
        pb[spine].rotation_mode='XYZ'; pb[spine].rotation_euler=(0.006 if fr==30 else 0,0,0)
        pb[spine].keyframe_insert("rotation_euler",frame=fr)
    if head:
        pb[head].rotation_mode='XYZ'; pb[head].rotation_euler=(0,0,0)
        pb[head].keyframe_insert("rotation_euler",frame=fr)
bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle=arm.animation_data.action; idle.name="idle"; idle.use_fake_user=True
relax_hands(idle,(1,30,60))
for o in (hL,hR,eL,eR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# ---------- clean direct-bone walk ----------
# Uses the MakeHuman game-engine rig's sagittal X rotation axis.
# No leg IK, no pole targets: knees cannot kick sideways.
reset_pose()
walk=bpy.data.actions.new("walk"); arm.animation_data.action=walk

# Arms are position-IK only; this keeps hands beside the body and avoids twisted wrists.
whL=empty("walk_hand_L",(left_sign*hand_x,hand_y,hand_z))
whR=empty("walk_hand_R",(right_sign*hand_x,hand_y,hand_z))
weL=empty("walk_elbow_L",(left_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
weR=empty("walk_elbow_R",(right_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
add_ik(laL,whL,weL); add_ik(laR,whR,weR)

# Proven MakeHuman-style walk poses: contact, passing, opposite contact, passing, loop.
A=0.29
poses=[
    (1,   A,-0.10, 0.08,   -A,-0.24,-0.14,   -1.0),
    (9,   0,-0.12, 0.00,    0,-0.56, 0.08,    0.0),
    (17, -A,-0.24,-0.14,    A,-0.10, 0.08,    1.0),
    (25,  0,-0.56, 0.08,    0,-0.12, 0.00,    0.0),
    (33,  A,-0.10, 0.08,   -A,-0.24,-0.14,   -1.0),
]
arm_swing=H*0.035
for fr,rt,rc,rf,lt,lc,lf,phase in poses:
    for bn,ang in ((thR,rt),(caR,rc),(footR,rf),(thL,lt),(caL,lc),(footL,lf)):
        set_sagittal_rotation(bn,ang,fr)
    # very small body bob and forward lean, with absolutely no roll/yaw
    pb[pelvis].location=(0,0,H*(0.006 if phase==0 else 0.0))
    pb[pelvis].keyframe_insert("location",frame=fr)
    pb[pelvis].rotation_mode='QUATERNION'; pb[pelvis].rotation_quaternion=(1,0,0,0)
    pb[pelvis].keyframe_insert("rotation_quaternion",frame=fr)
    if spine:
        set_sagittal_rotation(spine,0.018,fr)
    # counter-swing hands gently forward/back while staying clear of thighs
    key_obj(whL,fr,(left_sign*hand_x,hand_y+arm_swing*phase,hand_z))
    key_obj(whR,fr,(right_sign*hand_x,hand_y-arm_swing*phase,hand_z))

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=33,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
walk=arm.animation_data.action; walk.name="walk"; walk.use_fake_user=True
relax_hands(walk,(1,9,17,25,33))
for o in (whL,whR,weL,weR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# Export both clips cleanly.
if arm.animation_data is None: arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(tr)
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
print("V13_DIRECT_SAGITTAL_WALK",os.path.abspath(out))
