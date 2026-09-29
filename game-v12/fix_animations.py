import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature")

arm.animation_data_create()
pb=arm.pose.bones
bones=arm.data.bones

def bone(*names):
    for n in names:
        if n in pb:
            return n
    return None

pelvis=bone("pelvis")
uaL=bone("upperarm_l"); uaR=bone("upperarm_r")
laL=bone("lowerarm_l"); laR=bone("lowerarm_r")
handL=bone("hand_l"); handR=bone("hand_r")
thL=bone("thigh_l"); thR=bone("thigh_r")
sp2=bone("spine_02","spine_01")
if any(x is None for x in [pelvis,uaL,uaR,laL,laR,handL,handR,thL,thR]):
    raise SystemExit("Missing required MakeHuman bones")

pts=[]
for b in bones:
    pts += [b.head_local,b.tail_local]
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); H=max(.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*.5
left_sign=1.0 if bones[uaL].head_local.x > bones[uaR].head_local.x else -1.0
right_sign=-left_sign
leg_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))

def world(v):
    return arm.matrix_world @ Vector(v)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.empty_display_type='PLAIN_AXES'
    e.empty_display_size=H*.025
    e.location=world(local)
    return e

def add_ik(bone_name,target,pole):
    c=pb[bone_name].constraints.new('IK')
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False

# Find native MakeHuman walk action imported with the raw character.
actions=list(bpy.data.actions)
walk_src=None
for a in actions:
    if "walk" in a.name.lower():
        walk_src=a; break
if walk_src is None and actions:
    walk_src=actions[0]
if walk_src is None:
    raise SystemExit("No native walk action found")

# Remove unused extra actions but keep native walk.
for a in list(bpy.data.actions):
    if a != walk_src:
        bpy.data.actions.remove(a)
walk_src.name="walk"

# Comfortable arm positions from actual character scale.
hand_x=leg_half + H*.115
hand_z=hip_z-H*.115
hand_y=-H*.015
elbow_x=hand_x+H*.085
elbow_z=shoulder_z-H*.105
swing=H*.055

# ---------- IDLE ----------
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

idle=bpy.data.actions.new("idle")
arm.animation_data.action=idle
hL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
hR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
eL=empty("idle_elbow_L",(left_sign*elbow_x,-H*.055,elbow_z))
eR=empty("idle_elbow_R",(right_sign*elbow_x,-H*.055,elbow_z))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)

for fr,breathe in [(1,0.0),(30,H*.003),(60,0.0)]:
    hL.location=world((left_sign*hand_x,hand_y,hand_z+breathe))
    hR.location=world((right_sign*hand_x,hand_y,hand_z+breathe))
    hL.keyframe_insert("location",frame=fr); hR.keyframe_insert("location",frame=fr)
    eL.location=world((left_sign*elbow_x,-H*.055,elbow_z))
    eR.location=world((right_sign*elbow_x,-H*.055,elbow_z))
    eL.keyframe_insert("location",frame=fr); eR.keyframe_insert("location",frame=fr)

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,visual_keying=True,
                 clear_constraints=True,clear_parents=False,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle=arm.animation_data.action; idle.name="idle"; idle.use_fake_user=True
arm.animation_data.action=None
for o in [hL,hR,eL,eR]:
    bpy.data.objects.remove(o,do_unlink=True)

# ---------- WALK: preserve native leg motion, replace only arm chains ----------
walk=walk_src
arm.animation_data.action=walk
start=int(walk.frame_range[0]); end=int(walk.frame_range[1])
if end-start < 8:
    start=1; end=32

hL=empty("walk_hand_L",(left_sign*hand_x,hand_y,hand_z))
hR=empty("walk_hand_R",(right_sign*hand_x,hand_y,hand_z))
eL=empty("walk_elbow_L",(left_sign*elbow_x,-H*.055,elbow_z))
eR=empty("walk_elbow_R",(right_sign*elbow_x,-H*.055,elbow_z))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)

# Counter-swing is deliberately small and smooth. Hands stay outside the thighs.
span=max(1,end-start)
for fr in range(start,end+1):
    phase=2.0*math.pi*(fr-start)/span
    s=math.sin(phase)
    # left hand back as right leg steps forward, right hand opposite
    hL.location=world((left_sign*hand_x,hand_y+swing*s,hand_z+H*.006*abs(s)))
    hR.location=world((right_sign*hand_x,hand_y-swing*s,hand_z+H*.006*abs(s)))
    hL.keyframe_insert("location",frame=fr); hR.keyframe_insert("location",frame=fr)
    eL.location=world((left_sign*elbow_x,-H*.045+swing*.35*s,elbow_z))
    eR.location=world((right_sign*elbow_x,-H*.045-swing*.35*s,elbow_z))
    eL.keyframe_insert("location",frame=fr); eR.keyframe_insert("location",frame=fr)

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=False,visual_keying=True,
                 clear_constraints=True,clear_parents=False,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
walk=arm.animation_data.action; walk.name="walk"; walk.use_fake_user=True

# Neutral hands/fingers on idle + walk. Do this after baking so wrists cannot twist into the body.
def neutralize_hands(action,frame_start,frame_end):
    arm.animation_data.action=action
    for fr in range(frame_start,frame_end+1):
        bpy.context.scene.frame_set(fr)
        for side in ("l","r"):
            hn="hand_"+side
            if hn in pb:
                pb[hn].rotation_mode='XYZ'
                pb[hn].rotation_euler=(0.0,0.0,0.0)
                pb[hn].keyframe_insert("rotation_euler",frame=fr)
            for finger in ("index","middle","ring","pinky"):
                for seg,amt in (("01",-0.06),("02",-0.12),("03",-0.08)):
                    n=f"{finger}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode='XYZ'
                        pb[n].rotation_euler=(0.0,0.0,amt)
                        pb[n].keyframe_insert("rotation_euler",frame=fr)
        if "thumb_01_l" in pb:
            for side in ("l","r"):
                for seg,amt in (("01",-0.08),("02",-0.10),("03",-0.06)):
                    n=f"thumb_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode='XYZ'; pb[n].rotation_euler=(0.0,amt,0.0)
                        pb[n].keyframe_insert("rotation_euler",frame=fr)

neutralize_hands(idle,1,60)
neutralize_hands(walk,start,end)

# Run is a clean copy of walk; Godot raises playback speed. This avoids introducing a second bad gait.
run=walk.copy(); run.name="run"; run.use_fake_user=True

# Keep torso upright: erase accidental side lean from all three actions by keying spine/pelvis roll/yaw to zero.
for act,fs,fe in [(idle,1,60),(walk,start,end),(run,start,end)]:
    arm.animation_data.action=act
    for fr in range(fs,fe+1):
        bpy.context.scene.frame_set(fr)
        for bn in [pelvis,sp2]:
            if bn and bn in pb:
                pb[bn].rotation_mode='XYZ'
                e=pb[bn].rotation_euler.copy()
                pb[bn].rotation_euler=(e.x,0.0,0.0)
                pb[bn].keyframe_insert("rotation_euler",frame=fr)

arm.animation_data.action=None
for o in [hL,hR,eL,eR]:
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

# NLA tracks make all clips export reliably.
for act in (idle,walk,run):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,int(act.frame_range[0]),act)
    st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V12_NATIVE_WALK_FIXED_ARMS",os.path.abspath(out))
