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

# ---------- official MakeHuman walk1.bvh ----------
before=set(bpy.data.objects)
bpy.ops.import_anim.bvh(filepath=os.path.abspath(walk_bvh),axis_forward='-Z',axis_up='Y',use_fps_scale=False)
src_arm=next(o for o in bpy.data.objects if o not in before and o.type=='ARMATURE')
raw_action=src_arm.animation_data.action if src_arm.animation_data else None
srcpb=src_arm.pose.bones

MAP={
    "pelvis":"Hips",
    "spine_01":"Spine1","spine_02":"Spine2","spine_03":"Spine3",
    "neck_01":"Neck","head":"Head",
    "clavicle_l":"Clavicle_L","upperarm_l":"UpArm_L","lowerarm_l":"LoArm_L","hand_l":"Hand_L",
    "clavicle_r":"Clavicle_R","upperarm_r":"UpArm_R","lowerarm_r":"LoArm_R","hand_r":"Hand_R",
    "thigh_l":"UpLeg_L","calf_l":"LoLeg_L","foot_l":"Foot_L","ball_l":"Toe_L",
    "thigh_r":"UpLeg_R","calf_r":"LoLeg_R","foot_r":"Foot_R","ball_r":"Toe_R",
}
# Finger mapping removes the malformed palm/finger look during motion.
for side_t,side_s in (("l","L"),("r","R")):
    for f_t,f_s in (("thumb","Thumb"),("index","Index"),("middle","Middle"),("ring","Ring"),("pinky","Pinky")):
        for i in (1,2,3):
            MAP[f"{f_t}_{i:02d}_{side_t}"]=f"{f_s}{i}_{side_s}"

pairs={tb:sb for tb,sb in MAP.items() if tb in pb and sb in srcpb}
print("V11 WALK mapped",len(pairs),"bones")

def depth(db):
    d=0
    while db.parent:
        db=db.parent; d+=1
    return d

tgt_rest={tb:arm.data.bones[tb].matrix_local.to_3x3() for tb in pairs}
src_rest={tb:src_arm.data.bones[sb].matrix_local.to_3x3() for tb,sb in pairs.items()}
order=sorted(pairs,key=lambda b:depth(arm.data.bones[b]))

walk=bpy.data.actions.new("walk")
arm.animation_data.action=walk
for b in pb:
    b.rotation_mode='QUATERNION'

# walk1.bvh is a native MakeHuman 14-frame in-place cycle.
for f in range(1,15):
    bpy.context.scene.frame_set(f)
    se=src_arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    for tb in order:
        src_pose=se.pose.bones[pairs[tb]]
        Rw=src_pose.matrix.to_3x3() @ src_rest[tb].inverted() @ tgt_rest[tb]
        p=pb[tb]
        p.matrix=Matrix.Translation(p.matrix.to_translation()) @ Rw.to_4x4()
        bpy.context.view_layer.update()
        p.rotation_mode='QUATERNION'
        p.keyframe_insert("rotation_quaternion",frame=f)

# Keep all translation/root motion out: the Godot CharacterBody drives movement.
if pelvis in pb:
    p=pb[pelvis]
    p.location=(0,0,0)
    for f in range(1,15):
        p.keyframe_insert("location",frame=f)

walk.use_fake_user=True
arm.animation_data.action=None

# Remove imported source rig + its raw action.
bpy.data.objects.remove(src_arm,do_unlink=True)
if raw_action:
    try:bpy.data.actions.remove(raw_action)
    except:pass

# Duplicate walk as a named run fallback. Godot V11 uses walk sped up for running.
run=walk.copy(); run.name="run"; run.use_fake_user=True

# NLA tracks keep all clips attached to this armature for deterministic glTF export.
for act in (idle,walk,run):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V11_MOTION_DONE",os.path.abspath(out))
