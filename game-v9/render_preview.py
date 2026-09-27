import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
(normal_path,ihram_path,npc_old,npc_dark,npc_young,npc_stocky,bus_path,standard_path,out)=argv[:9]
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def import_group(path,name,loc,scale=1.0,rot=0.0):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    arm=None
    for o in objs:
        if o.parent is None: o.parent=root
        if o.type=='ARMATURE': arm=o
    root.location=loc; root.scale=(scale,scale,scale); root.rotation_euler.z=rot
    return root,arm

def choose_action(arm,clip):
    if not arm: return
    if not arm.animation_data: arm.animation_data_create()
    chosen=None
    for a in bpy.data.actions:
        if a.name.lower().startswith(clip.lower()):
            chosen=a
            break
    if chosen:
        arm.animation_data.action=chosen
        print("PREVIEW ACTION",arm.name,chosen.name)

# Main player: relaxed idle, walking pose, and ihram reference pose.
idle,arm_idle=import_group(normal_path,"PlayerIdle",(-4.7,-1.4,0),1.0,0)
walk,arm_walk=import_group(normal_path,"PlayerWalk",(-2.3,-1.4,0),1.0,0)
ihram,arm_ihram=import_group(ihram_path,"PlayerIhram",(0.2,-1.4,0),1.0,0)
choose_action(arm_idle,"idle")
choose_action(arm_walk,"walk")
choose_action(arm_ihram,"idle")

# Four genuinely different NPCs for visual QA.
o1,a1=import_group(npc_old,"NpcOlder",(-5.8,2.0,0),0.98,math.radians(6))
o2,a2=import_group(npc_dark,"NpcDark",(-3.2,2.2,0),1.03,math.radians(-5))
o3,a3=import_group(npc_young,"NpcYoung",(-0.5,2.1,0),0.96,math.radians(4))
o4,a4=import_group(npc_stocky,"NpcStocky",(2.3,2.2,0),1.04,math.radians(-4))
for a in (a1,a2,a3,a4):
    choose_action(a,"idle")

# SAFIR bus + one fleet bus.
safir,_=import_group(bus_path,"SafirBus",(6.4,5.7,0),0.58,math.radians(-8))
std,_=import_group(standard_path,"StdBus",(-7.2,7.0,0),0.50,math.radians(8))

bpy.context.scene.frame_set(9)

# Ground.
m=bpy.data.materials.new("Ground"); m.diffuse_color=(0.22,0.23,0.24,1)
bpy.ops.mesh.primitive_plane_add(size=44,location=(0,1,-0.02))
bpy.context.object.data.materials.append(m)

# Lighting.
world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.06,0.075,0.095,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.62
bpy.ops.object.light_add(type='AREA',location=(-4,-7,8))
key=bpy.context.object; key.data.energy=1450; key.data.size=6; key.data.color=(1.0,.80,.62)
bpy.ops.object.light_add(type='AREA',location=(8,-2,5))
fill=bpy.context.object; fill.data.energy=900; fill.data.size=5; fill.data.color=(.58,.70,1.0)
bpy.ops.object.light_add(type='SUN',location=(0,0,10))
bpy.context.object.data.energy=2.0

def look_at(obj,p):
    obj.rotation_euler=(Vector(p)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(12,-17,7.0))
cam=bpy.context.object; cam.data.lens=50; look_at(cam,(0.0,1.2,1.55)); bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1500; scene.render.resolution_y=840; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=os.path.abspath(out)
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("V9_PREVIEW",os.path.abspath(out))
