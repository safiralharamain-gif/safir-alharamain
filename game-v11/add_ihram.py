import bpy, os, sys, math
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
src=argv[0]; out=argv[1]

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(src))

arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if arm is None:
    raise SystemExit("No armature")

meshes=[o for o in bpy.data.objects if o.type=='MESH']
if not meshes:
    raise SystemExit("No meshes")

# Main body is the highest vertex-count mesh. Hair/beard/accessories are much smaller.
body=max(meshes,key=lambda o:len(o.data.vertices))
print("V11 BODY",body.name,len(body.data.vertices))

inv_arm=arm.matrix_world.inverted()
body_pts=[inv_arm @ (body.matrix_world @ v.co) for v in body.data.vertices]
zmin=min(p.z for p in body_pts); zmax=max(p.z for p in body_pts); H=zmax-zmin
if H < 1.0:
    raise SystemExit("Unexpected body height "+str(H))
print("V11 BODY BOUNDS",zmin,zmax,H)

bones=arm.data.bones
uaL="upperarm_l"; uaR="upperarm_r"
left_sign=1.0
if uaL in bones and uaR in bones:
    left_sign=1.0 if bones[uaL].head_local.x>bones[uaR].head_local.x else -1.0

# Robust percentile utility.
def perc(vals,p=.94):
    if not vals:return 0.0
    s=sorted(vals)
    return s[min(len(s)-1,max(0,int((len(s)-1)*p)))]

def cross_extents(z,band=None):
    if band is None: band=H*.018
    pts=[p for p in body_pts if abs(p.z-z)<=band and abs(p.x)<H*.26 and abs(p.y)<H*.18]
    if len(pts)<20:
        pts=[p for p in body_pts if abs(p.z-z)<=band*2 and abs(p.x)<H*.30 and abs(p.y)<H*.22]
    rx=perc([abs(p.x) for p in pts],.95)
    ry=perc([abs(p.y) for p in pts],.95)
    return max(rx,H*.055),max(ry,H*.045)

ankle=zmin+H*.075
waist=zmin+H*.535
hip=zmin+H*.48
chest=zmin+H*.70
shoulder=zmin+H*.835

def cloth_material():
    m=bpy.data.materials.new("IhramCotton")
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(0.985,0.98,0.96,1)
    bs.inputs["Roughness"].default_value=.92
    if "Sheen Weight" in bs.inputs: bs.inputs["Sheen Weight"].default_value=.22
    noise=m.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=165
    noise.inputs["Detail"].default_value=2.0
    noise.inputs["Roughness"].default_value=.62
    bump=m.node_tree.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value=.09
    bump.inputs["Distance"].default_value=.008
    m.node_tree.links.new(noise.outputs["Fac"],bump.inputs["Height"])
    m.node_tree.links.new(bump.outputs["Normal"],bs.inputs["Normal"])
    return m
CLOTH=cloth_material()

def add_modifiers(o):
    o.data.materials.append(CLOTH)
    sol=o.modifiers.new("FabricThickness",'SOLIDIFY'); sol.thickness=H*.0032
    bev=o.modifiers.new("SoftClothEdge",'BEVEL'); bev.width=H*.0018; bev.segments=2
    sm=o.modifiers.new("ClothSmooth",'SMOOTH'); sm.factor=.28; sm.iterations=2

def transfer_weights(o):
    # Copy body skin weights so cloth follows the exact same skeleton, not hand-guessed bones.
    for vg in body.vertex_groups:
        if vg.name not in o.vertex_groups:
            o.vertex_groups.new(name=vg.name)
    dt=o.modifiers.new("TransferBodyWeights",'DATA_TRANSFER')
    dt.object=body
    dt.use_vert_data=True
    dt.data_types_verts={'VGROUP_WEIGHTS'}
    dt.vert_mapping='POLYINTERP_NEAREST'
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    try:
        bpy.ops.object.modifier_apply(modifier=dt.name)
    except Exception as e:
        print("weight transfer apply warning",e)
    am=o.modifiers.new("Armature",'ARMATURE'); am.object=arm
    o.parent=arm
    o.matrix_parent_inverse=arm.matrix_world.inverted()
    o.select_set(False)

# ---------------- lower IZAR: fitted from actual body cross-sections ----------------
radial=64; rings=24
verts=[]; faces=[]
for j in range(rings):
    t=j/(rings-1)
    z=ankle+(waist-ankle)*t
    rx,ry=cross_extents(z)
    # Wrapped towel stays just off the skin; wider only by ~1–2 cm.
    rx += H*(.009 + .003*(1-t))
    ry += H*(.009 + .002*(1-t))
    # Keep hem straighter so it reads as cloth, not trousers.
    if t<.18:
        rx*=1.025; ry*=1.02
    for i in range(radial):
        a=2*math.pi*i/radial
        fold=1.0 + .015*math.sin(7*a+.4) + .007*math.sin(13*a+1.1)
        x=rx*fold*math.cos(a)
        y=ry*(1+.010*math.sin(9*a))*math.sin(a)
        z2=z + (H*.003*math.sin(a*2.0) if j==0 else 0)
        verts.append((x,y,z2))
for j in range(rings-1):
    for i in range(radial):
        n=(i+1)%radial
        a=j*radial+i; b=j*radial+n; c=(j+1)*radial+n; d=(j+1)*radial+i
        faces.append((a,b,c,d))
me=bpy.data.meshes.new("IhramIzarMesh"); me.from_pydata(verts,[],faces); me.update()
izar=bpy.data.objects.new("Ihram_Izar",me); bpy.context.collection.objects.link(izar)
transfer_weights(izar); add_modifiers(izar)

# Overlap flap very close to the front of the izar.
rxw,ryw=cross_extents(waist-H*.03)
front_y=-(ryw+H*.012)
fw=rxw*.72
verts=[(-fw,front_y,ankle+H*.035),(fw,front_y,ankle+H*.035),
       (fw*.86,front_y-H*.004,waist-H*.018),(-fw*.86,front_y-H*.004,waist-H*.018)]
me=bpy.data.meshes.new("IhramIzarOverlapMesh"); me.from_pydata(verts,[],[(0,1,2,3)]); me.update()
flap=bpy.data.objects.new("Ihram_Izar_Overlap",me); bpy.context.collection.objects.link(flap)
transfer_weights(flap); add_modifiers(flap)

# ---------------- upper RIDA: stable diagonal wrap ----------------
# V11.1: the rida is NOT weight-transferred from the whole torso. That caused the cloth to crumple.
# It is a stable unsewn wrap controlled only by the chest + covered left shoulder.
spine_name="spine_02" if "spine_02" in arm.data.bones else "spine_01"
clav_name="clavicle_l"
if clav_name not in arm.data.bones:
    raise SystemExit("Missing left clavicle for rida")

def bind_rida(o):
    vg_sp=o.vertex_groups.new(name=spine_name)
    vg_cl=o.vertex_groups.new(name=clav_name)
    for idx,v in enumerate(o.data.vertices):
        # upper vertices follow the shoulder more; lower ones follow the torso.
        t=max(0.0,min(1.0,(v.co.z-(waist-H*.02))/(shoulder-(waist-H*.02))))
        wc=.12+.56*t
        ws=1.0-wc
        vg_sp.add([idx],ws,'REPLACE')
        vg_cl.add([idx],wc,'REPLACE')
    am=o.modifiers.new("Armature",'ARMATURE'); am.object=arm
    o.parent=arm
    o.matrix_parent_inverse=arm.matrix_world.inverted()

rows=18; cols=12

def make_stable_drape(name,front=True):
    verts=[]; faces=[]
    for j in range(rows):
        t=j/(rows-1)  # 0 shoulder, 1 lower torso
        z=shoulder*(1-t)+(waist+H*.035)*t
        _,ry=cross_extents(z,H*.025)
        # Covered-left-shoulder diagonal: narrow at shoulder, broader toward waist.
        cx=left_sign*(H*.105*(1-t) - H*.025*t)
        half=H*(.066 + .038*t)
        for i in range(cols):
            u=i/(cols-1)
            x=cx+(u-.5)*2*half
            surf=ry+H*.007
            y=(-surf if front else surf)
            # very shallow folds only
            y += (-1 if front else 1)*H*.0018*math.sin(i*1.45+j*.42)
            # outer lower edge drops slightly, like a towel fold
            z2=z-H*.012*t*u
            verts.append((x,y,z2))
    for j in range(rows-1):
        for i in range(cols-1):
            a=j*cols+i; b=a+1; cc=(j+1)*cols+i+1; d=(j+1)*cols+i
            faces.append((a,b,cc,d))
    me=bpy.data.meshes.new(name+"Mesh"); me.from_pydata(verts,[],faces); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    bind_rida(o); add_modifiers(o)
    return o

front=make_stable_drape("Ihram_Rida_Front",True)
back=make_stable_drape("Ihram_Rida_Back",False)

# Compact bridge over the covered LEFT shoulder.
_,shoulder_depth=cross_extents(shoulder,H*.025)
rows2=8; cols2=8
verts=[]; faces=[]
xcenter=left_sign*H*.105
for j in range(rows2):
    v=j/(rows2-1)
    y=-(shoulder_depth+H*.007) + 2*(shoulder_depth+H*.007)*v
    z=shoulder+H*.014*math.sin(v*math.pi)
    for i in range(cols2):
        u=i/(cols2-1)
        x=xcenter+(u-.5)*H*.105
        verts.append((x,y,z-H*.003*abs(u-.5)))
for j in range(rows2-1):
    for i in range(cols2-1):
        a=j*cols2+i; b=a+1; cc=(j+1)*cols2+i+1; d=(j+1)*cols2+i
        faces.append((a,b,cc,d))
me=bpy.data.meshes.new("IhramShoulderBridgeMesh"); me.from_pydata(verts,[],faces); me.update()
bridge=bpy.data.objects.new("Ihram_Rida_Shoulder",me); bpy.context.collection.objects.link(bridge)
bind_rida(bridge); add_modifiers(bridge)

# Loose hanging end on the covered side, kept narrow and chest-bound.
rr=12; cc=5; verts=[]; faces=[]
for j in range(rr):
    t=j/(rr-1)
    z=(shoulder-H*.02)*(1-t)+(waist-H*.075)*t
    _,ry=cross_extents(z,H*.025)
    for i in range(cc):
        u=i/(cc-1)
        x=left_sign*(H*.155-H*.018*t)+(u-.5)*H*.055
        y=-(ry+H*.008)-H*.0015*math.sin(j+i)
        verts.append((x,y,z))
for j in range(rr-1):
    for i in range(cc-1):
        a=j*cc+i; b=a+1; cc2=(j+1)*cc+i+1; d=(j+1)*cc+i
        faces.append((a,b,cc2,d))
me=bpy.data.meshes.new("IhramLooseEdgeMesh"); me.from_pydata(verts,[],faces); me.update()
loose=bpy.data.objects.new("Ihram_Rida_LooseEdge",me); bpy.context.collection.objects.link(loose)
bind_rida(loose); add_modifiers(loose)

# Validate garment distance: reject an absurdly oversized ihram.
garments=[izar,flap,front,back,bridge,loose]
for g in garments:
    xs=[abs(v.co.x) for v in g.data.vertices]
    if xs and max(xs)>H*.40:
        raise SystemExit("Garment too wide: "+g.name+" "+str(max(xs)))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V11_IHRAM_FITTED",os.path.abspath(out))
