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

# ---------------- upper RIDA: body-surface wrap ----------------
# Build the upper cloth directly from the character torso surface. This guarantees that the rida
# hugs the chest/back and inherits the exact original skin weights, instead of floating as panels.

rida_z0=waist+H*.025
rida_z1=shoulder+H*.035
selected=[]
for poly in body.data.polygons:
    ps=[body_pts[i] for i in poly.vertices]
    ctr=sum(ps,Vector((0,0,0)))/len(ps)
    if ctr.z<rida_z0 or ctr.z>rida_z1:
        continue
    t=(ctr.z-rida_z0)/max(.0001,(rida_z1-rida_z0))
    # coordinate toward the covered LEFT side
    lx=left_sign*ctr.x
    # At waist the wrap reaches across the torso; near shoulder it narrows to the covered side.
    threshold=H*(-.115 + .155*t)
    # Prevent far upper-arm/hand geometry from becoming part of the cloth.
    if lx>threshold and abs(ctr.x)<H*.235 and abs(ctr.y)<H*.17:
        selected.append(poly)

if len(selected)<50:
    raise SystemExit("Too few torso faces selected for rida: "+str(len(selected)))

vmap={}
newverts=[]
orig_for_new=[]
newfaces=[]
offset=H*.0065
for poly in selected:
    face=[]
    for oi in poly.vertices:
        if oi not in vmap:
            ov=body.data.vertices[oi]
            ni=len(newverts)
            vmap[oi]=ni
            # body-local offset along the skin normal creates a thin cotton layer.
            newverts.append(tuple(ov.co + ov.normal*offset))
            orig_for_new.append(oi)
        face.append(vmap[oi])
    newfaces.append(tuple(face))

me=bpy.data.meshes.new("IhramRidaBodyWrapMesh")
me.from_pydata(newverts,[],newfaces); me.update()
rida=bpy.data.objects.new("Ihram_Rida_BodyWrap",me)
bpy.context.collection.objects.link(rida)

# Copy the exact source-body vertex weights one-for-one.
for vg in body.vertex_groups:
    rida.vertex_groups.new(name=vg.name)
for ni,oi in enumerate(orig_for_new):
    ov=body.data.vertices[oi]
    for g in ov.groups:
        src_group=body.vertex_groups[g.group]
        if src_group.name in rida.vertex_groups:
            rida.vertex_groups[src_group.name].add([ni],g.weight,'REPLACE')

world_matrix=body.matrix_world.copy()
rida.parent=arm
rida.matrix_parent_inverse=arm.matrix_world.inverted()
rida.matrix_world=world_matrix
am=rida.modifiers.new("Armature",'ARMATURE'); am.object=arm
add_modifiers(rida)

# A narrow loose end falls from the covered shoulder, like the real towel edge in the references.
spine_name="spine_02" if "spine_02" in arm.data.bones else "spine_01"
clav_name="clavicle_l"
if clav_name not in arm.data.bones:
    raise SystemExit("Missing left clavicle")

def bind_loose(o):
    vg1=o.vertex_groups.new(name=spine_name)
    vg2=o.vertex_groups.new(name=clav_name)
    for idx,v in enumerate(o.data.vertices):
        t=max(0,min(1,(v.co.z-(waist-H*.05))/(shoulder-(waist-H*.05))))
        wc=.18+.52*t
        vg1.add([idx],1-wc,'REPLACE'); vg2.add([idx],wc,'REPLACE')
    md=o.modifiers.new("Armature",'ARMATURE'); md.object=arm
    o.parent=arm; o.matrix_parent_inverse=arm.matrix_world.inverted()

rr=14; cc=6; verts=[]; faces=[]
for j in range(rr):
    t=j/(rr-1)
    z=(shoulder-H*.01)*(1-t)+(waist-H*.09)*t
    _,ry=cross_extents(z,H*.025)
    for i in range(cc):
        u=i/(cc-1)
        # hangs down the covered left side, close to the torso
        x=left_sign*(H*.145-H*.018*t)+(u-.5)*H*.062
        y=-(ry+H*.009)-H*.0015*math.sin(j*.7+i)
        verts.append((x,y,z))
for j in range(rr-1):
    for i in range(cc-1):
        a=j*cc+i; b=a+1; c2=(j+1)*cc+i+1; d=(j+1)*cc+i
        faces.append((a,b,c2,d))
me2=bpy.data.meshes.new("IhramLooseEndMesh"); me2.from_pydata(verts,[],faces); me2.update()
loose=bpy.data.objects.new("Ihram_Rida_LooseEnd",me2); bpy.context.collection.objects.link(loose)
bind_loose(loose); add_modifiers(loose)

# Validate garment distance: reject an absurdly oversized ihram.
garments=[izar,flap,rida,loose]
for g in garments:
    xs=[abs(v.co.x) for v in g.data.vertices]
    if xs and max(xs)>H*.40:
        raise SystemExit("Garment too wide: "+g.name+" "+str(max(xs)))

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    export_animations=True,export_animation_mode='ACTIONS',export_yup=True,
    export_materials='EXPORT',export_apply=False)
print("V11_IHRAM_FITTED",os.path.abspath(out))
