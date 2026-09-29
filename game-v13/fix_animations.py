import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src,out=argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature")
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
footL=find("foot_l"); footR=find("foot_r")
required=[pelvis,uaL,uaR,laL,laR,handL,handR,thL,thR,footL,footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

# Find the MakeHuman-native mocap walk imported by make-human.py.
walk_src=next((a for a in bpy.data.actions if a.name.lower().startswith("walk")),None)
if walk_src is None:
    raise SystemExit("Native walk action missing")
walk=walk_src.copy()
walk.name="walk"
walk.use_fake_user=True

# Delete everything except the copied walk; idle will be rebuilt cleanly.
for a in list(bpy.data.actions):
    if a != walk:
        bpy.data.actions.remove(a)

# Character metrics.
pts=[p for b in bones for p in (b.head_local,b.tail_local)]
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); H=max(0.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*0.5
left_sign=1.0 if bones[uaL].head_local.x>bones[uaR].head_local.x else -1.0
right_sign=-left_sign
hip_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))

def wpos(local):
    return arm.matrix_world @ Vector(local)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.location=wpos(local)
    return e

def add_ik(bone,target,pole):
    c=pb[bone].constraints.new("IK")
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False
    return c

def key(obj,frame,local):
    obj.location=wpos(local)
    obj.keyframe_insert("location",frame=frame)

def reset_pose():
    for b in pb:
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)
        b.location=(0,0,0)
        b.scale=(1,1,1)

def relax_fingers(action,frames):
    arm.animation_data.action=action
    for fr in frames:
        bpy.context.scene.frame_set(int(fr))
        for side in ("l","r"):
            hn=f"hand_{side}"
            if hn in pb:
                pb[hn].rotation_mode='QUATERNION'
                pb[hn].rotation_quaternion=(1,0,0,0)
                pb[hn].keyframe_insert("rotation_quaternion",frame=fr)
            thumb=f"thumb_01_{side}"
            if thumb in pb:
                pb[thumb].rotation_mode='XYZ'
                pb[thumb].rotation_euler=(0.05,0.0,-0.18 if side=="l" else 0.18)
                pb[thumb].keyframe_insert("rotation_euler",frame=fr)
            for finger in ("index","middle","ring","pinky"):
                for seg,amt in (("01",-0.12),("02",-0.28),("03",-0.20)):
                    n=f"{finger}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode='XYZ'
                        pb[n].rotation_euler=(0,0,amt)
                        pb[n].keyframe_insert("rotation_euler",frame=fr)

# -------- idle: approved relaxed stance --------
reset_pose()
hand_gap=hip_half+H*0.105
hand_z=hip_z-H*0.17
hand_y=-H*0.015
hL=empty("idle_hand_L",(left_sign*hand_gap,hand_y,hand_z))
hR=empty("idle_hand_R",(right_sign*hand_gap,hand_y,hand_z))
eL=empty("idle_elbow_L",(left_sign*(hand_gap+H*0.10),-H*0.055,shoulder_z-H*0.12))
eR=empty("idle_elbow_R",(right_sign*(hand_gap+H*0.10),-H*0.055,shoulder_z-H*0.12))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)
idle=bpy.data.actions.new("idle")
arm.animation_data.action=idle
for fr,breathe in ((1,0.0),(30,H*0.003),(60,0.0)):
    key(hL,fr,(left_sign*hand_gap,hand_y,hand_z+breathe))
    key(hR,fr,(right_sign*hand_gap,hand_y,hand_z+breathe))
    if spine:
        pb[spine].rotation_mode='XYZ'
        pb[spine].rotation_euler=(0.006 if fr==30 else 0.0,0.0,0.0)
        pb[spine].keyframe_insert("rotation_euler",frame=fr)
    if head:
        pb[head].rotation_mode='XYZ'
        pb[head].rotation_euler=(0,0,0)
        pb[head].keyframe_insert("rotation_euler",frame=fr)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle=arm.animation_data.action; idle.name="idle"; idle.use_fake_user=True
relax_fingers(idle,(1,30,60))
for o in (hL,hR,eL,eR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# -------- walk: keep mocap LEGS/TORSO, replace only the arms/hands --------
# This avoids the previous distorted wrists while retaining genuine hip/knee/ankle motion.
walk_fixed=walk.copy()
walk_fixed.name="walk"
walk_fixed.use_fake_user=True
arm.animation_data.action=walk_fixed
f0=int(round(walk_fixed.frame_range[0])); f1=int(round(walk_fixed.frame_range[1]))
if f1<=f0: raise SystemExit("Walk action has no duration")
cycle=f1-f0

# Sample old walk first so leg/body motion remains untouched after baking.
# Hand targets are authored in armature-local coordinates, safely outside the thighs.
whL=empty("walk_hand_L",(left_sign*hand_gap,hand_y,hand_z))
whR=empty("walk_hand_R",(right_sign*hand_gap,hand_y,hand_z))
weL=empty("walk_elbow_L",(left_sign*(hand_gap+H*0.105),-H*0.06,shoulder_z-H*0.12))
weR=empty("walk_elbow_R",(right_sign*(hand_gap+H*0.105),-H*0.06,shoulder_z-H*0.12))
add_ik(laL,whL,weL); add_ik(laR,whR,weR)

# Four clean swing phases + loop. Small swing looks natural and keeps hands away from trousers.
for frac in (0.0,0.25,0.5,0.75,1.0):
    fr=f0+int(round(cycle*frac))
    phase=math.sin(frac*2.0*math.pi)
    swing=H*0.055*phase
    lift=H*0.010*abs(phase)
    key(whL,fr,(left_sign*hand_gap,hand_y+swing,hand_z+lift))
    key(whR,fr,(right_sign*hand_gap,hand_y-swing,hand_z+lift))
    key(weL,fr,(left_sign*(hand_gap+H*0.105),-H*0.06+swing*0.35,shoulder_z-H*0.12))
    key(weR,fr,(right_sign*(hand_gap+H*0.105),-H*0.06-swing*0.35,shoulder_z-H*0.12))

bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=f0,frame_end=f1,step=1,only_selected=False,
                 visual_keying=True,clear_constraints=True,clear_parents=False,
                 use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
walk_fixed=arm.animation_data.action
walk_fixed.name="walk"
walk_fixed.use_fake_user=True
relax_fingers(walk_fixed,(f0,f0+cycle//4,f0+cycle//2,f0+3*cycle//4,f1))
for o in (whL,whR,weL,weR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# Enforce 30 fps so animation cadence is deterministic in Godot.
bpy.context.scene.render.fps=30
bpy.context.scene.render.fps_base=1.0
arm.animation_data.action=None
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle,walk_fixed):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=max(60,f1)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V13_NATIVE_LEGS_SAFE_ARMS",os.path.abspath(out),"walk_frames",f0,f1)
