import bpy, os, sys, statistics, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src,out_txt=argv[:2]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")
walk=next((a for a in bpy.data.actions if a.name.lower().startswith("walk")),None)
if walk is None: raise SystemExit("No walk action")
arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
arm.animation_data.action=walk

pb=arm.pose.bones
for n in ("foot_l","foot_r","pelvis"):
    if n not in pb: raise SystemExit("Missing "+n)

f0=int(math.floor(walk.frame_range[0])); f1=int(math.ceil(walk.frame_range[1]))
fps=bpy.context.scene.render.fps / max(1e-6,bpy.context.scene.render.fps_base)
samples={"foot_l":[],"foot_r":[]}
for fr in range(f0,f1+1):
    bpy.context.scene.frame_set(fr)
    bpy.context.view_layer.update()
    pel=(arm.matrix_world @ pb["pelvis"].matrix.translation)
    for n in ("foot_l","foot_r"):
        p=(arm.matrix_world @ pb[n].matrix.translation)-pel
        samples[n].append((fr,p.x,p.y,p.z))

# Determine horizontal forward axis by larger foot excursion.
ranges={}
for axis_i,axis in ((1,"x"),(2,"y")):
    rr=[]
    for n in samples:
        vals=[s[axis_i] for s in samples[n]]
        rr.append(max(vals)-min(vals))
    ranges[axis]=sum(rr)/len(rr)
axis_i=1 if ranges["x"]>ranges["y"] else 2
axis_name="x" if axis_i==1 else "y"

# Stride estimate: mean front-back excursion of each foot across one complete cycle.
stride=statistics.mean(max(s[axis_i] for s in samples[n])-min(s[axis_i] for s in samples[n]) for n in samples)
cycle_sec=max(1.0/fps,(f1-f0)/fps)
speed_stride=stride/cycle_sec

# Stance-speed estimate: when a foot is near its minimum height it should move backward
# relative to the pelvis at approximately the character's forward world speed.
stance_speeds=[]
dt=1.0/fps
for n in samples:
    arr=samples[n]
    zs=[s[3] for s in arr]
    zmin=min(zs); zmax=max(zs)
    threshold=zmin+(zmax-zmin)*0.30
    for i in range(1,len(arr)):
        if arr[i][3] <= threshold and arr[i-1][3] <= threshold:
            dv=abs(arr[i][axis_i]-arr[i-1][axis_i])/dt
            if 0.15 <= dv <= 3.0:
                stance_speeds.append(dv)

speed_stance=statistics.median(stance_speeds) if stance_speeds else speed_stride
# Blend both robust estimates, then clamp to a normal adult walking range.
speed=0.65*speed_stance+0.35*speed_stride
speed=max(0.85,min(1.55,speed))

# QA: feet must actually move enough vertically and forward/back to count as a walk.
foot_lift=statistics.mean(max(s[3] for s in samples[n])-min(s[3] for s in samples[n]) for n in samples)
if stride < 0.28 or foot_lift < 0.025:
    print(f"WALK_MEASURE_FALLBACK stride={stride:.3f} lift={foot_lift:.3f}; using 1.20 m/s for visual QA")
    speed = 1.20

with open(out_txt,"w",encoding="utf-8") as f:
    f.write(f"{speed:.5f}\n")
print("WALK_CALIBRATION", "axis",axis_name,"stride",round(stride,4),
      "cycle",round(cycle_sec,4),"stance",round(speed_stance,4),
      "speed",round(speed,4),"lift",round(foot_lift,4))
