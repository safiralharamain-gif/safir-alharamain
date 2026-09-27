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

# --- Piece 1: IZAR ---
# Close to the hips/legs like a real wrapped towel; the old radius was too large and looked like a barrel.
radial=56; rings=18
rx_top=0.285; ry_top=0.185
rx_bottom=0.300; ry_bottom=0.195
verts=[]; faces=[]
for j in range(rings):
    t=j/(rings-1)
    z=ankle+(waist-ankle)*t
    rx=rx_bottom*(1-t)+rx_top*t
    ry=ry_bottom*(1-t)+ry_top*t
    for i in range(radial):
        a=2*math.pi*i/radial
        fold=1.0 + 0.018*math.sin(9*a+0.4) + 0.008*math.sin(17*a)
        x=rx*fold*math.cos(a)
        y=ry*(1.0+0.012*math.sin(11*a))*math.sin(a)
        verts.append((x,y,z))
for j in range(rings-1):
    for i in range(radial):
        n=(i+1)%radial
        a=j*radial+i; b=j*radial+n; cc=(j+1)*radial+n; d=(j+1)*radial+i
        faces.append((a,b,cc,d))
me=bpy.data.meshes.new("IzarMesh"); me.from_pydata(verts,[],faces); me.update()
izar=bpy.data.objects.new("Ihram_Izar",me); bpy.context.collection.objects.link(izar)
izar.name="Ihram_Izar"; izar.data.materials.append(CLOTH)
sol=izar.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.006
bev=izar.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.003; bev.segments=2

# Skin the upper part to pelvis and the lower cloth softly to the thighs so walking does not cut through it.
md=izar.modifiers.new("Armature",'ARMATURE'); md.object=arm
izar.parent=arm; izar.matrix_parent_inverse=arm.matrix_world.inverted()
groups={}
for bn in ("pelvis","thigh_l","thigh_r"):
    if bn in arm.data.bones:
        groups[bn]=izar.vertex_groups.new(name=bn)
for idx,v in enumerate(izar.data.vertices):
    t=max(0.0,min(1.0,(v.co.z-ankle)/(waist-ankle)))
    if t>0.52 or "thigh_l" not in groups or "thigh_r" not in groups:
        if "pelvis" in groups: groups["pelvis"].add([idx],1.0,'REPLACE')
    else:
        pelvis_w=0.48+0.28*t
        left_w=(1.0-pelvis_w)*(0.62 if v.co.x<0 else 0.38)
        right_w=(1.0-pelvis_w)-left_w
        if "pelvis" in groups: groups["pelvis"].add([idx],pelvis_w,'REPLACE')
        groups["thigh_l"].add([idx],left_w,'REPLACE')
        groups["thigh_r"].add([idx],right_w,'REPLACE')

# Front overlap: a narrow second layer, not a rigid plate.
front_y=-ry_top*1.025
fw=0.22
verts=[
    (-fw,front_y-0.006,ankle+h*0.035),(fw,front_y-0.006,ankle+h*0.035),
    (fw*0.86,front_y-0.010,waist-h*0.015),(-fw*0.86,front_y-0.010,waist-h*0.015)
]
me=bpy.data.meshes.new("IzarOverlapMesh"); me.from_pydata(verts,[],[(0,1,2,3)]); me.update()
flap=bpy.data.objects.new("Ihram_Izar_Overlap",me); bpy.context.collection.objects.link(flap)
finish(flap,"Ihram_Izar_Overlap","pelvis")

# --- Piece 2: RIDA ---
# One shoulder is covered and the opposite shoulder remains exposed, matching the user's photo.
# Front/back are curved diagonal drapes that hug the torso rather than a cylindrical shell.
rows=18; cols=9
def make_rida_surface(name,front=True):
    verts=[]; faces=[]
    # diagonal centreline: covered LEFT shoulder -> opposite/right waist
    sx=-0.22; sz=shoulder+h*0.012
    ex= 0.17; ez=waist+h*0.045
    dx=ex-sx; dz=ez-sz
    plen=max(1e-6,math.sqrt(dx*dx+dz*dz))
    px=-dz/plen; pz=dx/plen
    for j in range(rows):
        t=j/(rows-1)
        cx=sx+(ex-sx)*t
        cz=sz+(ez-sz)*t
        width=(0.19 + 0.035*math.sin(t*math.pi))
        for i in range(cols):
            u=(i/(cols-1)-0.5)*2.0
            x=cx+px*width*u
            z=cz+pz*width*u
            # gently curve around the chest/back, with woven folds
            torso_y=0.188 + 0.025*(1.0-min(1.0,abs(x)/0.32))
            fold=0.006*math.sin(i*1.7+j*0.45)
            y=(-torso_y-fold) if front else (torso_y+fold)
            verts.append((x,y,z))
    for j in range(rows-1):
        for i in range(cols-1):
            a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
            faces.append((a,b,cc,d))
    me=bpy.data.meshes.new(name+"Mesh"); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    o.data.materials.append(CLOTH)
    sol=o.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.007
    bev=o.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.003; bev.segments=2
    bind_to_bone(o,"spine_02")
    return o

rida_front=make_rida_surface("Ihram_Rida_Front",True)
rida_back=make_rida_surface("Ihram_Rida_Back",False)

# Small rounded bridge over the LEFT shoulder connects front and back visually.
bpy.ops.mesh.primitive_cube_add(location=(-0.235,0.0,shoulder+h*0.005),scale=(0.135,0.195,0.030))
bridge=bpy.context.object
bridge.name="Ihram_Rida_Shoulder"
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
md2=bridge.modifiers.new("Rounded",'BEVEL'); md2.width=0.034; md2.segments=6
bpy.context.view_layer.objects.active=bridge; bpy.ops.object.modifier_apply(modifier=md2.name)
bridge.data.materials.append(CLOTH)
bind_to_bone(bridge,"spine_02")

# Hanging end on the covered side to give the loose-towel look seen in real ihram.
hang_x=-0.23; hang_y=-0.205
verts=[
    (hang_x-0.10,hang_y,shoulder-h*0.02),
    (hang_x+0.08,hang_y,shoulder-h*0.05),
    (hang_x+0.06,hang_y-0.006,waist-h*0.12),
    (hang_x-0.09,hang_y+0.004,waist-h*0.09)
]
me=bpy.data.meshes.new("RidaLooseEndMesh"); me.from_pydata(verts,[],[(0,1,2,3)]); me.update()
loose=bpy.data.objects.new("Ihram_Rida_LooseEnd",me); bpy.context.collection.objects.link(loose)
finish(loose,"Ihram_Rida_LooseEnd","spine_02")

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V9_IHRAM_DONE",os.path.abspath(out))
