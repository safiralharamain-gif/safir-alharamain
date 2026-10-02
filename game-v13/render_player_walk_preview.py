import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src,out_dir=argv[:2]
os.makedirs(out_dir,exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

def load():
    clear()
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
    arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
    if arm is None: raise RuntimeError("No armature")
    walk=next((a for a in bpy.data.actions if a.name.lower().startswith("walk")),None)
    if walk is None: raise RuntimeError("No walk action")
    arm.animation_data_create()
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    arm.animation_data.action=walk
    return arm,walk

def scene(view):
    mat=bpy.data.materials.new("Ground")
    mat.diffuse_color=(0.31,0.31,0.30,1)
    bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0,-.02))
    bpy.context.object.data.materials.append(mat)

    world=bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world=world
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.52,0.56,0.62,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7

    bpy.ops.object.light_add(type='SUN',location=(0,-4,9))
    sun=bpy.context.object
    sun.data.energy=2.2
    sun.rotation_euler=(math.radians(35),0,math.radians(-25))

    bpy.ops.object.light_add(type='AREA',location=(-3,-5,6))
    bpy.context.object.data.energy=850
    bpy.context.object.data.size=4.5

    if view=="side":
        loc=(4.7,0.0,1.75)
    elif view=="threeq":
        loc=(3.4,-3.4,1.82)
    else:
        loc=(2.0,-4.5,1.85)

    bpy.ops.object.camera_add(location=loc)
    cam=bpy.context.object
    cam.data.lens=64
    target=Vector((0,0,0.95))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera=cam

    s=bpy.context.scene
    s.render.engine='BLENDER_WORKBENCH'
    s.render.resolution_x=500
    s.render.resolution_y=500
    s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'
    s.view_settings.look='AgX - Medium High Contrast'

def render(frame,name,view):
    arm,walk=load()
    bpy.context.scene.frame_set(frame)
    scene(view)
    bpy.context.scene.render.filepath=os.path.join(out_dir,name+".png")
    bpy.ops.render.render(write_still=True)

clear()
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
walk=next((a for a in bpy.data.actions if a.name.lower().startswith("walk")),None)
if walk is None: raise RuntimeError("No walk")
f0=int(round(walk.frame_range[0])); f1=int(round(walk.frame_range[1]))
span=max(1,f1-f0)
frames8=[f0+(span*i)//8 for i in range(8)]
frames4=[frames8[i] for i in (0,2,4,6)]

for i,fr in enumerate(frames8):
    render(fr,f"side_{i}","side")
for i,fr in enumerate(frames4):
    render(fr,f"front_{i}","front")
for i,fr in enumerate(frames4):
    render(fr,f"threeq_{i}","threeq")

print("PLAYER_MOCAP_PREVIEW",f0,f1,frames8,out_dir)
