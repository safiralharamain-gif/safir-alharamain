import bpy, os, sys, math

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")

# Remove imported animation state completely. v9 animations are authored on THIS exact rig,
# avoiding BVH-retarget distortions and T/A-pose idle arms.
if arm.animation_data:
    arm.animation_data_clear()
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)

pb=arm.pose.bones
for b in pb:
    b.rotation_mode='XYZ'
    b.rotation_euler=(0,0,0)

def find(*names):
    for n in names:
        if n in pb: return n
    return None

pelvis=find("pelvis")
sp1=find("spine_01"); sp2=find("spine_02"); sp3=find("spine_03")
neck=find("neck_01"); head=find("head")
clL=find("clavicle_l"); clR=find("clavicle_r")
uaL=find("upperarm_l"); uaR=find("upperarm_r")
faL=find("lowerarm_l"); faR=find("lowerarm_r")
handL=find("hand_l"); handR=find("hand_r")
thL=find("thigh_l"); thR=find("thigh_r")
caL=find("calf_l"); caR=find("calf_r")
foL=find("foot_l"); foR=find("foot_r")

print("V9 BONES",pelvis,sp1,sp2,uaL,uaR,faL,faR,thL,thR,caL,caR,foL,foR)

# Gentle finger curl.
finger_pose={}
for side in ("l","r"):
    for fng in ("index","middle","ring","pinky"):
        for seg,amt in (("01",-0.18),("02",-0.38),("03",-0.28)):
            n=f"{fng}_{seg}_{side}"
            if n in pb: finger_pose[n]=(0,0,amt)

# MakeHuman's game-engine rest is an open A/T pose. These Z rotations bring arms down alongside
# the torso. Small X values then create the forward/back swing without reopening the shoulders.
ARM_DOWN_L=-1.02
ARM_DOWN_R= 1.02
ELBOW_L=0.18
ELBOW_R=0.18

def reset_pose():
    for b in pb:
        b.rotation_mode='XYZ'
        b.rotation_euler=(0,0,0)

def base_pose():
    d={}
    if uaL: d[uaL]=(0.04,0.02,ARM_DOWN_L)
    if uaR: d[uaR]=(0.04,-0.02,ARM_DOWN_R)
    if faL: d[faL]=(ELBOW_L,0.02,-0.05)
    if faR: d[faR]=(ELBOW_R,-0.02,0.05)
    if clL: d[clL]=(0.0,0.0,-0.04)
    if clR: d[clR]=(0.0,0.0,0.04)
    d.update(finger_pose)
    return d

def blend(base,extra):
    d=dict(base); d.update(extra); return d

def author(name,frames,fps=30):
    reset_pose()
    act=bpy.data.actions.new(name)
    ad=arm.animation_data_create()
    ad.action=act
    for fr,pose in frames:
        for bn,eu in pose.items():
            if bn and bn in pb:
                pb[bn].rotation_euler=eu
                pb[bn].keyframe_insert("rotation_euler",frame=fr)
    tr=ad.nla_tracks.new(); tr.name=name
    tr.strips.new(name,frames[0][0],act)
    ad.action=None
    # smooth curves
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation='BEZIER'
    return act

B=base_pose()

# Relaxed idle: arms down, slight elbow flex, tiny breathing only.
idle=[]
for fr,breath in [(1,0.0),(30,0.025),(60,0.0)]:
    ex={}
    if sp2: ex[sp2]=(breath,0,0)
    if head: ex[head]=(0.0,0.015 if fr==30 else 0.0,0.0)
    idle.append((fr,blend(B,ex)))
author("idle",idle)

# Natural walk: moderate stride, knees bend on recovery, arms counter-swing while remaining down.
# 32-frame seamless cycle.
walk_specs=[
    (1,   0.34,-0.10,-0.20,  -0.34,-0.42, 0.12,  -0.22, 0.22),
    (9,   0.03,-0.08, 0.02,  -0.05,-0.78, 0.18,  -0.04, 0.04),
    (17, -0.34,-0.42, 0.12,   0.34,-0.10,-0.20,   0.22,-0.22),
    (25, -0.05,-0.78, 0.18,   0.03,-0.08, 0.02,   0.04,-0.04),
    (33,  0.34,-0.10,-0.20,  -0.34,-0.42, 0.12,  -0.22, 0.22),
]
walk=[]
for fr,rt,rc,rf,lt,lc,lf,asr,asl in walk_specs:
    ex={}
    if thR: ex[thR]=(rt,0,0)
    if caR: ex[caR]=(rc,0,0)
    if foR: ex[foR]=(rf,0,0)
    if thL: ex[thL]=(lt,0,0)
    if caL: ex[caL]=(lc,0,0)
    if foL: ex[foL]=(lf,0,0)
    if uaR: ex[uaR]=(asr,0.0,ARM_DOWN_R)
    if uaL: ex[uaL]=(asl,0.0,ARM_DOWN_L)
    if faR: ex[faR]=(0.24,0,0.05)
    if faL: ex[faL]=(0.24,0,-0.05)
    if pelvis: ex[pelvis]=(0.02,0,0.025*math.sin((fr-1)/32*math.tau))
    if sp2: ex[sp2]=(0.02,0,0)
    walk.append((fr,blend(B,ex)))
author("walk",walk)

# Run keeps the same natural arm-down base but bends elbows and increases stride.
run_specs=[
    (1,  0.58,-0.25,-0.12, -0.58,-0.72,0.16, -0.38,0.38),
    (7,  0.06,-0.20, 0.02, -0.10,-1.05,0.20, -0.08,0.08),
    (13,-0.58,-0.72, 0.16,  0.58,-0.25,-0.12, 0.38,-0.38),
    (19,-0.10,-1.05, 0.20,  0.06,-0.20,0.02, 0.08,-0.08),
    (25, 0.58,-0.25,-0.12, -0.58,-0.72,0.16, -0.38,0.38),
]
run=[]
for fr,rt,rc,rf,lt,lc,lf,asr,asl in run_specs:
    ex={}
    if thR: ex[thR]=(rt,0,0)
    if caR: ex[caR]=(rc,0,0)
    if foR: ex[foR]=(rf,0,0)
    if thL: ex[thL]=(lt,0,0)
    if caL: ex[caL]=(lc,0,0)
    if foL: ex[foL]=(lf,0,0)
    if uaR: ex[uaR]=(asr,0,ARM_DOWN_R)
    if uaL: ex[uaL]=(asl,0,ARM_DOWN_L)
    if faR: ex[faR]=(0.55,0,0.05)
    if faL: ex[faL]=(0.55,0,-0.05)
    if sp2: ex[sp2]=(0.10,0,0)
    run.append((fr,blend(B,ex)))
author("run",run)

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',export_animations=True,
    export_animation_mode='ACTIONS',export_yup=True,export_materials='EXPORT',export_apply=False)
print("V9_ANIMATED",os.path.abspath(out))
