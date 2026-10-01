import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src,out_dir=argv[:2]
os.makedirs(out_dir,exist_ok=True)

def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

clear_scene()
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")
walk=next((a for a in bpy.data.actions if a.name.lower().startswith("walk")),None)
if walk is None:
    print("ACTIONS", [a.name for a in bpy.data.actions])
    raise SystemExit("No walk action")
arm.animation_data_create()
for tr in list(arm.animation_data.nla_tracks):
    arm.animation_data.nla_tracks.remove(tr)
arm.animation_data.action=walk

# ground + lighting
mat=bpy.data.materials.new("Ground"); mat.diffuse_color=(0.32,0.32,0.31,1)
bpy.ops.mesh.primitive_plane_add(size=12,location=(0,0,-.02))
bpy.context.object.data.materials.append(mat)
world=bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world=world; world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.50,0.53,0.58,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7
bpy.ops.object.light_add(type='SUN',location=(0,-4,9))
bpy.context.object.data.energy=2.2
bpy.ops.object.light_add(type='AREA',location=(-3,-4,5))
bpy.context.object.data.energy=750; bpy.context.object.data.size=4

s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH'
s.render.resolution_x=420; s.render.resolution_y=420; s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'

def camera_at(loc):
    bpy.ops.object.camera_add(location=loc)
    cam=bpy.context.object; cam.data.lens=62
    cam.rotation_euler=(Vector((0,0,0.95))-cam.location).to_track_quat('-Z','Y').to_euler()
    s.camera=cam
    return cam

f0=int(round(walk.frame_range[0])); f1=int(round(walk.frame_range[1]))
span=max(1,f1-f0)
frames=[f0, f0+span//8, f0+span//4, f0+3*span//8, f0+span//2, f0+5*span//8, f0+3*span//4, f0+7*span//8]
for i,fr in enumerate(frames):
    s.frame_set(fr); bpy.context.view_layer.update()
    cam=camera_at((4.7,0.0,1.75))
    s.render.filepath=os.path.join(out_dir,f"native_side_{i}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam,do_unlink=True)

for i,fr in enumerate(frames[::2]):
    s.frame_set(fr); bpy.context.view_layer.update()
    cam=camera_at((2.0,-4.5,1.85))
    s.render.filepath=os.path.join(out_dir,f"native_front_{i}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam,do_unlink=True)

print("NATIVE_WALK_PREVIEW", tuple(walk.frame_range), out_dir)
