import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
(normal_path,ihram_path,npc_old,npc_dark,npc_young,npc_stocky,
 miqat_path,bus_path,standard_path,out)=argv[:10]

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def import_group(path,name,loc,rot=0.0):
    before=set(bpy.data.objects); before_actions=set(bpy.data.actions)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    objs=[o for o in bpy.data.objects if o not in before]
    acts=[a for a in bpy.data.actions if a not in before_actions]
    root=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(root)
    arm=None
    for o in objs:
        if o.parent is None:o.parent=root
        if o.type=='ARMATURE':arm=o
    root.location=loc; root.rotation_euler.z=rot
    return root,arm,acts

def choose(arm,acts,clip):
    if not arm:return
    if not arm.animation_data:arm.animation_data_create()
    a=next((x for x in acts if x.name.lower().startswith(clip.lower())),None)
    if a is None:a=next((x for x in bpy.data.actions if x.name.lower().startswith(clip.lower())),None)
    if a:arm.animation_data.action=a

def p(arm,bone):
    return arm.matrix_world @ arm.pose.bones[bone].head if bone in arm.pose.bones else None

def validate(arm,label):
    bpy.context.view_layer.update()
    lh,rh=p(arm,"hand_l"),p(arm,"hand_r")
    lu,ru=p(arm,"upperarm_l"),p(arm,"upperarm_r")
    pel=p(arm,"pelvis")
    if None in (lh,rh,lu,ru,pel):raise RuntimeError(label+" missing bones")
    s=1 if lu.x>ru.x else -1
    if s*(lh.x-pel.x)<.045:raise RuntimeError(label+" left hand crossed torso")
    if -s*(rh.x-pel.x)<.045:raise RuntimeError(label+" right hand crossed torso")
    if lh.z>lu.z-.10 or rh.z>ru.z-.10:raise RuntimeError(label+" arms raised")
    if abs(lh.x-rh.x)<.23:raise RuntimeError(label+" hands clasped")
    print("POSE_OK",label,lh,rh)

idle,ai,aa=import_group(normal_path,"Idle",(-3.9,0,0))
walk,aw,wa=import_group(normal_path,"Walk",(-1.3,0,0))
ifr,ar,ra=import_group(ihram_path,"IhramFront",(1.35,0,0))
ibr,ab,ba=import_group(ihram_path,"IhramBack",(4.0,0,0),math.pi)
choose(ai,aa,"idle"); choose(aw,wa,"walk"); choose(ar,ra,"idle"); choose(ab,ba,"idle")

bpy.context.scene.frame_set(1)
validate(ai,"normal idle"); validate(ar,"ihram idle")
bpy.context.scene.frame_set(7)
validate(aw,"walk frame 7")

# neutral floor
mat=bpy.data.materials.new("Ground");mat.diffuse_color=(.28,.28,.27,1)
bpy.ops.mesh.primitive_plane_add(size=18,location=(0,0,-.02));bpy.context.object.data.materials.append(mat)

world=bpy.context.scene.world or bpy.data.worlds.new("World");bpy.context.scene.world=world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs["Color"].default_value=(.42,.48,.58,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value=.7
bpy.ops.object.light_add(type='SUN',location=(0,-4,9))
sun=bpy.context.object;sun.data.energy=2.1;sun.rotation_euler=(math.radians(35),0,math.radians(-25))
bpy.ops.object.light_add(type='AREA',location=(-3,-5,7))
bpy.context.object.data.energy=950;bpy.context.object.data.size=5
bpy.ops.object.light_add(type='AREA',location=(6,-2,5))
bpy.context.object.data.energy=550;bpy.context.object.data.size=4

def look(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(9,-14,5.2))
cam=bpy.context.object;cam.data.lens=58;look(cam,(0.2,0,1.15));bpy.context.scene.camera=cam

s=bpy.context.scene
s.render.engine='BLENDER_EEVEE_NEXT'
s.render.resolution_x=1200;s.render.resolution_y=700;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.filepath=os.path.abspath(out)
s.view_settings.look='AgX - Medium High Contrast'
bpy.ops.render.render(write_still=True)
print("V11_PREVIEW",os.path.abspath(out))
