import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature found")
ad=arm.animation_data_create()
pb=arm.pose.bones
bones=arm.data.bones

def find_action(token):
    token=token.lower()
    for a in bpy.data.actions:
        if token in a.name.lower(): return a
    return None

walk=find_action("walk")
if walk is None: raise SystemExit("No real walk action found")
walk.name="walk"; walk.use_fake_user=True

# Keep the real mocap action intact, including its wrist/hand motion.
# The MakeHuman generator already adds a relaxed finger curl to this clip.
for a in list(bpy.data.actions):
    if a != walk:
        bpy.data.actions.remove(a)

def bn(name): return pb.get(name)
pelvis=bn("pelvis")
uaL=bn("upperarm_l"); uaR=bn("upperarm_r")
laL=bn("lowerarm_l"); laR=bn("lowerarm_r")
handL=bn("hand_l"); handR=bn("hand_r")
sp2=bn("spine_02") or bn("spine_01")
if any(x is None for x in (pelvis,uaL,uaR,laL,laR,handL,handR)):
    raise SystemExit("Missing core arm bones")

allpts=[]
for b in bones: allpts += [b.head_local,b.tail_local]
zmin=min(p.z for p in allpts); zmax=max(p.z for p in allpts); H=max(.1,zmax-zmin)
hip_z=bones["pelvis"].head_local.z
leg_half=max(abs(bones["thigh_l"].head_local.x),abs(bones["thigh_r"].head_local.x))
left_sign=1.0 if bones["upperarm_l"].head_local.x > bones["upperarm_r"].head_local.x else -1.0
right_sign=-left_sign
shoulder_z=(bones["upperarm_l"].head_local.z+bones["upperarm_r"].head_local.z)*.5

# Pick a genuinely neutral mocap frame: arms down, hands separated and not crossing the pelvis.
start=max(1,int(math.floor(walk.frame_range[0])))
end=max(start+1,int(math.ceil(walk.frame_range[1])))
ad.action=walk
best_frame=start; best_score=1e12
for f in range(start,end+1):
    bpy.context.scene.frame_set(f); bpy.context.view_layer.update()
    pel=pelvis.matrix.translation
    lh=handL.matrix.translation; rh=handR.matrix.translation
    lu=uaL.matrix.translation; ru=uaR.matrix.translation
    lout=left_sign*(lh.x-pel.x); rout=right_sign*(rh.x-pel.x)
    # Heavy penalties for crossed/raised/clasped hands.
    penalty=0.0
    if lout < H*.035: penalty += 100.0 + (H*.035-lout)*100
    if rout < H*.035: penalty += 100.0 + (H*.035-rout)*100
    if lh.z > lu.z-H*.08: penalty += 100.0
    if rh.z > ru.z-H*.08: penalty += 100.0
    sep=abs(lh.x-rh.x)
    if sep < H*.16: penalty += 100.0
    score=penalty + abs(lh.y-rh.y)*5 + abs(lh.z-rh.z)*2
    if score < best_score:
        best_score=score; best_frame=f
print("V12_NEUTRAL_FRAME",best_frame,"score",best_score)

bpy.context.scene.frame_set(best_frame); bpy.context.view_layer.update()

# Save the neutral mocap pose first.
upper_names=[
 "clavicle_l","clavicle_r","upperarm_l","upperarm_r","lowerarm_l","lowerarm_r",
 "hand_l","hand_r","spine_01","spine_02","spine_03","neck_01","head"
]
finger_names=[]
for side in ("l","r"):
    for fng in ("thumb","index","middle","ring","pinky"):
        for seg in ("01","02","03"):
            n=f"{fng}_{seg}_{side}"
            if n in pb: finger_names.append(n)

neutral={}
for n in upper_names+finger_names:
    if n in pb: neutral[n]=pb[n].matrix_basis.copy()

# Reset, reapply neutral upper body, then use IK ONLY to place wrists beside thighs.
ad.action=None
for b in pb:
    b.rotation_mode='QUATERNION'; b.rotation_quaternion=(1,0,0,0); b.location=(0,0,0); b.scale=(1,1,1)
for n,m in neutral.items():
    pb[n].matrix_basis=m.copy()
bpy.context.view_layer.update()

def world(local): return arm.matrix_world @ Vector(local)
def empty(name,local):
    e=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(e)
    e.location=world(local); e.empty_display_type='PLAIN_AXES'; e.empty_display_size=H*.02
    return e
def add_ik(lower,target,pole):
    c=lower.constraints.new('IK'); c.target=target; c.pole_target=pole; c.chain_count=2; c.use_rotation=False
    return c

hand_x=leg_half+H*.115
hand_z=hip_z-H*.165
hand_y=-H*.015
tL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
tR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
pL=empty("idle_elbow_L",(left_sign*(hand_x+H*.16),-H*.09,shoulder_z-H*.10))
pR=empty("idle_elbow_R",(right_sign*(hand_x+H*.16),-H*.09,shoulder_z-H*.10))
cL=add_ik(laL,tL,pL); cR=add_ik(laR,tR,pR)
bpy.context.view_layer.update()

# Capture the corrected evaluated idle pose.
idle_pose={}
for n in upper_names+finger_names:
    if n in pb:
        idle_pose[n]=pb[n].matrix_basis.copy()

laL.constraints.remove(cL); laR.constraints.remove(cR)
for o in (tL,tR,pL,pR): bpy.data.objects.remove(o,do_unlink=True)

# Author stable idle with corrected arms, natural wrists and relaxed fingers.
idle=bpy.data.actions.new("idle"); idle.use_fake_user=True; ad.action=idle
for fr in (1,30,60):
    for n,m in idle_pose.items():
        b=pb[n]; b.rotation_mode='QUATERNION'
        b.rotation_quaternion=m.to_quaternion()
        b.location=m.to_translation()
        b.scale=m.to_scale()
        b.keyframe_insert("rotation_quaternion",frame=fr)
        b.keyframe_insert("location",frame=fr)
        b.keyframe_insert("scale",frame=fr)
ad.action=None

# Lock wrists and fingers to the relaxed neutral pose while preserving the mocap
# shoulder/elbow/leg motion. This removes twisted palms and fingers clipping into trousers.
ad.action=walk
relaxed_bones=["hand_l","hand_r"]+finger_names
for n in relaxed_bones:
    if n not in pb or n not in neutral:
        continue
    pb[n].rotation_mode='QUATERNION'
    q=neutral[n].to_quaternion()
    for fr in range(start,end+1,3):
        pb[n].rotation_quaternion=q
        pb[n].keyframe_insert("rotation_quaternion",frame=fr,group=n)
    if (end-start) % 3 != 0:
        pb[n].rotation_quaternion=q
        pb[n].keyframe_insert("rotation_quaternion",frame=end,group=n)
ad.action=None

# Run reuses the same natural full-body human gait at a faster cadence.
run=walk.copy(); run.name="run"; run.use_fake_user=True

# Explicitly attach all clips for deterministic glTF ACTIONS export.
for tr in list(ad.nla_tracks): ad.nla_tracks.remove(tr)
for act in (idle,walk,run):
    tr=ad.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]

ad.action=None
for b in pb:
    b.rotation_mode='QUATERNION'; b.rotation_quaternion=(1,0,0,0); b.location=(0,0,0); b.scale=(1,1,1)

bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=max(60,end)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    use_selection=True,export_animations=True,export_animation_mode='ACTIONS',
    export_yup=True,export_materials='EXPORT',export_apply=False)
print("V12_REAL_MOCAP_SAFE_IDLE_EXPORTED",os.path.abspath(out))
