import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
normal_path,ihram_path,bus_path,standard_path,out=argv[:5]
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
    if not arm or not arm.animation_data: return
    chosen=None
    for tr in arm.animation_data.nla_tracks:
        for st in tr.strips:
            if st.action and st.action.name.lower().startswith(clip.lower()):
                chosen=st.action
        tr.mute=True
    if chosen:
        arm.animation_data.action=chosen
        print("PREVIEW ACTION",arm.name,chosen.name)
    else:
        for a in bpy.data.actions:
            if a.name.lower().startswith(clip.lower()):
                arm.animation_data.action=a; break

idle,arm_idle=import_group(normal_path,"IdlePlayer",(-4.2,-0.3,0),1.0,0)
walk,arm_walk=import_group(normal_path,"WalkPlayer",(-1.8,-0.3,0),1.0,0)
ihram,arm_ihram=import_group(ihram_path,"IhramPlayer",(0.7,-0.3,0),1.0,math.radians(180))
safir,_=import_group(bus_path,"SafirBus",(4.6,5.0,0),0.62,math.radians(-8))
std,_=import_group(standard_path,"StdBus",(-5.8,6.8,0),0.56,math.radians(7))

choose_action(arm_idle,"idle")
choose_action(arm_walk,"walk")
choose_action(arm_ihram,"idle")
bpy.context.scene.frame_set(9)

# ground
m=bpy.data.materials.new("Ground"); m.diffuse_color=(0.24,0.24,0.24,1)
bpy.ops.mesh.primitive_plane_add(size=40,location=(0,1,-0.02))
bpy.context.object.data.materials.append(m)

world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.07,0.085,0.11,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.60
bpy.ops.object.light_add(type='AREA',location=(-4,-6,8))
key=bpy.context.object; key.data.energy=1300; key.data.size=6; key.data.color=(1.0,.80,.62)
bpy.ops.object.light_add(type='AREA',location=(7,-2,5))
fill=bpy.context.object; fill.data.energy=850; fill.data.size=5; fill.data.color=(.58,.70,1.0)
bpy.ops.object.light_add(type='SUN',location=(0,0,10))
bpy.context.object.data.energy=2.0

def look_at(obj,p):
    obj.rotation_euler=(Vector(p)-obj.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(11,-15,6.4))
cam=bpy.context.object; cam.data.lens=52; look_at(cam,(0.2,1.0,1.5)); bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1400; scene.render.resolution_y=780; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=os.path.abspath(out)
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("V9_PREVIEW",os.path.abspath(out))
