import bpy, os, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
glb_path, out_dir, tag = argv[:3]
os.makedirs(out_dir, exist_ok=True)

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

def load_char():
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(glb_path))
    arm = next((o for o in bpy.data.objects if o.type=='ARMATURE'), None)
    if arm is None:
        raise RuntimeError("No armature")
    act = next((a for a in bpy.data.actions if a.name.lower().startswith("idle")), None)
    if act is None:
        raise RuntimeError("No idle action")
    arm.animation_data_create()
    for tr in list(arm.animation_data.nla_tracks):
        arm.animation_data.nla_tracks.remove(tr)
    arm.animation_data.action = act
    bpy.context.scene.frame_set(1)
    return arm

def setup(view):
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0,0,-0.02))
    world=bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world=world
    world.use_nodes=True
    world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.42,0.44,0.47,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.8
    bpy.ops.object.light_add(type='AREA', location=(-3,-4,5))
    bpy.context.object.data.energy=700
    bpy.context.object.data.size=4
    bpy.ops.object.light_add(type='AREA', location=(3,1,4))
    bpy.context.object.data.energy=450
    bpy.context.object.data.size=3

    if view=="front":
        loc=(0.0,-4.2,1.25)
    elif view=="side":
        loc=(4.2,0.0,1.25)
    else:
        loc=(3.1,-3.1,1.25)
    bpy.ops.object.camera_add(location=loc)
    cam=bpy.context.object
    cam.data.lens=72
    target=Vector((0,0,1.05))
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.scene.camera=cam
    s=bpy.context.scene
    s.render.engine='BLENDER_WORKBENCH'
    s.render.resolution_x=520
    s.render.resolution_y=520
    s.render.resolution_percentage=100
    s.render.image_settings.file_format='PNG'
    return cam

for view in ("front","side","threeq"):
    clear()
    arm=load_char()
    setup(view)
    bpy.context.scene.render.filepath=os.path.join(out_dir,f"{tag}_{view}.png")
    bpy.ops.render.render(write_still=True)

print("WRIST_VARIANT_RENDERED", tag, out_dir)
