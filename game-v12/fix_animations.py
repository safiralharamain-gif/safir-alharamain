import bpy, os, sys
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]
out=argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature")
pb=arm.pose.bones
bones=arm.data.bones

def find(*names):
    for n in names:
        if n in pb:
            return n
    return None

pelvis=find("pelvis")
uaL=find("upperarm_l"); uaR=find("upperarm_r")
laL=find("lowerarm_l"); laR=find("lowerarm_r")
thL=find("thigh_l"); thR=find("thigh_r")
sp2=find("spine_02","spine_01")
head=find("head")
if any(x is None for x in [pelvis,uaL,uaR,laL,laR,thL,thR]):
    raise SystemExit("Missing required bones")

# Preserve the MakeHuman-native walk clip generated from its own walk1.bvh.
walk=None
for a in list(bpy.data.actions):
    if a.name.lower().startswith("walk"):
        walk=a
        break
if walk is None:
    raise SystemExit("Native walk action missing")
walk.name="walk"
walk.use_fake_user=True
for a in list(bpy.data.actions):
    if a != walk:
        bpy.data.actions.remove(a)

pts=[]
for b in bones:
    pts += [b.head_local,b.tail_local]
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); H=max(.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*.5
left_sign=1.0 if bones[uaL].head_local.x > bones[uaR].head_local.x else -1.0
right_sign=-left_sign
leg_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))

def world(local):
    return arm.matrix_world @ Vector(local)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.location=world(local)
    return e

def add_ik(bone,target,pole):
    c=pb[bone].constraints.new('IK')
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False

# Relaxed standing pose matching the approved reference images:
# hands at the sides, small elbow bend, palms clear of the trousers.
hand_x=leg_half + H*.115
hand_y=-H*.010
hand_z=hip_z-H*.165
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

hL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
hR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
eL=empty("idle_elbow_L",(left_sign*(hand_x+H*.105),-H*.055,shoulder_z-H*.115))
eR=empty("idle_elbow_R",(right_sign*(hand_x+H*.105),-H*.055,shoulder_z-H*.115))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)

idle=bpy.data.actions.new("idle")
arm.animation_data_create().action=idle
for fr,breathe in [(1,0.0),(30,H*.003),(60,0.0)]:
    hL.location=world((left_sign*hand_x,hand_y,hand_z+breathe))
    hR.location=world((right_sign*hand_x,hand_y,hand_z+breathe))
    hL.keyframe_insert("location",frame=fr)
    hR.keyframe_insert("location",frame=fr)
    if sp2:
        pb[sp2].rotation_mode='XYZ'
        pb[sp2].rotation_euler=(0.010 if fr==30 else 0.0,0,0)
        pb[sp2].keyframe_insert("rotation_euler",frame=fr)
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
idle=arm.animation_data.action
idle.name="idle"
idle.use_fake_user=True

arm.animation_data.action=idle
for fr in (1,30,60):
    for side in ("l","r"):
        for finger in ("index","middle","ring","pinky"):
            for seg,amt in (("01",-0.18),("02",-0.38),("03",-0.28)):
                n=f"{finger}_{seg}_{side}"
                if n in pb:
                    pb[n].rotation_mode='XYZ'
                    pb[n].rotation_euler=(0,0,amt)
                    pb[n].keyframe_insert("rotation_euler",frame=fr)
        hn=f"hand_{side}"
        if hn in pb:
            pb[hn].rotation_mode='XYZ'
            pb[hn].rotation_euler=(0,0,0)
            pb[hn].keyframe_insert("rotation_euler",frame=fr)
arm.animation_data.action=None

for o in (hL,hR,eL,eR):
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

if arm.animation_data is None:
    arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new()
    tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V12_NATIVE_WALK_RELAXED_IDLE",os.path.abspath(out))