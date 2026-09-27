import bpy, os, sys, math
from mathutils import Matrix

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]
out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature found")

ad=arm.animation_data_create()
pb=arm.pose.bones

def find_action(token):
    token=token.lower()
    for a in bpy.data.actions:
        if token in a.name.lower():
            return a
    return None

walk=find_action("walk")
if walk is None:
    raise SystemExit("No walk action found in generated GLB")

# Remove old generated non-walk clips. We'll derive a clean idle and run from the real walk.
for a in list(bpy.data.actions):
    if a != walk:
        bpy.data.actions.remove(a)

# Strip all finger and wrist rotation tracks from the walk.
# The mocap has no finger capture, and the prior hand overrides were what produced twisted palms.
bad_tokens=[
    "index_","middle_","ring_","pinky_","thumb_",
    'pose.bones["hand_l"]','pose.bones["hand_r"]'
]
try:
    for fc in list(walk.fcurves):
        if any(tok in fc.data_path for tok in bad_tokens):
            walk.fcurves.remove(fc)
except Exception as e:
    print("FCURVE_STRIP_NOTE",repr(e))

walk.name="walk"
walk.use_fake_user=True

# Find the most neutral frame in the real walk: both hands at roughly the same fore/aft position.
handL=pb.get("hand_l"); handR=pb.get("hand_r")
uaL=pb.get("upperarm_l"); uaR=pb.get("upperarm_r")
laL=pb.get("lowerarm_l"); laR=pb.get("lowerarm_r")
clL=pb.get("clavicle_l"); clR=pb.get("clavicle_r")
sp1=pb.get("spine_01"); sp2=pb.get("spine_02"); sp3=pb.get("spine_03")
neck=pb.get("neck_01"); head=pb.get("head")
pelvis=pb.get("pelvis")

start=max(1,int(math.floor(walk.frame_range[0])))
end=max(start+1,int(math.ceil(walk.frame_range[1])))
ad.action=walk
best_frame=start
best_score=1e9
for f in range(start,end+1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    if handL and handR:
        hl=handL.matrix.translation
        hr=handR.matrix.translation
        # Neutral arm swing: hands side-by-side in fore/aft direction and similar vertical level.
        score=abs(hl.y-hr.y)*6.0 + abs(hl.z-hr.z)*1.5
        if score < best_score:
            best_score=score
            best_frame=f
print("NEUTRAL_WALK_FRAME",best_frame,"score",best_score)

bpy.context.scene.frame_set(best_frame)
bpy.context.view_layer.update()

# Capture only a relaxed upper-body pose from the real mocap.
capture_names=[
    "clavicle_l","clavicle_r","upperarm_l","upperarm_r",
    "lowerarm_l","lowerarm_r","hand_l","hand_r",
    "spine_01","spine_02","spine_03","neck_01","head"
]
captured={}
for n in capture_names:
    if n in pb:
        captured[n]=pb[n].matrix_basis.copy()

# Reset all bones to their bind pose first.
ad.action=None
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

# Create a stable idle from the neutral mocap upper body while legs/pelvis stay in bind pose.
idle=bpy.data.actions.new("idle")
idle.use_fake_user=True
ad.action=idle
for fr in (1,30,60):
    for n,m in captured.items():
        b=pb[n]
        b.rotation_mode='QUATERNION'
        b.rotation_quaternion=m.to_quaternion()
        b.location=(0,0,0)
        b.scale=(1,1,1)
        b.keyframe_insert("rotation_quaternion",frame=fr)
        b.keyframe_insert("location",frame=fr)
# Tiny breathing only in spine; no arm or hand distortion.
if sp2:
    sp2.rotation_mode='XYZ'
    for fr,x in ((1,0.0),(30,0.018),(60,0.0)):
        sp2.rotation_euler=(x,0,0)
        sp2.keyframe_insert("rotation_euler",frame=fr)
ad.action=None

# Run uses the same proven human walk cycle; Godot plays it faster.
# This is deliberately safer than a separately hand-authored run that can break knees/wrists.
run=walk.copy()
run.name="run"
run.use_fake_user=True

# Remove any remaining hand/finger curves from idle/run too.
for act in (idle,run):
    try:
        for fc in list(act.fcurves):
            if any(tok in fc.data_path for tok in bad_tokens):
                act.fcurves.remove(fc)
    except Exception as e:
        print("CLEAN_NOTE",act.name,repr(e))

# Ensure all three clips are explicitly attached to this armature for glTF ACTIONS export.
for tr in list(ad.nla_tracks):
    ad.nla_tracks.remove(tr)
for act in (idle,walk,run):
    tr=ad.nla_tracks.new()
    tr.name=act.name
    st=tr.strips.new(act.name,1,act)
    st.action_frame_start=act.frame_range[0]
    st.action_frame_end=act.frame_range[1]

# Return to clean bind/rest state before export.
ad.action=None
for b in pb:
    b.rotation_mode='QUATERNION'
    b.rotation_quaternion=(1,0,0,0)
    b.location=(0,0,0)
    b.scale=(1,1,1)

bpy.context.scene.frame_start=1
bpy.context.scene.frame_end=max(60,end)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(
    filepath=os.path.abspath(out),
    export_format='GLB',
    use_selection=True,
    export_animations=True,
    export_animation_mode='ACTIONS',
    export_yup=True,
    export_materials='EXPORT',
    export_apply=False
)
print("V12_CLEAN_MOCAP_EXPORTED",os.path.abspath(out))
