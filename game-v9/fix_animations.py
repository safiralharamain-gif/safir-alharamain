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
ARM_DOWN_L=-1.12
ARM_DOWN_R= 1.12
ELBOW_L=-0.10
ELBOW_R= 0.10

def reset_pose():
    for b in pb:
        b.rotation_mode='XYZ'
        b.rotation_euler=(0,0,0)

def base_pose():
    d={}
    if uaL: d[uaL]=(0.0,0.0,ARM_DOWN_L)
    if uaR: d[uaR]=(0.0,0.0,ARM_DOWN_R)
    if faL: d[faL]=(0.0,0.0,ELBOW_L)
    if faR: d[faR]=(0.0,0.0,ELBOW_R)
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
    # fr, right thigh/calf/foot, left thigh/calf/foot, right-arm swing, left-arm swing
    (1,   0.24,-0.10,-0.08,  -0.24,-0.22, 0.08,  -0.18, 0.18),
    (9,   0.03,-0.08, 0.00,  -0.05,-0.38, 0.10,  -0.02, 0.02),
    (17, -0.24,-0.22, 0.08,   0.24,-0.10,-0.08,   0.18,-0.18),
    (25, -0.05,-0.38, 0.10,   0.03,-0.08, 0.00,   0.02,-0.02),
    (33,  0.24,-0.10,-0.08,  -0.24,-0.22, 0.08,  -0.18, 0.18),
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
    if faR: ex[faR]=(-0.05+0.05*abs(asr),0.0,ELBOW_R)
    if faL: ex[faL]=(-0.05+0.05*abs(asl),0.0,ELBOW_L)
    if pelvis: ex[pelvis]=(0.015,0,0.018*math.sin((fr-1)/32*math.tau))
    if sp2: ex[sp2]=(0.018,0,0)
    walk.append((fr,blend(B,ex)))
author("walk",walk)

# Run keeps the same natural arm-down base but bends elbows and increases stride.
run_specs=[
    (1,  0.42,-0.18,-0.06, -0.42,-0.48,0.12, -0.30, 0.30),
    (7,  0.05,-0.14, 0.00, -0.08,-0.64,0.14, -0.05, 0.05),
    (13,-0.42,-0.48, 0.12,  0.42,-0.18,-0.06,  0.30,-0.30),
    (19,-0.08,-0.64, 0.14,  0.05,-0.14,0.00,  0.05,-0.05),
    (25, 0.42,-0.18,-0.06, -0.42,-0.48,0.12, -0.30, 0.30),
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
    if uaR: ex[uaR]=(asr,0.0,ARM_DOWN_R)
    if uaL: ex[uaL]=(asl,0.0,ARM_DOWN_L)
    if faR: ex[faR]=(-0.34,0.0,ELBOW_R)
    if faL: ex[faL]=(-0.34,0.0,ELBOW_L)
    if sp2: ex[sp2]=(0.07,0,0)
    run.append((fr,blend(B,ex)))
author("run",run)

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',export_animations=True,
    export_animation_mode='ACTIONS',export_yup=True,export_materials='EXPORT',export_apply=False)
print("V9_ANIMATED",os.path.abspath(out))
