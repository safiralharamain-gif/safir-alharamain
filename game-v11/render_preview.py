import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
(normal_path,ihram_path,npc_old,npc_dark,npc_young,npc_stocky,
 miqat_path,bus_path,standard_path,out)=argv[:10]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def import_group(path,name,loc,scale=1.0,rot=0.0):
    before=set(bpy.data.objects); before_actions=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    acts=[a for a in bpy.data.actions if a not in before_actions]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    arm=None
    for o in objs:
        if o.parent is None:o.parent=root
        if o.type=='ARMATURE':arm=o
    root.location=loc; root.scale=(scale,scale,scale); root.rotation_euler.z=rot
    return root,arm,acts

def choose_action(arm,acts,clip):
    if not arm:return None
    if not arm.animation_data:arm.animation_data_create()
    chosen=next((a for a in acts if a.name.lower().startswith(clip.lower())),None)
    if chosen is None:
        chosen=next((a for a in bpy.data.actions if a.name.lower().startswith(clip.lower())),None)
    if chosen:
        arm.animation_data.action=chosen
        print("PREVIEW_ACTION",arm.name,chosen.name)
    return chosen

def bone_pos(arm,name):
    if not arm or name not in arm.pose.bones:return None
    return arm.matrix_world @ arm.pose.bones[name].head

def validate_relaxed(arm,label):
    bpy.context.view_layer.update()
    lh=bone_pos(arm,"hand_l"); rh=bone_pos(arm,"hand_r")
    lu=bone_pos(arm,"upperarm_l"); ru=bone_pos(arm,"upperarm_r")
    pel=bone_pos(arm,"pelvis")
    if None in (lh,rh,lu,ru,pel):raise RuntimeError(label+" missing pose bones")
    left_sign=1 if lu.x>ru.x else -1
    if left_sign*(lh.x-pel.x)<.06:raise RuntimeError(label+" left hand crossed torso")
    if -left_sign*(rh.x-pel.x)<.06:raise RuntimeError(label+" right hand crossed torso")
    if lh.z>lu.z-.12 or rh.z>ru.z-.12:raise RuntimeError(label+" arms still raised")
    if abs(lh.x-rh.x)<.26:raise RuntimeError(label+" hands clasped/too close")
    print("POSE_OK",label,lh,rh)

# Environment behind the QA lineup.
miqat,_,_=import_group(miqat_path,"MiqatAbyarAli",(0,8.5,0),0.64,0)
safir,_,_=import_group(bus_path,"SafirBus",(9.0,11.5,0),0.45,math.radians(-8))
std,_,_=import_group(standard_path,"StdBus",(-9.5,12.0,0),0.42,math.radians(8))

# Main player states.
idle,arm_idle,a_idle=import_group(normal_path,"PlayerIdle",(-6.2,-5.0,0),1.0,0)
walk,arm_walk,a_walk=import_group(normal_path,"PlayerWalk",(-3.6,-5.0,0),1.0,0)
ihram,arm_ihram,a_ihram=import_group(ihram_path,"PlayerIhramFront",(-0.7,-5.0,0),1.0,0)
ihram_back,arm_ib,a_ib=import_group(ihram_path,"PlayerIhramBack",(2.1,-5.0,0),1.0,math.pi)

choose_action(arm_idle,a_idle,"idle")
choose_action(arm_walk,a_walk,"walk")
choose_action(arm_ihram,a_ihram,"idle")
choose_action(arm_ib,a_ib,"idle")

# Diverse background people.
o1,a1,aa1=import_group(npc_old,"NpcOlder",(-5.8,.1,0),.97,math.radians(7))
o2,a2,aa2=import_group(npc_dark,"NpcDark",(-3.2,.3,0),1.03,math.radians(-4))
o3,a3,aa3=import_group(npc_young,"NpcYoung",(3.2,.2,0),.95,math.radians(4))
o4,a4,aa4=import_group(npc_stocky,"NpcStocky",(5.5,.3,0),1.04,math.radians(-6))
for a,acts in [(a1,aa1),(a2,aa2),(a3,aa3),(a4,aa4)]:choose_action(a,acts,"idle")

bpy.context.scene.frame_set(1)
validate_relaxed(arm_idle,"normal idle")
validate_relaxed(arm_ihram,"ihram idle")
bpy.context.scene.frame_set(7)
# Walking hands may swing, but must remain on their own side of the body.
validate_relaxed(arm_walk,"walk frame 7")

# Ground.
m=bpy.data.materials.new("PreviewGround");m.diffuse_color=(.30,.29,.25,1)
bpy.ops.mesh.primitive_plane_add(size=76,location=(0,3,-.03));bpy.context.object.data.materials.append(m)

world=bpy.context.scene.world or bpy.data.worlds.new("World");bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.35,.50,.72,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.75
bpy.ops.object.light_add(type='SUN',location=(0,-6,14))
sun=bpy.context.object;sun.data.energy=2.35;sun.rotation_euler=(math.radians(32),math.radians(-18),math.radians(-28))
bpy.ops.object.light_add(type='AREA',location=(-5,-9,10))
key=bpy.context.object;key.data.energy=1350;key.data.size=7;key.data.color=(1,.84,.67)
bpy.ops.object.light_add(type='AREA',location=(9,-3,7))
fill=bpy.context.object;fill.data.energy=900;fill.data.size=6;fill.data.color=(.62,.72,1)

def look_at(o,p):o.rotation_euler=(Vector(p)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(15,-23,8.5))
cam=bpy.context.object;cam.data.lens=52;look_at(cam,(0,2.5,1.9));bpy.context.scene.camera=cam

scene=bpy.context.scene
scene.render.engine='BLENDER_EEVEE_NEXT'
scene.render.resolution_x=1700;scene.render.resolution_y=950;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=os.path.abspath(out)
scene.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("V11_PREVIEW",os.path.abspath(out))
