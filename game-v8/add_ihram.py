import bpy, math, os, sys
from mathutils import Vector

# Add a two-piece, armature-skinned ihram to a MakeHuman GLB.
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]
out=argv[1] if len(argv)>1 else src

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature found")

meshes=[o for o in bpy.data.objects if o.type=='MESH']
# Character bounds excluding tiny accessory objects where possible.
pts=[]
for o in meshes:
    for c in o.bound_box:
        pts.append(o.matrix_world @ Vector(c))
zmin=min(p.z for p in pts); zmax=max(p.z for p in pts)
h=zmax-zmin
print("CHAR_BOUNDS",zmin,zmax,h)

# Use human proportions; imported MakeHuman is centered at X/Y ~= 0.
waist=zmin+h*0.53
ankle=zmin+h*0.10
chest=zmin+h*0.72
shoulder=zmin+h*0.84

def cloth_material():
    m=bpy.data.materials.new("IhramFabric")
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(0.965,0.955,0.925,1)
    bs.inputs["Roughness"].default_value=0.92
    bs.inputs["Sheen Weight"].default_value=0.22
    # subtle woven bump
    tex=m.node_tree.nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value=145
    tex.inputs["Detail"].default_value=2.0
    tex.inputs["Roughness"].default_value=.65
    bump=m.node_tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.12
    bump.inputs["Distance"].default_value=.018
    m.node_tree.links.new(tex.outputs["Fac"],bump.inputs["Height"])
    m.node_tree.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m
CLOTH=cloth_material()

def add_armature_weights(obj, weight_func):
    mod=obj.modifiers.new("Armature",'ARMATURE'); mod.object=arm
    groups={}
    for bn in ["pelvis","spine_01","spine_02","clavicle_l","upperarm_l","thigh_l","thigh_r"]:
        if bn in arm.data.bones:
            groups[bn]=obj.vertex_groups.new(name=bn)
    for i,v in enumerate(obj.data.vertices):
        weights=weight_func(v.co)
        total=sum(w for _,w in weights if w>0)
        if total<=0: continue
        for bn,w in weights:
            if bn in groups and w>0:
                groups[bn].add([i],w/total,'REPLACE')

# IZAR — elliptical wrapped cloth with many vertical subdivisions and natural folds.
radial=40; rings=10
verts=[]; faces=[]
rx=0.34; ry=0.235
for j in range(rings):
    t=j/(rings-1)
    z=ankle+(waist-ankle)*t
    # Slightly tighter at waist; cloth hangs straighter below.
    rr=1.02-0.08*t
    for i in range(radial):
        a=2*math.pi*i/radial
        fold=1.0 + 0.035*math.sin(a*7.0+0.6) + 0.018*math.sin(a*13.0)
        x=rx*rr*fold*math.cos(a)
        y=ry*rr*(1.0+0.03*math.sin(a*9.0))*math.sin(a)
        # slight overlapping front flap toward -Y
        if -0.75 < a-math.pi/2 < 0.75:
            y-=0.008
        verts.append((x,y,z))
for j in range(rings-1):
    for i in range(radial):
        n=(i+1)%radial
        a=j*radial+i; b=j*radial+n; c=(j+1)*radial+n; d=(j+1)*radial+i
        faces.append((a,b,c,d))
mesh=bpy.data.meshes.new("IhramIzarMesh"); mesh.from_pydata(verts,[],faces); mesh.update()
izar=bpy.data.objects.new("Ihram_Izar",mesh); bpy.context.collection.objects.link(izar)
izar.data.materials.append(CLOTH)
sol=izar.modifiers.new("ClothThickness",'SOLIDIFY'); sol.thickness=0.008
bev=izar.modifiers.new("SoftHem",'BEVEL'); bev.width=0.004; bev.segments=2

def izar_w(co):
    t=max(0,min(1,(co.z-ankle)/(waist-ankle)))
    # upper half rides pelvis. Bottom receives mild thigh influence to avoid a rigid barrel.
    if t>0.62: return [("pelvis",1.0)]
    left=max(0,min(1,(-co.x/rx+1)/2))
    right=1-left
    return [("pelvis",0.62),("thigh_l",0.38*left),("thigh_r",0.38*right)]
add_armature_weights(izar,izar_w)

# RIDA — a close-fitting diagonal drape from the covered LEFT shoulder to the opposite waist.
# Use a narrow, subdivided strip instead of a large rectangle so it reads as wrapped fabric.
rows=14; cols=7

def make_drape(name, front=True):
    verts=[]; faces=[]
    # Centerline: lower-right torso -> upper-left shoulder.
    x0, z0 = 0.17, waist + h*0.075
    x1, z1 = -0.235, shoulder + h*0.008
    dx=x1-x0; dz=z1-z0
    plen=max(1e-6,math.sqrt(dx*dx+dz*dz))
    # Perpendicular in the X/Z plane gives the cloth width around the diagonal centerline.
    px=-dz/plen; pz=dx/plen
    half_width=h*0.095
    ybase=-h*0.128 if front else h*0.114
    for j in range(rows):
        t=j/(rows-1)
        cx=x0+(x1-x0)*t
        cz=z0+(z1-z0)*t
        # Slight taper near shoulder and waist; widest over the chest/back.
        width=half_width*(0.74 + 0.26*math.sin(t*math.pi))
        for i in range(cols):
            u=(i/(cols-1)-0.5)*2.0
            # Fine woven/fold relief, kept close to body.
            fold=0.006*math.sin(i*math.pi*1.6 + j*0.55)
            x=cx + px*width*u
            z=cz + pz*width*u
            y=ybase + ((-fold) if front else fold)
            verts.append((x,y,z))
    for j in range(rows-1):
        for i in range(cols-1):
            a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
            faces.append((a,b,cc,d))
    me=bpy.data.meshes.new(name+"Mesh"); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    o.data.materials.append(CLOTH)
    sol=o.modifiers.new("ClothThickness",'SOLIDIFY'); sol.thickness=0.007
    bev=o.modifiers.new("SoftEdge",'BEVEL'); bev.width=0.0035; bev.segments=2
    return o

rida=make_drape("Ihram_Rida_Front",True)
back=make_drape("Ihram_Rida_Back",False)

def rida_w(co):
    t=max(0,min(1,(co.z-(waist+h*0.03))/(shoulder-(waist+h*0.03))))
    return [("spine_01",0.48*(1-t)),("spine_02",0.48+0.22*t),("clavicle_l",0.24*t),("upperarm_l",0.06*t)]
add_armature_weights(rida,rida_w)
add_armature_weights(back,rida_w)

# A compact shoulder bridge wraps over the left shoulder and connects front/back.
bpy.ops.mesh.primitive_cube_add(location=(-h*0.135,-0.002,shoulder-h*0.018),scale=(h*0.095,h*0.105,h*0.022))
bridge=bpy.context.object; bridge.name="Ihram_Rida_Shoulder"
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
md=bridge.modifiers.new("Rounded",'BEVEL'); md.width=h*0.018; md.segments=5
bpy.context.view_layer.objects.active=bridge; bpy.ops.object.modifier_apply(modifier=md.name)
bridge.data.materials.append(CLOTH)
def bridge_w(co): return [("clavicle_l",0.74),("spine_02",0.26)]
add_armature_weights(bridge,bridge_w)

# Put cloth under the armature root and export all animations.
for o in [izar,rida,back,bridge]:
    o.parent=arm
    o.matrix_parent_inverse=arm.matrix_world.inverted()

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',use_selection=True,
                          export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
                          export_materials='EXPORT',export_apply=False)
print("IHRAM_DECORATED",os.path.abspath(out))
