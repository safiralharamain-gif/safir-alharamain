import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None: raise SystemExit("No armature")
meshes=[o for o in bpy.data.objects if o.type=='MESH']
pts=[]
for o in meshes:
    for p in o.bound_box: pts.append(o.matrix_world @ Vector(p))
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts); h=zmax-zmin
waist=zmin+h*0.53
ankle=zmin+h*0.075
chest=zmin+h*0.72
shoulder=zmin+h*0.84
print("V9 IHRAM BOUNDS",zmin,zmax,h)

def cloth_mat():
    m=bpy.data.materials.new("IhramWhiteFabric")
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(0.97,0.965,0.94,1)
    bs.inputs["Roughness"].default_value=0.94
    if "Sheen Weight" in bs.inputs: bs.inputs["Sheen Weight"].default_value=0.18
    noise=m.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=115
    noise.inputs["Detail"].default_value=2.5
    bump=m.node_tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=0.10
    bump.inputs["Distance"].default_value=0.012
    m.node_tree.links.new(noise.outputs["Fac"],bump.inputs["Height"])
    m.node_tree.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m
CLOTH=cloth_mat()

def bind_to_bone(o,bone):
    if bone not in arm.data.bones:
        raise SystemExit("Missing bone "+bone)
    vg=o.vertex_groups.new(name=bone)
    vg.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
    md=o.modifiers.new("Armature",'ARMATURE'); md.object=arm
    o.parent=arm
    o.matrix_parent_inverse=arm.matrix_world.inverted()

def finish(o,name,bone):
    o.name=name
    o.data.materials.append(CLOTH)
    sol=o.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.006
    bev=o.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.003; bev.segments=2
    bind_to_bone(o,bone)
    return o

# --- Piece 1: IZAR, continuous wrapped cloth from waist to ankles ---
radial=48; rings=15
rx=0.36; ry=0.245
verts=[]; faces=[]
for j in range(rings):
    t=j/(rings-1)
    z=ankle+(waist-ankle)*t
    # slightly tighter at waist, soft flare at lower hem
    rr=1.03 - 0.09*t + 0.025*(1-t)
    for i in range(radial):
        a=2*math.pi*i/radial
        wrinkle=1.0 + 0.025*math.sin(8*a+0.8) + 0.012*math.sin(15*a)
        x=rx*rr*wrinkle*math.cos(a)
        y=ry*rr*(1.0+0.018*math.sin(10*a))*math.sin(a)
        verts.append((x,y,z))
for j in range(rings-1):
    for i in range(radial):
        n=(i+1)%radial
        a=j*radial+i; b=j*radial+n; c=(j+1)*radial+n; d=(j+1)*radial+i
        faces.append((a,b,c,d))
me=bpy.data.meshes.new("IzarMesh"); me.from_pydata(verts,[],faces); me.update()
izar=bpy.data.objects.new("Ihram_Izar",me); bpy.context.collection.objects.link(izar)
finish(izar,"Ihram_Izar","pelvis")

# Visible overlapping flap in front, like a real wrapped izar.
front_y=-ry*1.045
fw=0.44
verts=[
    (-fw/2,front_y-0.008,ankle+h*0.03),(fw/2,front_y-0.008,ankle+h*0.03),
    (fw/2*0.88,front_y-0.012,waist-h*0.01),(-fw/2*0.88,front_y-0.012,waist-h*0.01)
]
me=bpy.data.meshes.new("IzarOverlapMesh"); me.from_pydata(verts,[],[(0,1,2,3)]); me.update()
flap=bpy.data.objects.new("Ihram_Izar_Overlap",me); bpy.context.collection.objects.link(flap)
finish(flap,"Ihram_Izar_Overlap","pelvis")

# --- Piece 2: RIDA ---
# Front diagonal sheet: from lower right torso to covered left shoulder, close to chest.
rows=14; cols=9
verts=[]; faces=[]
for j in range(rows):
    t=j/(rows-1)
    z=(waist+h*0.045)+(shoulder-(waist+h*0.045))*t
    cx=(0.15*(1-t))+(-0.17*t)
    half=(0.24 + 0.055*math.sin(t*math.pi))
    for i in range(cols):
        u=(i/(cols-1)-0.5)*2.0
        x=cx+u*half
        # follow torso curvature instead of a flat board
        y=-0.205 - 0.035*(1-(x/0.40)**2) - 0.007*math.sin(i*1.5+j*0.35)
        verts.append((x,y,z))
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i; b=a+1; c=(j+1)*cols+i+1; d=(j+1)*cols+i
        faces.append((a,b,c,d))
me=bpy.data.meshes.new("RidaFrontMesh"); me.from_pydata(verts,[],faces); me.update()
front=bpy.data.objects.new("Ihram_Rida_Front",me); bpy.context.collection.objects.link(front)
finish(front,"Ihram_Rida_Front","spine_02")

# Back drape: broad cloth down the back, starting on left shoulder, right shoulder still exposed.
rows=15; cols=11
verts=[]; faces=[]
for j in range(rows):
    t=j/(rows-1)
    z=(waist+h*0.02)+(shoulder+h*0.012-(waist+h*0.02))*t
    # upper edge shifts left to leave right shoulder open
    cx=(-0.04*(1-t))+(-0.16*t)
    half=0.30 - 0.055*t
    for i in range(cols):
        u=(i/(cols-1)-0.5)*2.0
        x=cx+u*half
        y=0.205 + 0.028*(1-(x/0.42)**2) + 0.006*math.sin(i*1.35+j*0.42)
        verts.append((x,y,z))
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i; b=a+1; c=(j+1)*cols+i+1; d=(j+1)*cols+i
        faces.append((a,b,c,d))
me=bpy.data.meshes.new("RidaBackMesh"); me.from_pydata(verts,[],faces); me.update()
back=bpy.data.objects.new("Ihram_Rida_Back",me); bpy.context.collection.objects.link(back)
finish(back,"Ihram_Rida_Back","spine_02")

# Curved shoulder bridge over LEFT shoulder only.
bpy.ops.mesh.primitive_uv_sphere_add(segments=36,ring_count=18,location=(-0.24,0.0,shoulder-0.015))
bridge=bpy.context.object
bridge.scale=(0.30,0.29,0.10)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
# Cut is visually approximated by a flattened oval, mostly hidden by front/back drapes.
finish(bridge,"Ihram_Rida_LeftShoulder","spine_02")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V9_IHRAM_DONE",os.path.abspath(out))
