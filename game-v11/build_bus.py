import bpy, math, os, sys

# Modern 3-axle pilgrimage coach inspired by the user's reference:
# long panoramic black window band, rounded nose, three axles, tall mirrors.
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=argv[0] if argv else "coach.glb"
style=argv[1] if len(argv)>1 else "standard"

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)

def mat(name,c,metal=0.0,rough=.5,alpha=1.0,em=None):
    m=bpy.data.materials.new(name); m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*c,1)
    bs.inputs["Metallic"].default_value=metal
    bs.inputs["Roughness"].default_value=rough
    if alpha<1:
        bs.inputs["Alpha"].default_value=alpha
        try:m.surface_render_method='DITHERED'
        except:pass
    if em:
        bs.inputs["Emission Color"].default_value=(*em,1); bs.inputs["Emission Strength"].default_value=2.4
    return m

if style=="safir":
    BODY=mat("SafirPearlBlack",(0.018,0.022,0.028),0.52,0.18)
    LOWER=mat("SafirBlackLower",(0.03,0.033,0.038),0.40,0.26)
    ACC=mat("SafirGold",(0.78,0.51,0.08),0.76,0.17)
else:
    BODY=mat("CoachSilver",(0.82,0.84,0.86),0.54,0.20)
    LOWER=mat("CoachLower",(0.10,0.12,0.14),0.36,0.30)
    ACC=mat("CoachAccent",(0.11,0.32,0.46),0.52,0.22)
GLASS=mat("PanoramicGlass",(0.018,0.035,0.048),0.18,0.07,0.82)
RUBBER=mat("Tyres",(0.008,0.009,0.011),0.02,0.90)
CHROME=mat("Chrome",(0.48,0.51,0.54),0.94,0.08)
HEAD=mat("Headlamp",(0.92,0.90,0.74),0.04,0.16,1.0,(1.0,0.86,0.48))
TAIL=mat("TailLamp",(0.58,0.01,0.012),0.04,0.20,1.0,(0.72,0.01,0.008))

def box(name,loc,size,ma,bev=.08):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bev>0:
        md=o.modifiers.new("Soft",'BEVEL'); md.width=bev; md.segments=5
        bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=md.name)
    o.data.materials.append(ma); return o

def cyl(name,loc,r,d,ma):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=r,depth=d,location=loc,rotation=(0,math.radians(90),0))
    o=bpy.context.object; o.name=name; o.data.materials.append(ma); return o

# Coach dimensions around 13m L, 2.6m W, 3.7m H.
box("MainShell",(0,0,1.72),(2.62,12.55,3.12),BODY,.24)
box("LowerSkirt",(0,0,0.62),(2.70,12.65,0.74),LOWER,.11)
box("RoofCap",(0,0,3.34),(2.50,11.95,0.34),BODY,.16)
box("AccentLine",(0,-0.02,1.02),(2.715,12.55,0.095),ACC,.025)

# Large continuous panoramic side window band.
for side in (-1,1):
    x=side*1.326
    # one long dark glass band, then slim pillars on top
    box(f"GlassBand_{side}",(x,0.15,2.34),(0.045,10.90,1.20),GLASS,.045)
    for y in (-4.55,-3.05,-1.55,-0.05,1.45,2.95,4.45):
        box(f"Pillar_{side}_{y}",(x*1.002,y,2.34),(0.052,0.065,1.22),BODY,.015)
    # luggage door seams
    for y in (-3.9,-1.6,0.7,3.0):
        box(f"LuggageSeam_{side}_{y}",(side*1.365,y,0.63),(0.024,1.95,0.035),CHROME,.008)

# Panoramic front/rear glass.
front=box("Windshield",(0,-6.34,2.42),(2.28,0.07,1.38),GLASS,.12)
front.rotation_euler.x=math.radians(9)
box("RearGlass",(0,6.34,2.36),(2.10,0.065,1.14),GLASS,.09)

# Sculpted nose / bumpers / grille.
box("FrontUpper",(0,-6.39,1.54),(2.34,0.18,0.66),BODY,.11)
box("FrontMask",(0,-6.45,0.94),(2.38,0.18,0.62),LOWER,.10)
box("FrontBumper",(0,-6.52,0.44),(2.43,0.20,0.26),CHROME,.07)
box("RearBumper",(0,6.50,0.44),(2.42,0.18,0.24),CHROME,.07)
for x in (-0.76,0.76):
    box(f"Head_{x}",(x,-6.51,0.92),(0.58,0.09,0.23),HEAD,.06)
    box(f"DRL_{x}",(x,-6.53,1.14),(0.40,0.07,0.06),HEAD,.03)
    box(f"Tail_{x}",(x,6.48,1.02),(0.38,0.07,0.70),TAIL,.06)
box("Grille",(0,-6.54,0.70),(1.05,0.06,0.23),CHROME,.04)

# Passenger door right-front.
box("DoorFrame",(1.355,-5.05,1.57),(0.055,1.35,2.62),ACC,.025)
box("DoorGlass",(1.378,-5.05,2.20),(0.035,1.16,1.18),GLASS,.025)
box("DoorLower",(1.378,-5.05,0.95),(0.035,1.16,0.92),BODY,.025)
box("EntryStep",(1.53,-5.12,0.25),(0.38,0.98,0.12),LOWER,.035)

# Three axles: one front, tandem rear like the reference coach.
axles=(-4.15,2.85,4.12)
for y in axles:
    for side in (-1,1):
        cyl(f"Wheel_{side}_{y}",(side*1.36,y,0.54),0.52,0.34,RUBBER)
        cyl(f"Hub_{side}_{y}",(side*1.545,y,0.54),0.22,0.055,CHROME)

# Tall front mirrors.
for side in (-1,1):
    # arm along width
    bpy.ops.mesh.primitive_cylinder_add(vertices=28,radius=.035,depth=.58,
        location=(side*1.60,-5.65,2.55),rotation=(0,math.radians(90),0))
    arm=bpy.context.object; arm.data.materials.append(CHROME)
    box(f"Mirror_{side}",(side*1.88,-5.68,2.60),(0.24,0.35,0.54),LOWER,.09)

# Roof HVAC detail.
box("RoofAC1",(0,-1.7,3.56),(1.32,1.78,0.22),BODY,.09)
box("RoofAC2",(0,1.35,3.56),(1.32,1.78,0.22),BODY,.09)

# The SAFIR coach has an unmistakable gold roof/side stripe and luminous marker.
if style=="safir":
    box("SafirRoofStripe",(0,0,3.53),(0.16,11.7,0.055),ACC,.02)
    box("SafirSideBadgeL",(-1.373,0.2,1.32),(0.035,3.3,0.28),ACC,.03)
    box("SafirSideBadgeR",(1.373,0.2,1.32),(0.035,3.3,0.28),ACC,.03)
    beacon=mat("Beacon",(0.95,0.60,0.04),0.28,0.14,1.0,(1.0,.48,.02))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=36,ring_count=18,location=(0,-4.7,3.72),scale=(.18,.18,.13))
    bpy.context.object.data.materials.append(beacon)

root=bpy.data.objects.new("CoachBus",None); bpy.context.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is not root and o.parent is None: o.parent=root

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',use_selection=True,
    export_apply=True,export_yup=True,export_materials='EXPORT')
print("V9_BUS",style,os.path.abspath(out))
