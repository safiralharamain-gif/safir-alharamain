import bpy, math, os, sys
from mathutils import Vector

argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=argv[0] if argv else "miqat_abyar_ali.glb"

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def mat(name,c,metal=0.0,rough=.6,em=None):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*c,1)
    bs.inputs["Metallic"].default_value=metal
    bs.inputs["Roughness"].default_value=rough
    if em:
        bs.inputs["Emission Color"].default_value=(*em,1); bs.inputs["Emission Strength"].default_value=1.8
    return m

CREAM=mat("MiqatCream",(0.86,0.82,0.70),0.02,.82)
LIGHT=mat("MiqatLightCream",(0.95,0.92,0.82),0.01,.86)
STONE=mat("CourtyardStone",(0.66,0.61,0.50),0.02,.88)
DARKSTONE=mat("BaseStone",(0.34,0.27,0.21),0.02,.82)
GREEN=mat("GardenGreen",(0.08,0.22,0.09),0.0,.95)
TRUNK=mat("PalmTrunk",(0.30,0.18,0.10),0.0,.92)
LEAF=mat("PalmLeaf",(0.06,0.20,0.09),0.0,.92)
WATER=mat("FountainTile",(0.12,0.36,0.48),0.08,.28)
BLACK=mat("LampBlack",(0.035,0.038,0.042),0.55,.30)
LAMP=mat("WarmLamp",(0.9,0.66,0.24),0.08,.18,(1.0,.55,.16))

def box(name,loc,size,ma,bev=.04):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bev>0:
        md=o.modifiers.new("Soft",'BEVEL'); md.width=bev; md.segments=3
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=md.name)
    o.data.materials.append(ma); return o

def cyl(name,loc,r,d,ma,verts=40):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=d,location=loc)
    o=bpy.context.object; o.name=name; o.data.materials.append(ma); return o

def dome(name,loc,r,ma):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=loc,scale=(r,r,r*.72))
    o=bpy.context.object; o.name=name; o.data.materials.append(ma)
    # hide lower half inside tower/roof by placement
    return o

def arch_curve(name,center,width,height,depth,ma,front_y):
    cu=bpy.data.curves.new(name+"Curve",'CURVE')
    cu.dimensions='3D'; cu.bevel_depth=depth; cu.bevel_resolution=3
    sp=cu.splines.new('POLY')
    steps=24; sp.points.add(steps)
    # vertical sides + semicircle-like upper arch
    pts=[]
    xL=center[0]-width/2; xR=center[0]+width/2
    z0=center[2]
    side_h=height*.48
    pts.append((xL,front_y,z0,1)); pts.append((xL,front_y,z0+side_h,1))
    for i in range(steps-3):
        t=i/(steps-4)
        a=math.pi - math.pi*t
        x=center[0] + (width/2)*math.cos(a)
        z=z0+side_h + (height-side_h)*math.sin(a)
        pts.append((x,front_y,z,1))
    pts.append((xR,front_y,z0+side_h,1)); pts.append((xR,front_y,z0,1))
    for p,v in zip(sp.points,pts): p.co=v
    o=bpy.data.objects.new(name,cu); bpy.context.collection.objects.link(o); o.data.materials.append(ma)
    return o

def palm(name,x,y,h=5.5):
    # textured-looking segmented trunk
    segs=8
    for i in range(segs):
        z=.35 + i*(h*.72/segs)
        r=.25*(1.0-i*.035)
        o=cyl(f"{name}_trunk_{i}",(x,y,z),r,h*.72/segs+0.05,TRUNK,28)
        o.rotation_euler.z=(i%2)*.12
    crown_z=h*.78
    # leaf fronds as elongated flattened cubes, angled around the crown
    for i in range(12):
        a=2*math.pi*i/12
        length=2.2 + .35*math.sin(i*1.7)
        cx=x+math.cos(a)*length*.42; cy=y+math.sin(a)*length*.42
        leaf=box(f"{name}_leaf_{i}",(cx,cy,crown_z+.16*math.sin(a*2)),
                 (length,.16,.055),LEAF,.025)
        leaf.rotation_euler.z=a
        leaf.rotation_euler.y=.10+.11*math.sin(a*2)
    # crown
    cyl(name+"_crown",(x,y,crown_z-.1),.34,.52,TRUNK,32)

def lamp_post(name,x,y):
    cyl(name+"_pole",(x,y,1.65),.055,3.3,BLACK,20)
    box(name+"_head",(x,y,3.25),(.34,.34,.38),LAMP,.07)

# Ground zones.
box("Courtyard",(0,0,-.08),(48,48,.16),STONE,.0)
# darker bus road at north edge (+Y)
road=mat("Road",(0.13,0.14,0.15),0.0,.96)
box("BusRoad",(0,20.5,-.02),(48,9,.12),road,.0)

# Main mosque wall at far side of courtyard (+Y), matching cream fortified facade.
box("MainFacade",(0,12.7,3.2),(36,.8,6.4),CREAM,.08)
box("FacadeBase",(0,12.24,.62),(36,.92,1.24),DARKSTONE,.04)
# crenellation
for x in [i*1.2-17.4 for i in range(30)]:
    box("Crenel",(x,12.7,6.65),(.55,.86,.55),LIGHT,.02)

# Monumental central gate with flanking piers and arch.
box("GatePierL",(-3.2,12.05,3.25),(2.4,1.45,6.5),LIGHT,.10)
box("GatePierR",(3.2,12.05,3.25),(2.4,1.45,6.5),LIGHT,.10)
box("GateTop",(0,12.05,5.85),(4.3,1.45,1.35),LIGHT,.10)
arch_curve("GateArch",(0,0,0.25),5.25,5.2,.20,DARKSTONE,11.28)

# Two corner towers inspired by domed towers in the reference.
for x in (-7.4,7.4):
    box(f"Tower_{x}",(x,12.0,5.2),(2.45,2.2,6.6),LIGHT,.10)
    # open belfry slots
    for sx in (-.52,.52):
        box(f"TowerSlot_{x}_{sx}",(x+sx,10.86,6.55),(.34,.08,1.35),DARKSTONE,.03)
    dome(f"TowerDome_{x}",(x,12.0,8.65),1.23,LIGHT)
    cyl(f"TowerFinial_{x}",(x,12.0,9.72),.055,.75,BLACK,18)

# Side arcades: long colonnades along both sides.
for side in (-1,1):
    x=side*14.8
    box(f"ArcadeRoof_{side}",(x,0,4.25),(3.2,24,1.0),CREAM,.08)
    for j,y in enumerate([-10,-7.5,-5,-2.5,0,2.5,5,7.5,10]):
        # columns
        cyl(f"Column_{side}_{j}",(x-side*1.05,y,1.9),.29,3.8,LIGHT,28)
        cyl(f"ColumnInner_{side}_{j}",(x+side*1.05,y,1.9),.29,3.8,LIGHT,28)
        # arch trim facing courtyard
        arch_curve(f"ArcadeArch_{side}_{j}",(x-side*.02,0,.15),2.0,3.2,.095,DARKSTONE,y)
    box(f"ArcadeBack_{side}",(x+side*1.48,0,2.2),(.45,24,4.4),CREAM,.04)

# Garden courts with palms / low hedges.
for gx in (-8.4,8.4):
    for gy in (-7.2,-1.6,4.0):
        box(f"Garden_{gx}_{gy}",(gx,gy,.12),(4.8,3.5,.24),GREEN,.25)
        box(f"GardenBorder_{gx}_{gy}",(gx,gy,.20),(5.1,3.8,.18),LIGHT,.08)
        palm(f"Palm_{gx}_{gy}",gx,gy,5.2 if gy<0 else 5.8)
        for dx,dy in [(-1.5,-.9),(1.5,-.9),(-1.5,.9),(1.5,.9)]:
            cyl(f"Shrub_{gx}_{gy}_{dx}_{dy}",(gx+dx,gy+dy,.50),.48,.8,GREEN,28)

# Central walkway and small rectangular fountain/tile basins.
walk=mat("Walkway",(0.73,0.68,0.57),0.0,.90)
box("MainWalk",(0,1.0,.03),(5.2,21,.08),walk,.0)
for y in (-6.0,-1.5,3.0,7.5):
    box(f"BasinBorder_{y}",(0,y,.16),(3.6,1.9,.28),LIGHT,.05)
    box(f"BasinWater_{y}",(0,y,.31),(3.1,1.38,.05),WATER,.02)

# Lamps along main paths.
for y in (-8.2,-4.0,.2,4.4,8.6):
    lamp_post(f"LampL_{y}",-3.8,y); lamp_post(f"LampR_{y}",3.8,y)

# Secondary simple prayer hall at left rear.
box("PrayerHall",(-10.5,10.7,2.45),(7.0,4.5,4.9),CREAM,.08)
dome("PrayerDome",(-10.5,10.6,5.55),1.9,LIGHT)
# Carpet visible through open front opening.
carpet=mat("PrayerCarpet",(0.45,0.12,0.07),0.0,.92)
box("PrayerCarpet",(-10.5,8.55,.08),(6.2,3.6,.09),carpet,.01)

# Parking separators and curb near bus area.
CURB=mat("Curb",(0.58,0.56,0.52),0.0,.88)
for x in (-15,-7.5,0,7.5,15):
    box(f"ParkingLine_{x}",(x,19.8,.04),(.10,7.5,.025),LIGHT,.0)
box("RoadCurb",(0,15.9,.16),(48,.38,.32),CURB,.03)

# Root and export.
root=bpy.data.objects.new("MiqatAbyarAli",None); bpy.context.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is not root and o.parent is None: o.parent=root

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',
    use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
print("V10_MIQAT",os.path.abspath(out))
