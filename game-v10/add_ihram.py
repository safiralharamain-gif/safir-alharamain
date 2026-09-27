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
    bs.inputs["Base Color"].default_value=(0.92,0.915,0.89,1)
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
rx_top=0.265; ry_top=0.172
rx_bottom=0.248; ry_bottom=0.162
verts=[]; faces=[]
for j in range(rings):
    t=j/(rings-1)
    z_base=ankle+(waist-ankle)*t
    rx=rx_bottom*(1-t)+rx_top*t
    ry=ry_bottom*(1-t)+ry_top*t
    for i in range(radial):
        a=2*math.pi*i/radial
        z=z_base + (0.010*h*math.sin(a*2.0) if j==0 else 0.0)
        fold=1.0 + 0.040*math.sin(7*a+0.4) + 0.018*math.sin(13*a) + 0.010*math.sin(19*a+1.2)
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
for poly in izar.data.polygons: poly.use_smooth=True
sub=izar.modifiers.new("FabricSubdivision",'SUBSURF'); sub.levels=1; sub.render_levels=1
sol=izar.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.0055
bev=izar.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.0025; bev.segments=2

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
front_y=-ry_top*1.055
fw=0.185
verts=[
    (-fw,front_y-0.006,ankle+h*0.035),(fw,front_y-0.006,ankle+h*0.035),
    (fw*0.86,front_y-0.010,waist-h*0.015),(-fw*0.86,front_y-0.010,waist-h*0.015)
]
me=bpy.data.meshes.new("IzarOverlapMesh"); me.from_pydata(verts,[],[(0,1,2,3)]); me.update()
flap=bpy.data.objects.new("Ihram_Izar_Overlap",me); bpy.context.collection.objects.link(flap)
finish(flap,"Ihram_Izar_Overlap","pelvis")

# --- Piece 2: RIDA ---
# Curved drape based on the user's reference: LEFT shoulder covered, RIGHT shoulder exposed.
# Back panel widens toward the waist and follows the torso curvature instead of hanging like a board.

def add_weighted_rida(o):
    groups={}
    for bn in ("spine_02","clavicle_l","upperarm_l"):
        if bn in arm.data.bones:
            groups[bn]=o.vertex_groups.new(name=bn)
    md=o.modifiers.new("Armature",'ARMATURE'); md.object=arm
    o.parent=arm; o.matrix_parent_inverse=arm.matrix_world.inverted()
    zlo=waist-h*0.02; zhi=shoulder+h*0.03
    for idx,v in enumerate(o.data.vertices):
        t=max(0.0,min(1.0,(v.co.z-zlo)/(zhi-zlo)))
        w_cl=0.08+0.70*t
        w_arm=0.05*t
        w_sp=max(0.0,1.0-w_cl-w_arm)
        if "spine_02" in groups: groups["spine_02"].add([idx],w_sp,'REPLACE')
        if "clavicle_l" in groups: groups["clavicle_l"].add([idx],w_cl,'REPLACE')
        if "upperarm_l" in groups: groups["upperarm_l"].add([idx],w_arm,'REPLACE')

def make_curved_drape(name,front):
    rows=18; cols=11
    verts=[]; faces=[]
    for j in range(rows):
        t=j/(rows-1)  # 0 top shoulder, 1 lower waist
        z=shoulder*(1-t)+(waist+h*0.025)*t
        # Narrow at the covered shoulder, broader toward the waist/back.
        half=0.12 + 0.165*t
        cx=-0.205 + 0.15*t
        for i in range(cols):
            u=i/(cols-1)
            x=cx+(u-0.5)*2.0*half
            xn=max(-1.0,min(1.0,x/0.36))
            # Torso curvature; front/back are close to the skin with soft cloth folds.
            curve=0.158 + 0.030*(1.0-xn*xn)
            fold=0.010*math.sin(i*1.55+j*0.48) + 0.004*math.sin(i*2.8-j*0.35)
            y=(-curve-fold) if front else (curve+fold)
            # Lower right edge hangs a little more, creating the diagonal towel edge.
            z2=z - 0.035*u*t
            verts.append((x,y,z2))
    for j in range(rows-1):
        for i in range(cols-1):
            a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
            faces.append((a,b,cc,d))
    me=bpy.data.meshes.new(name+"Mesh"); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    o.data.materials.append(CLOTH)
    for poly in o.data.polygons: poly.use_smooth=True
    sub=o.modifiers.new("FabricSubdivision",'SUBSURF'); sub.levels=1; sub.render_levels=1
    sol=o.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.0055
    bev=o.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.0025; bev.segments=2
    add_weighted_rida(o)
    return o

rida_back=make_curved_drape("Ihram_Rida_Back",False)
rida_front=make_curved_drape("Ihram_Rida_Front",True)

# Curved shoulder bridge from front to back over the LEFT shoulder.
rows=7; cols=9
verts=[]; faces=[]
for j in range(rows):
    vv=j/(rows-1)
    y=-0.175 + 0.350*vv
    # arc over shoulder
    z=shoulder + 0.050*math.sin(vv*math.pi)
    for i in range(cols):
        u=i/(cols-1)
        x=-0.205 + (u-0.5)*0.24
        z2=z - 0.012*abs(u-0.5)
        verts.append((x,y,z2))
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
        faces.append((a,b,cc,d))
me=bpy.data.meshes.new("RidaShoulderMesh"); me.from_pydata(verts,[],faces); me.update()
bridge=bpy.data.objects.new("Ihram_Rida_Shoulder",me); bpy.context.collection.objects.link(bridge)
bridge.data.materials.append(CLOTH)
sol=bridge.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.0065
bev=bridge.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.0032; bev.segments=2
add_weighted_rida(bridge)

# Loose hanging towel edge down the covered left side.
rows=10; cols=5
verts=[]; faces=[]
for j in range(rows):
    t=j/(rows-1)
    z=(shoulder-h*0.035)*(1-t)+(waist-h*0.13)*t
    cx=-0.285+0.055*t
    for i in range(cols):
        u=i/(cols-1)
        x=cx+(u-0.5)*0.13
        y=-0.178-0.004*math.sin(j*0.8+i)
        verts.append((x,y,z))
for j in range(rows-1):
    for i in range(cols-1):
        a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
        faces.append((a,b,cc,d))
me=bpy.data.meshes.new("RidaLooseEndMesh"); me.from_pydata(verts,[],faces); me.update()
loose=bpy.data.objects.new("Ihram_Rida_LooseEnd",me); bpy.context.collection.objects.link(loose)
loose.data.materials.append(CLOTH)
sol=loose.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=0.006
bev=loose.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=0.003; bev.segments=2
add_weighted_rida(loose)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V9_IHRAM_DONE",os.path.abspath(out))
