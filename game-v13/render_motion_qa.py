import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
normal_path,ihram_path,npc_path,out_dir=argv[:4]
os.makedirs(out_dir,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)

def import_char(path):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    arm=next((o for o in objs if o.type=='ARMATURE'),None)
    if arm is None: raise RuntimeError("No armature "+path)
    return arm,objs

def get_action(prefix):
    return next((a for a in bpy.data.actions if a.name.lower().startswith(prefix)),None)

def pos(arm,bone):
    return arm.matrix_world @ arm.pose.bones[bone].matrix.translation

def validate_pose(arm,label):
    bpy.context.view_layer.update()
    required=("pelvis","hand_l","hand_r","upperarm_l","upperarm_r","thigh_l","thigh_r","calf_l","calf_r","foot_l","foot_r")
    if any(n not in arm.pose.bones for n in required):
        raise RuntimeError(label+" missing bones")
    pel=pos(arm,"pelvis"); lh=pos(arm,"hand_l"); rh=pos(arm,"hand_r")
    lu=pos(arm,"upperarm_l"); ru=pos(arm,"upperarm_r")
    lt=pos(arm,"thigh_l"); rt=pos(arm,"thigh_r")
    lk=pos(arm,"calf_l"); rk=pos(arm,"calf_r")
    lf=pos(arm,"foot_l"); rf=pos(arm,"foot_r")
    s=1.0 if lu.x>ru.x else -1.0
    lg=s*(lh.x-pel.x); rg=-s*(rh.x-pel.x)
    if lg<0.055 or rg<0.055:
        raise RuntimeError(f"{label}: hand too close/crossing torso L={lg:.3f} R={rg:.3f}")
    if lh.z>lu.z-0.08 or rh.z>ru.z-0.08:
        raise RuntimeError(label+": arms too high")
    lks=s*(lk.x-pel.x); rks=-s*(rk.x-pel.x)
    lfs=s*(lf.x-pel.x); rfs=-s*(rf.x-pel.x)
    if lks < -0.035 or rks < -0.035:
        raise RuntimeError(f"{label}: knee crossed body center L={lks:.3f} R={rks:.3f}")
    if lks > 0.42 or rks > 0.42:
        raise RuntimeError(f"{label}: knee kicked sideways L={lks:.3f} R={rks:.3f}")
    if lfs < -0.10 or rfs < -0.10:
        raise RuntimeError(f"{label}: foot crossed unnaturally L={lfs:.3f} R={rfs:.3f}")
    if abs(lk.x-lt.x) > 0.30 or abs(rk.x-rt.x) > 0.30:
        raise RuntimeError(label+": excessive lateral knee displacement")
    if abs(lk.x-rk.x) < 0.10:
        raise RuntimeError(label+": knees collapsed toward each other")
    if abs(lf.x-rf.x) < 0.09:
        raise RuntimeError(label+": feet crossed or collapsed toward each other")
    print("POSE_OK",label,"hands",round(lg,3),round(rg,3),
          "knees",round(lks,3),round(rks,3),"feet",lf,rf)

def setup_scene():
    mat=bpy.data.materials.new("Ground"); mat.diffuse_color=(0.31,0.31,0.30,1)
    bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0,-.02))
    bpy.context.object.data.materials.append(mat)
    world=bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world=world; world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.52,0.56,0.62,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7
    bpy.ops.object.light_add(type='SUN',location=(0,-4,9))
    sun=bpy.context.object; sun.data.energy=2.2; sun.rotation_euler=(math.radians(35),0,math.radians(-25))
    bpy.ops.object.light_add(type='AREA',location=(-3,-5,6))
    bpy.context.object.data.energy=850; bpy.context.object.data.size=4.5
    bpy.ops.object.light_add(type='AREA',location=(5,-1,4))
    bpy.context.object.data.energy=500; bpy.context.object.data.size=3.5
    bpy.ops.object.camera_add(location=(2.0,-4.5,1.85))
    cam=bpy.context.object; cam.data.lens=68
    cam.rotation_euler=(Vector((0,0,0.95))-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera=cam
    s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'
    s.render.resolution_x=480; s.render.resolution_y=480; s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'
    s.view_settings.look='AgX - Medium High Contrast'
    return cam

def render_character(path,clip,frame,name,view="front"):
    clear()
    arm,objs=import_char(path)
    act=get_action(clip)
    if act is None: raise RuntimeError("Missing "+clip+" in "+path)
    arm.animation_data_create()
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    arm.animation_data.action=act
    bpy.context.scene.frame_set(frame)
    validate_pose(arm,name)
    cam=setup_scene()
    if view=="back":
        cam.location=(-2.0,4.5,1.85)
        cam.rotation_euler=(Vector((0,0,0.95))-cam.location).to_track_quat('-Z','Y').to_euler()
    elif view=="side":
        cam.location=(4.7,0.0,1.75)
        cam.data.lens=62
        cam.rotation_euler=(Vector((0,0,0.95))-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.render.filepath=os.path.join(out_dir,name+".png")
    bpy.ops.render.render(write_still=True)

clear(); arm,_=import_char(normal_path); walk=get_action("walk")
if walk is None: raise RuntimeError("No walk action")
f0=int(round(walk.frame_range[0])); f1=int(round(walk.frame_range[1])); span=max(1,f1-f0)
frames8=[f0 + (span*i)//8 for i in range(8)]
frames4=[frames8[i] for i in (0,2,4,6)]
for i,fr in enumerate(frames4):
    render_character(normal_path,"walk",fr,f"walk_{i}")
for i,fr in enumerate(frames8):
    render_character(normal_path,"walk",fr,f"walk_side_{i}",view="side")
render_character(normal_path,"idle",1,"idle_front")
render_character(normal_path,"idle",1,"idle_side",view="side")
render_character(ihram_path,"idle",1,"ihram_front")
render_character(ihram_path,"idle",1,"ihram_back",view="back")
try:
    render_character(npc_path,"walk",frames8[2],"npc_walk")
except Exception as e:
    print("NPC_QA_WARNING",repr(e))
    # NPC validation must not block player walk preview/build acceptance.

print("V14_MOTION_QA_RENDERED",out_dir)
