import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
(normal_path,ihram_path,npc_old,npc_dark,npc_young,npc_stocky,
 miqat_path,bus_path,standard_path,out)=argv[:10]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def import_group(path,name,loc,scale=1.0,rot=0.0):
    before=set(bpy.data.objects)
    before_actions=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    acts=[a for a in bpy.data.actions if a not in before_actions]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    arm=None
    for o in objs:
        if o.parent is None: o.parent=root
        if o.type=='ARMATURE': arm=o
    root.location=loc; root.scale=(scale,scale,scale); root.rotation_euler.z=rot
    return root,arm,acts

def choose_action(arm,acts,clip):
    if not arm: return None
    if not arm.animation_data: arm.animation_data_create()
    chosen=None
    for a in acts:
        if a.name.lower().startswith(clip.lower()):
            chosen=a; break
    if chosen is None:
        for a in bpy.data.actions:
            if a.name.lower().startswith(clip.lower()):
                chosen=a; break
    if chosen:
        arm.animation_data.action=chosen
        print("PREVIEW_ACTION",arm.name,chosen.name)
    return chosen

def bone_pos(arm,name):
    if not arm or name not in arm.pose.bones: return None
    p=arm.pose.bones[name].head
    return arm.matrix_world @ p

def validate_relaxed(arm,label):
    if not arm: raise RuntimeError(label+" missing armature")
    bpy.context.view_layer.update()
    lh=bone_pos(arm,"hand_l"); rh=bone_pos(arm,"hand_r")
    lp=bone_pos(arm,"upperarm_l"); rp=bone_pos(arm,"upperarm_r")
    pel=bone_pos(arm,"pelvis")
    if None in (lh,rh,lp,rp,pel): return
    # Hands must stay on their own sides, below shoulders and not meet behind the spine.
    left_sign=1 if lp.x>rp.x else -1
    if left_sign*lh.x < left_sign*pel.x + 0.035:
        raise RuntimeError(label+" left hand crossed body center")
    if -left_sign*rh.x < -left_sign*pel.x + 0.035:
        raise RuntimeError(label+" right hand crossed body center")
    if lh.z>lp.z-0.10 or rh.z>rp.z-0.10:
        raise RuntimeError(label+" arms still raised/T-pose")
    if abs(lh.x-rh.x)<0.20:
        raise RuntimeError(label+" hands too close/clasped")
    print("POSE_OK",label,"LH",lh,"RH",rh)

# Full Abyar Ali-inspired environment in the background.
miqat,_,_=import_group(miqat_path,"MiqatAbyarAli",(0,6.0,0),0.72,0.0)

# Three states of the main player: idle, walking, dedicated ihram character.
idle,arm_idle,a_idle=import_group(normal_path,"PlayerIdle",(-5.4,-4.8,0),1.0,0)
walk,arm_walk,a_walk=import_group(normal_path,"PlayerWalk",(-2.8,-4.8,0),1.0,0)
ihram,arm_ihram,a_ihram=import_group(ihram_path,"PlayerIhram",(0.0,-4.8,0),1.0,0)
choose_action(arm_idle,a_idle,"idle")
choose_action(arm_walk,a_walk,"walk")
choose_action(arm_ihram,a_ihram,"idle")

# Four different NPC bodies around the courtyard.
o1,a1,aa1=import_group(npc_old,"NpcOlder",(-6.2,.2,0),0.98,math.radians(8))
o2,a2,aa2=import_group(npc_dark,"NpcDark",(-3.7,.5,0),1.04,math.radians(-6))
o3,a3,aa3=import_group(npc_young,"NpcYoung",(3.0,.2,0),0.95,math.radians(5))
o4,a4,aa4=import_group(npc_stocky,"NpcStocky",(5.2,.5,0),1.04,math.radians(-5))
for arm,acts in [(a1,aa1),(a2,aa2),(a3,aa3),(a4,aa4)]:
    choose_action(arm,acts,"idle")

# Fleet at the back, SAFIR clearly black/gold.
safir,_,_=import_group(bus_path,"SafirBus",(8.0,9.5,0),0.48,math.radians(-8))
std,_,_=import_group(standard_path,"StdBus",(-9.0,10.8,0),0.44,math.radians(9))

# Put walk cycle in a stride frame and idle characters in neutral.
bpy.context.scene.frame_set(1)
validate_relaxed(arm_idle,"player idle")
validate_relaxed(arm_ihram,"player ihram idle")
bpy.context.scene.frame_set(9)
validate_relaxed(arm_walk,"player walk frame 9")

# Ground extension around imported complex.
m=bpy.data.materials.new("PreviewGround"); m.diffuse_color=(0.28,0.27,0.24,1)
bpy.ops.mesh.primitive_plane_add(size=70,location=(0,3,-0.03))
bpy.context.object.data.materials.append(m)

# Warm daylight similar to Medina.
world=bpy.context.scene.world or bpy.data.worlds.new("World"); bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.34,0.48,0.68,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.72
bpy.ops.object.light_add(type='SUN',location=(0,-6,14))
sun=bpy.context.object; sun.data.energy=2.3; sun.rotation_euler=(math.radians(32),math.radians(-18),math.radians(-28))
bpy.ops.object.light_add(type='AREA',location=(-5,-8,10))
key=bpy.context.object; key.data.energy=1250; key.data.size=7; key.data.color=(1.0,.83,.66)
bpy.ops.object.light_add(type='AREA',location=(9,-3,7))
fill=bpy.context.object; fill.data.energy=850; fill.data.size=6; fill.data.color=(.62,.72,1.0)

def look_at(obj,p):
    obj.rotation_euler=(Vector(p)-obj.location).to_track_quat('-Z','Y').to_euler()

bpy.ops.object.camera_add(location=(15,-22,9.2))
cam=bpy.context.object; cam.data.lens=47; look_at(cam,(0,2.8,2.2)); bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1600; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=os.path.abspath(out)
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("V10_PREVIEW",os.path.abspath(out))
