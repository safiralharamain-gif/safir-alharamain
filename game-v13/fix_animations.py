import bpy, os, sys, math
from mathutils import Vector, Matrix, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
src, out = argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
if arm is None:
    raise SystemExit("No armature")

arm.animation_data_create()
pb = arm.pose.bones
bones = arm.data.bones

def find(*names):
    for n in names:
        if n in pb:
            return n
    return None

pelvis=find("pelvis")
uaL=find("upperarm_l"); uaR=find("upperarm_r")
laL=find("lowerarm_l"); laR=find("lowerarm_r")
handL=find("hand_l"); handR=find("hand_r")
thL=find("thigh_l"); thR=find("thigh_r")
caL=find("calf_l"); caR=find("calf_r")
footL=find("foot_l"); footR=find("foot_r")
head=find("head")
spine=find("spine_02","spine_01")
required=[pelvis,uaL,uaR,laL,laR,handL,handR,thL,thR,caL,caR,footL,footR]
if any(x is None for x in required):
    raise SystemExit("Missing required game-engine rig bones")

# IMPORTANT: keep the MakeHuman/CMU BVH-retargeted walk that arrived in the raw GLB.
mocap_walk = next((a for a in bpy.data.actions if a.name.lower() == "walk"), None)
if mocap_walk is None:
    mocap_walk = next((a for a in bpy.data.actions if "walk" in a.name.lower()), None)
if mocap_walk is None:
    raise SystemExit("No imported mocap walk action found")

mocap_walk.use_fake_user=True
mocap_walk.name="walk"

# Drop imported NLA tracks so we can rebuild a clean two-clip library.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
arm.animation_data.action=None

# Keep only the imported mocap walk; rebuild idle ourselves so the arms are down naturally.
for a in list(bpy.data.actions):
    if a != mocap_walk:
        bpy.data.actions.remove(a)

pts=[p for b in bones for p in (b.head_local,b.tail_local)]
H=max(0.1,max(p.z for p in pts)-min(p.z for p in pts))
forward=Vector((0.0,-1.0,0.0))

def local_head(bn):
    return bones[bn].head_local.copy()

def world_point(v):
    return arm.matrix_world @ Vector(v)

def make_target(name,bone_name=None):
    e=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(e)
    if bone_name:
        e.matrix_world=arm.matrix_world @ bones[bone_name].matrix_local
    return e

def set_target_local(obj,v,frame=None):
    obj.location=world_point(v)
    if frame is not None:
        obj.keyframe_insert("location",frame=frame)

def add_ik(end_bone,target,pole):
    c=pb[end_bone].constraints.new("IK")
    c.target=target
    c.pole_target=pole
    c.chain_count=2
    c.use_rotation=False
    c.iterations=64
    return c

def clear_pose():
    for b in pb:
        b.location=(0,0,0)
        b.scale=(1,1,1)
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=(1,0,0,0)

def local_axis_for_world(bn,axis):
    v=bones[bn].matrix_local.to_3x3().inverted() @ Vector(axis)
    v.normalize()
    return v

def set_bone_axis_angle(bn,world_axis,angle,frame):
    if not bn:
        return
    pb[bn].rotation_mode='QUATERNION'
    pb[bn].rotation_quaternion=Quaternion(local_axis_for_world(bn,world_axis),angle)
    pb[bn].keyframe_insert("rotation_quaternion",frame=frame)

def strip_rotation_channels(action,bn):
    paths={
        f'pose.bones["{bn}"].rotation_quaternion',
        f'pose.bones["{bn}"].rotation_euler',
        f'pose.bones["{bn}"].rotation_axis_angle',
    }
    for fc in list(action.fcurves):
        if fc.data_path in paths:
            action.fcurves.remove(fc)

def strip_root_motion(action):
    # The game owns world translation. Keep walk strictly in-place.
    bad_paths={"location"}
    for fc in list(action.fcurves):
        dp=fc.data_path
        if dp in bad_paths or dp == f'pose.bones["{pelvis}"].location':
            action.fcurves.remove(fc)

def orient_wrists_inward(action):
    """Preserve the approved palm direction while keeping the mocap arm swing."""
    arm.animation_data.action=action
    f0=int(math.floor(action.frame_range[0]))
    f1=int(math.ceil(action.frame_range[1]))

    configs=[]
    for hand_bn,fore_bn,side in ((handL,laL,"l"),(handR,laR,"r")):
        thumb_bn=f"thumb_01_{side}"
        if thumb_bn not in bones:
            raise RuntimeError("Missing thumb bone: "+thumb_bn)

        rest_rot=bones[hand_bn].matrix_local.to_3x3()
        local_y=Vector((0.0,1.0,0.0))
        thumb_arm=bones[thumb_bn].head_local-bones[hand_bn].head_local
        thumb_local=rest_rot.inverted() @ thumb_arm
        local_x=thumb_local-local_y*thumb_local.dot(local_y)
        if local_x.length < 1e-6:
            raise RuntimeError("Degenerate thumb axis on "+hand_bn)
        local_x.normalize()
        local_z=local_x.cross(local_y); local_z.normalize()
        local_x=local_y.cross(local_z); local_x.normalize()
        local_basis=Matrix((local_x,local_y,local_z)).transposed()
        configs.append((hand_bn,fore_bn,local_basis))
        strip_rotation_channels(action,hand_bn)

    for fr in range(f0,f1+1):
        bpy.context.scene.frame_set(fr)
        bpy.context.view_layer.update()
        for hand_bn,fore_bn,local_basis in configs:
            fore=pb[fore_bn]
            hand=pb[hand_bn]
            target_y=(fore.tail-fore.head)
            if target_y.length < 1e-6:
                continue
            target_y.normalize()

            target_x=forward-target_y*forward.dot(target_y)
            if target_x.length < 1e-6:
                target_x=Vector((1.0,0.0,0.0))
                target_x=target_x-target_y*target_x.dot(target_y)
            target_x.normalize()

            target_z=target_x.cross(target_y); target_z.normalize()
            target_x=target_y.cross(target_z); target_x.normalize()
            target_basis=Matrix((target_x,target_y,target_z)).transposed()
            desired_rot=target_basis @ local_basis.inverted()

            pos=hand.matrix.to_translation()
            hand.matrix=Matrix.Translation(pos) @ desired_rot.to_4x4()
            bpy.context.view_layer.update()
            hand.rotation_mode='QUATERNION'
            hand.keyframe_insert("rotation_quaternion",frame=fr)
    arm.animation_data.action=None

def finger_relax(action):
    """Use the already-approved light finger curl, constant through the clip."""
    arm.animation_data.action=action
    f0=int(math.floor(action.frame_range[0]))
    f1=int(math.ceil(action.frame_range[1]))
    curl={"01":-0.12,"02":-0.24,"03":-0.18}
    thumb={"01":-0.04,"02":-0.07,"03":-0.05}
    names=[]
    for side in ("l","r"):
        for finger in ("index","middle","ring","pinky"):
            for seg,ang in curl.items():
                names.append((f"{finger}_{seg}_{side}",ang))
        for seg,ang in thumb.items():
            names.append((f"thumb_{seg}_{side}",ang))

    for bn,ang in names:
        if bn not in pb:
            continue
        strip_rotation_channels(action,bn)
        pb[bn].rotation_mode='QUATERNION'
        q=Quaternion(Vector((0.0,0.0,1.0)),ang)
        pb[bn].rotation_quaternion=q
        pb[bn].keyframe_insert("rotation_quaternion",frame=f0)
        pb[bn].rotation_quaternion=q
        pb[bn].keyframe_insert("rotation_quaternion",frame=f1)
    arm.animation_data.action=None

def bake_action(name,start,end):
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(frame_start=start,frame_end=end,step=1,only_selected=False,
                     visual_keying=True,clear_constraints=True,clear_parents=False,
                     use_current_action=True,bake_types={'POSE'})
    bpy.ops.object.mode_set(mode='OBJECT')
    act=arm.animation_data.action
    act.name=name
    act.use_fake_user=True
    return act

# ---------- Neutral idle (same approved arm/hand placement) ----------
clear_pose()
idle=bpy.data.actions.new("idle")
arm.animation_data.action=idle

hL=make_target("Idle_HandL",handL); hR=make_target("Idle_HandR",handR)
eL=make_target("Idle_ElbowPoleL"); eR=make_target("Idle_ElbowPoleR")
add_ik(laL,hL,eL); add_ik(laR,hR,eR)

shoulderL=local_head(uaL); shoulderR=local_head(uaR)
hipL=local_head(thL); hipR=local_head(thR)
left_sign=1.0 if hipL.x > hipR.x else -1.0
right_sign=-left_sign

hand_side=H*0.065
hand_drop=H*0.170
idle_hL=Vector((hipL.x + left_sign*hand_side, hipL.y-H*0.012, hipL.z-hand_drop))
idle_hR=Vector((hipR.x + right_sign*hand_side, hipR.y-H*0.012, hipR.z-hand_drop))
pole_out=H*0.085
pole_back=H*0.045
idle_eL=Vector((shoulderL.x+left_sign*pole_out, shoulderL.y+pole_back, shoulderL.z-H*0.115))
idle_eR=Vector((shoulderR.x+right_sign*pole_out, shoulderR.y+pole_back, shoulderR.z-H*0.115))

for fr,breathe in ((1,0.0),(30,H*0.003),(60,0.0)):
    set_target_local(hL,idle_hL+Vector((0,0,breathe)),fr)
    set_target_local(hR,idle_hR+Vector((0,0,breathe)),fr)
    set_target_local(eL,idle_eL,fr); set_target_local(eR,idle_eR,fr)
    pb[pelvis].location=(0.0,0.0,breathe*0.20)
    pb[pelvis].keyframe_insert("location",frame=fr)
    if spine:
        set_bone_axis_angle(spine,(1,0,0),math.radians(0.5),fr)
    if head:
        set_bone_axis_angle(head,(1,0,0),0.0,fr)

idle=bake_action("idle",1,60)
orient_wrists_inward(idle)
finger_relax(idle)
for o in (hL,hR,eL,eR):
    if o.name in bpy.data.objects:
        bpy.data.objects.remove(o,do_unlink=True)

# ---------- Real mocap walk from MakeHuman retarget ----------
walk=mocap_walk
walk.name="walk"
walk.use_fake_user=True
strip_root_motion(walk)

# The BVH already contains natural pelvis, spine, leg, knee, foot and arm timing.
# Touch only wrists/fingers so the approved hand pose is never lost.
orient_wrists_inward(walk)
finger_relax(walk)

# Clean NLA library: only idle + real mocap walk.
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
for a in list(bpy.data.actions):
    if a not in (idle,walk):
        bpy.data.actions.remove(a)

for act in (idle,walk):
    tr=arm.animation_data.nla_tracks.new()
    tr.name=act.name
    st=tr.strips.new(act.name,int(act.frame_range[0]),act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]
arm.animation_data.action=None

bpy.context.scene.render.fps=30
bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=max(60,int(walk.frame_range[1]))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
                          export_animations=True,export_animation_mode='ACTIONS',
                          export_yup=True,export_materials='EXPORT',export_apply=False)
print("V19_MOCAP_WALK_APPROVED_HANDS",os.path.abspath(out),
      "walk_frames",tuple(round(x,2) for x in walk.frame_range))
