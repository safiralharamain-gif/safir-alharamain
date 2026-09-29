import bpy, os, sys, math
from mathutils import Vector

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

# Remove all unreliable imported actions. V13 authors motion directly on the final rig.
for a in list(bpy.data.actions): bpy.data.actions.remove(a)

pts=[p for b in bones for p in (b.head_local,b.tail_local)]
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); H=max(0.1,zmax-zmin)
hip_z=bones[pelvis].head_local.z
shoulder_z=(bones[uaL].head_local.z+bones[uaR].head_local.z)*0.5
left_sign=1.0 if bones[uaL].head_local.x>bones[uaR].head_local.x else -1.0
right_sign=-left_sign
hip_half=max(abs(bones[thL].head_local.x),abs(bones[thR].head_local.x))
foot_l_rest=bones[footL].head_local.copy()
foot_r_rest=bones[footR].head_local.copy()
knee_l_rest=bones[caL].head_local.copy()
knee_r_rest=bones[caR].head_local.copy()

# Designed gait: 1-second cycle at 30fps, 60% stance. During stance each planted foot
# travels 0.66m backward relative to the body, exactly matching 1.10m/s world travel.
FPS=30
F0=1
F1=31
STANCE=0.60
WALK_SPEED=1.10
STANCE_DISTANCE=WALK_SPEED*(STANCE*((F1-F0)/FPS))
HALF=STANCE_DISTANCE*0.5
FOOT_LIFT=max(0.065,H*0.040)
HAND_SWING=max(0.075,H*0.055)

bpy.context.scene.render.fps=FPS
bpy.context.scene.render.fps_base=1.0

def world(local):
    return arm.matrix_world @ Vector(local)

def empty(name,local):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    e.location=world(local)
    return e

def key(obj,fr,local):
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
                pb[thumb].rotation_euler=(0.03,0.0,-0.16 if side=="l" else 0.16)
                pb[thumb].keyframe_insert("rotation_euler",frame=fr)
            for finger in ("index","middle","ring","pinky"):
                for seg,amt in (("01",-0.11),("02",-0.25),("03",-0.18)):
                    n=f"{finger}_{seg}_{side}"
                    if n in pb:
                        pb[n].rotation_mode='XYZ'
                        pb[n].rotation_euler=(0,0,amt)
                        pb[n].keyframe_insert("rotation_euler",frame=fr)

# ---------- relaxed idle ----------
reset_pose()
hand_x=hip_half+H*0.105
hand_z=hip_z-H*0.17
hand_y=-H*0.012
hL=empty("idle_hand_L",(left_sign*hand_x,hand_y,hand_z))
hR=empty("idle_hand_R",(right_sign*hand_x,hand_y,hand_z))
eL=empty("idle_elbow_L",(left_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
eR=empty("idle_elbow_R",(right_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
add_ik(laL,hL,eL); add_ik(laR,hR,eR)
idle=bpy.data.actions.new("idle"); arm.animation_data.action=idle
for fr,breathe in ((1,0.0),(30,H*0.003),(60,0.0)):
    key(hL,fr,(left_sign*hand_x,hand_y,hand_z+breathe))
    key(hR,fr,(right_sign*hand_x,hand_y,hand_z+breathe))
    if spine:
        pb[spine].rotation_mode='XYZ'; pb[spine].rotation_euler=(0.006 if fr==30 else 0,0,0)
        pb[spine].keyframe_insert("rotation_euler",frame=fr)
    if head:
        pb[head].rotation_mode='XYZ'; pb[head].rotation_euler=(0,0,0)
        pb[head].keyframe_insert("rotation_euler",frame=fr)
bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=1,frame_end=60,step=1,only_selected=False,visual_keying=True,
                 clear_constraints=True,clear_parents=False,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
idle=arm.animation_data.action; idle.name="idle"; idle.use_fake_user=True
relax_fingers(idle,(1,30,60))
for o in (hL,hR,eL,eR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# ---------- full V13 walk ----------
reset_pose()
walk=bpy.data.actions.new("walk"); arm.animation_data.action=walk

# Feet are driven by calf IK to ankle positions; knees use forward poles to prevent sideways bends.
ftL=empty("walk_foot_L",foot_l_rest)
ftR=empty("walk_foot_R",foot_r_rest)
kpL=empty("walk_knee_L",(knee_l_rest.x,-H*0.28,knee_l_rest.z))
kpR=empty("walk_knee_R",(knee_r_rest.x,-H*0.28,knee_r_rest.z))
add_ik(caL,ftL,kpL,2); add_ik(caR,ftR,kpR,2)

whL=empty("walk_hand_L",(left_sign*hand_x,hand_y,hand_z))
whR=empty("walk_hand_R",(right_sign*hand_x,hand_y,hand_z))
weL=empty("walk_elbow_L",(left_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
weR=empty("walk_elbow_R",(right_sign*(hand_x+H*0.10),-H*0.07,shoulder_z-H*0.11))
add_ik(laL,whL,weL,2); add_ik(laR,whR,weR,2)

def smooth(u): return u*u*(3.0-2.0*u)

# Blender character faces -Y. Front contact therefore has smaller Y.
def foot_at(rest,phase):
    phase%=1.0
    front=rest.y-HALF
    back=rest.y+HALF
    if phase<STANCE:
        u=phase/STANCE
        y=front+(back-front)*u
        z=rest.z
    else:
        u=(phase-STANCE)/(1.0-STANCE)
        su=smooth(u)
        y=back+(front-back)*su
        z=rest.z+FOOT_LIFT*math.sin(math.pi*u)
    return Vector((rest.x,y,z))

for fr in range(F0,F1+1):
    t=(fr-F0)/(F1-F0)
    lp=t%1.0
    rp=(t+0.5)%1.0
    L=foot_at(foot_l_rest,lp)
    R=foot_at(foot_r_rest,rp)
    key(ftL,fr,L); key(ftR,fr,R)
    # Poles stay forward and aligned to each leg's own x: knees cannot collapse inward/sideways.
    key(kpL,fr,(knee_l_rest.x,-H*0.30,knee_l_rest.z))
    key(kpR,fr,(knee_r_rest.x,-H*0.30,knee_r_rest.z))

    # Counter-swinging arms, deliberately modest as in normal walking.
    swing=math.sin(2*math.pi*t)*HAND_SWING
    zlift=H*0.006*math.cos(4*math.pi*t)
    key(whL,fr,(left_sign*hand_x,hand_y+swing,hand_z+zlift))
    key(whR,fr,(right_sign*hand_x,hand_y-swing,hand_z+zlift))
    key(weL,fr,(left_sign*(hand_x+H*0.10),-H*0.07+swing*0.30,shoulder_z-H*0.11))
    key(weR,fr,(right_sign*(hand_x+H*0.10),-H*0.07-swing*0.30,shoulder_z-H*0.11))

    # Small vertical body rhythm only; no side roll/yaw.
    pb[pelvis].rotation_mode='XYZ'; pb[pelvis].rotation_euler=(0,0,0)
    pb[pelvis].location=(0,0,H*0.008*(1.0-math.cos(4*math.pi*t))*0.5)
    pb[pelvis].keyframe_insert("rotation_euler",frame=fr)
    pb[pelvis].keyframe_insert("location",frame=fr)
    if spine:
        pb[spine].rotation_mode='XYZ'; pb[spine].rotation_euler=(H*0.0,0,0)
        pb[spine].keyframe_insert("rotation_euler",frame=fr)

bpy.context.view_layer.objects.active=arm; arm.select_set(True)
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.nla.bake(frame_start=F0,frame_end=F1,step=1,only_selected=False,visual_keying=True,
                 clear_constraints=True,clear_parents=False,use_current_action=True,bake_types={'POSE'})
bpy.ops.object.mode_set(mode='OBJECT')
walk=arm.animation_data.action; walk.name="walk"; walk.use_fake_user=True
relax_fingers(walk,(1,8,16,23,31))

for o in (ftL,ftR,kpL,kpR,whL,whR,weL,weR):
    if o and o.name in bpy.data.objects: bpy.data.objects.remove(o,do_unlink=True)

# Keep feet neutral/flat at contact frames.
arm.animation_data.action=walk
for fr in (1,10,16,25,31):
    bpy.context.scene.frame_set(fr)
    for n in (footL,footR):
        pb[n].rotation_mode='QUATERNION'
        # only soften extreme ankle twist; do not force a rigid world rotation
        q=pb[n].rotation_quaternion.copy()
        if abs(q.angle)>1.0:
            pb[n].rotation_quaternion=q.slerp(type(q)((1,0,0,0)),0.30)
        pb[n].keyframe_insert("rotation_quaternion",frame=fr)

arm.animation_data.action=None
for tr in list(arm.animation_data.nla_tracks): arm.animation_data.nla_tracks.remove(tr)
for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new(); tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]; st.action_frame_end=act.frame_range[1]

bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=60
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V13_FULL_IK_WALK",os.path.abspath(out),
      "speed",WALK_SPEED,"stance_distance",STANCE_DISTANCE,"lift",FOOT_LIFT)
