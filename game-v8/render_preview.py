import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
ihram_path, safir_bus_path, standard_bus_path, out = argv[:4]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def import_group(path,name,loc,rot=0.0,scale=1.0):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    for o in objs:
        if o.parent is None:
            o.parent=root
    root.location=loc
    root.rotation_euler.z=rot
    root.scale=(scale,scale,scale)
    return root

# QA composition: player in ihram, SAFIR bus, two standard buses.
player=import_group(ihram_path,"Pilgrim",(-2.15,-1.3,0),math.radians(8),1.0)
safir=import_group(safir_bus_path,"SafirBus",(2.5,1.2,0),math.radians(-6),0.82)
std1=import_group(standard_bus_path,"Std1",(-4.8,5.3,0),math.radians(6),0.72)
std2=import_group(standard_bus_path,"Std2",(6.0,6.7,0),math.radians(-12),0.70)

# Ground / road.
mat=bpy.data.materials.new("Ground"); mat.diffuse_color=(0.23,0.24,0.25,1)
bpy.ops.mesh.primitive_plane_add(size=40,location=(0,0,-0.015))
ground=bpy.context.object; ground.data.materials.append(mat)

# Warm key + cool fill + sun.
world=bpy.context.scene.world or bpy.data.worlds.new("World")
bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.08,0.095,0.12,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.55

bpy.ops.object.light_add(type='AREA',location=(-4,-5,7))
key=bpy.context.object; key.data.energy=1150; key.data.shape='DISK'; key.data.size=5.0
key.data.color=(1.0,0.78,0.58)
bpy.ops.object.light_add(type='AREA',location=(6,-2,4))
fill=bpy.context.object; fill.data.energy=700; fill.data.size=5.0; fill.data.color=(0.55,0.68,1.0)
bpy.ops.object.light_add(type='SUN',location=(0,0,8))
sun=bpy.context.object; sun.rotation_euler=(math.radians(38),math.radians(-20),math.radians(-25)); sun.data.energy=2.0

# Camera helper.
def look_at(obj,pt):
    direction=Vector(pt)-obj.location
    obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

bpy.ops.object.camera_add(location=(10,-14,6.2))
cam=bpy.context.object
look_at(cam,(0.6,1.0,1.55))
cam.data.lens=48
bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.abspath(out)
scene.render.film_transparent=False
scene.render.image_settings.color_mode='RGBA'
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("PREVIEW_RENDERED",os.path.abspath(out))
