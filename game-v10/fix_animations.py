import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")

# Remove every imported action. V10 animations are baked on this exact rig.
if arm.animation_data: arm.animation_data_clear()
for act in list(bpy.data.actions):
    bpy.data.actions.remove(act)

pb=arm.pose.bones
bones=arm.data.bones
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

def bn(*names):
    for n in names:
        if n in pb: return n
    return None

pelvis=bn("pelvis")
sp1=bn("spine_01"); sp2=bn("spine_02"); sp3=bn("spine_03")
head=bn("head")
uaL=bn("upperarm_l"); uaR=bn("upperarm_r")
laL=bn("lowerarm_l"); laR=bn("lowerarm_r")
handL=bn("hand_l"); handR=bn("hand_r")
thL=bn("thigh_l"); thR=bn("thigh_r")
caL=bn("calf_l"); caR=bn("calf_r")
foL=bn("foot_l"); foR=bn("foot_r")

required=[uaL,uaR,laL,laR,thL,thR,caL,caR]
if any(x is None for x in required):
    raise SystemExit("Missing required limb bones: "+str(required))

# Character dimensions in armature space.
allpts=[]
for b in bones:
    allpts += [b.head_local, b.tail_local]
zmin=min(p.z for p in allpts); zmax=max(p.z for p in allpts); H=max(0.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z if pelvis else zmin+H*.52
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*.5
ankle_z=(bones[caL].tail_local.z+bones[caR].tail_local.z)*.5
print("V10 RIG H",H,"hip",hip_z,"shoulder",shoulder_z,"ankle",ankle_z)

def world(local):
    return arm.matrix_world @ Vector(local)

def make_empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.empty_display_type='SPHERE'; e.empty_display_size=H*.025
    e.location=world(local)
    return e

# Determine left/right sign from rest skeleton, so this works even if naming-space is mirrored.
left_x=bones[uaL].head_local.x
right_x=bones[uaR].head_local.x
sxL=1.0 if left_x>right_x else -1.0
sxR=-sxL

def add_ik(pose_bone_name,target,pole,chain=2):
    c=pb[pose_bone_name].constraints.new('IK')
    c.target=target; c.chain_count=chain
    c.use_rotation=False
    if pole is not None:
        c.pole_target=pole
        c.pole_angle=0.0
    return c

def clear_constraints_and_targets(targets):
    for b in pb:
        for c in list(b.constraints):
            b.constraints.remove(c)
    for o in targets:
        if o and o.name in bpy.data.objects:
            bpy.data.objects.remove(o,do_unlink=True)

def reset_pose():
    for b in pb:
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)
        b.location=(0,0,0)
        b.scale=(1,1,1)
    bpy.context.view_layer.update()

# Hand targets: wrists beside hips, slightly forward; poles outwards keep elbows natural.
def setup_arm_ik():
    tx=H*.145
    hand_z=hip_z-H*.18
    hand_y=-H*.018
    tL=make_empty("hand_target_L",(sxL*tx,hand_y,hand_z))
    tR=make_empty("hand_target_R",(sxR*tx,hand_y,hand_z))
    pL=make_empty("elbow_pole_L",(sxL*H*.34,-H*.05,shoulder_z-H*.10))
    pR=make_empty("elbow_pole_R",(sxR*H*.34,-H*.05,shoulder_z-H*.10))
    add_ik(laL,tL,pL,2); add_ik(laR,tR,pR,2)
    return [tL,tR,pL,pR]

# Foot targets start at the rest ankles. Knee poles point forward (-Y) and a little outward.
def setup_leg_ik():
    aL=bones[caL].tail_local.copy(); aR=bones[caR].tail_local.copy()
    tL=make_empty("foot_target_L",aL); tR=make_empty("foot_target_R",aR)
    kz=(bones[thL].tail_local.z+bones[thR].tail_local.z)*.5
    pL=make_empty("knee_pole_L",(bones[thL].head_local.x,-H*.34,kz))
    pR=make_empty("knee_pole_R",(bones[thR].head_local.x,-H*.34,kz))
    add_ik(caL,tL,pL,2); add_ik(caR,tR,pR,2)
    return [tL,tR,pL,pR],aL,aR

def key_loc(obj,frame,local):
    obj.location=world(local)
    obj.keyframe_insert("location",frame=frame)

def bake_clip(name,start,end,setup_keyframes):
    reset_pose()
    arm.animation_data_create()
    action=bpy.data.actions.new(name)
    arm.animation_data.action=action

    arms=setup_arm_ik()
    legs,aL,aR=setup_leg_ik()
    targets=arms+legs
    setup_keyframes(start,end,arms,legs,aL,aR)

    # Small torso motion can coexist with IK.
    if sp2:
        pb[sp2].rotation_mode='XYZ'
        for fr,pitch,roll in [(start,0.01,0.0),((start+end)//2,0.025,0.008),(end,0.01,0.0)]:
            pb[sp2].rotation_euler=(pitch,0,roll)
            pb[sp2].keyframe_insert("rotation_euler",frame=fr)

    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=False,
        visual_keying=True,clear_constraints=True,clear_parents=False,
        use_current_action=True,bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')

    # Rename baked/current action deterministically.
    if arm.animation_data and arm.animation_data.action:
        arm.animation_data.action.name=name
    else:
        action.name=name
    clear_constraints_and_targets(targets)
    if arm.animation_data: arm.animation_data.action=None
    print("BAKED",name,start,end)

def idle_keys(start,end,arms,legs,aL,aR):
    tL,tR,_,_=arms
    tx=H*.145; z=hip_z-H*.18; y=-H*.018
    for fr,breath in [(start,0.0),((start+end)//2,H*.004),(end,0.0)]:
        key_loc(tL,fr,(sxL*tx,y,z+breath))
        key_loc(tR,fr,(sxR*tx,y,z+breath))
    lf,rf,_,_=legs
    for fr in (start,end):
        key_loc(lf,fr,aL); key_loc(rf,fr,aR)

def walk_keys(start,end,arms,legs,aL,aR):
    hL,hR,_,_=arms; fL,fR,_,_=legs
    stride=H*.105; lift=H*.035; hs=H*.055
    # 33-frame seamless cycle. Forward is -Y on MakeHuman.
    phases=[(0,1.0),(8,0.0),(16,-1.0),(24,0.0),(32,1.0)]
    for off,p in phases:
        fr=start+off
        # Feet counterphase; lift on swing.
        l=aL.copy(); r=aR.copy()
        l.y += -stride*p; r.y += stride*p
        if p<0: l.z += lift*(1-abs(p))
        if p>0: r.z += lift*(1-abs(p))
        key_loc(fL,fr,l); key_loc(fR,fr,r)
        # Hands counter-swing but remain beside body.
        key_loc(hL,fr,(sxL*H*.145,-H*.018 + hs*p,hip_z-H*.18))
        key_loc(hR,fr,(sxR*H*.145,-H*.018 - hs*p,hip_z-H*.18))
    # Ensure midpoint swing gets actual lift.
    for fr,left_swing in [(start+8,True),(start+24,False)]:
        if left_swing:
            l=aL.copy(); l.y+=stride*.15; l.z+=lift
            key_loc(fL,fr,l)
        else:
            r=aR.copy(); r.y+=stride*.15; r.z+=lift
            key_loc(fR,fr,r)

def run_keys(start,end,arms,legs,aL,aR):
    hL,hR,_,_=arms; fL,fR,_,_=legs
    stride=H*.16; lift=H*.055; hs=H*.09
    phases=[(0,1.0),(6,0.0),(12,-1.0),(18,0.0),(24,1.0)]
    for off,p in phases:
        fr=start+off
        l=aL.copy(); r=aR.copy()
        l.y += -stride*p; r.y += stride*p
        key_loc(fL,fr,l); key_loc(fR,fr,r)
        key_loc(hL,fr,(sxL*H*.145,-H*.018 + hs*p,hip_z-H*.15))
        key_loc(hR,fr,(sxR*H*.145,-H*.018 - hs*p,hip_z-H*.15))
    l=aL.copy(); l.y+=stride*.2; l.z+=lift; key_loc(fL,start+6,l)
    r=aR.copy(); r.y+=stride*.2; r.z+=lift; key_loc(fR,start+18,r)

bake_clip("idle",1,60,idle_keys)
bake_clip("walk",1,33,walk_keys)
bake_clip("run",1,25,run_keys)

# Set a clean relaxed frame before export.
reset_pose()
bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V10_ANIMATED",os.path.abspath(out))
