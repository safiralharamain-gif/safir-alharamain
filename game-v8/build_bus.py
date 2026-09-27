import bpy, math, os, sys

# SAFIR coach generator v8.
# Blender coordinates: X=width, Y=length, Z=UP. glTF export_yup converts correctly to Godot.
argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out = argv[0] if argv else "coach_bus.glb"
style = argv[1] if len(argv) > 1 else "standard"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, color, metallic=0.0, rough=0.5, transmission=0.0, alpha=1.0, emission=None):
    m=bpy.data.materials.new(name)
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1)
    bs.inputs["Metallic"].default_value=metallic
    bs.inputs["Roughness"].default_value=rough
    if "Transmission Weight" in bs.inputs:
        bs.inputs["Transmission Weight"].default_value=transmission
    if alpha < 1:
        bs.inputs["Alpha"].default_value=alpha
        try: m.surface_render_method='DITHERED'
        except: pass
    if emission:
        bs.inputs["Emission Color"].default_value=(*emission,1)
        bs.inputs["Emission Strength"].default_value=2.5
    return m

if style == "safir":
    BODY=mat("SafirBlack",(0.025,0.028,0.032),0.45,0.22)
    ACCENT=mat("SafirGold",(0.74,0.48,0.08),0.78,0.18)
    LOWER=mat("SafirLower",(0.045,0.045,0.05),0.48,0.30)
else:
    BODY=mat("CoachWhite",(0.91,0.92,0.93),0.12,0.30)
    ACCENT=mat("CoachBlue",(0.045,0.23,0.48),0.52,0.23)
    LOWER=mat("CoachLower",(0.08,0.10,0.13),0.40,0.34)
BLACK=mat("Rubber",(0.012,0.014,0.018),0.02,0.84)
GLASS=mat("TintedGlass",(0.022,0.065,0.095),0.12,0.08,0.20,0.72)
CHROME=mat("Chrome",(0.48,0.51,0.54),0.92,0.10)
LAMP=mat("HeadLamp",(0.95,0.83,0.52),0.06,0.18,emission=(1.0,0.72,0.30))
RED=mat("TailLamp",(0.50,0.012,0.012),0.05,0.25,emission=(0.65,0.01,0.005))

def rounded_box(name, loc, size, material, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object
    o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        md=o.modifiers.new("Bevel",'BEVEL')
        md.width=bevel
        md.segments=4
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=md.name)
    o.data.materials.append(material)
    return o

def cyl(name, loc, radius, depth, material, rot=(0,0,0), verts=56):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    o.data.materials.append(material)
    return o

# Dimensions ~2.65m W x 10.8m L x 3.45m H.
rounded_box("CoachShell",(0,0,1.75),(2.66,10.75,3.10),BODY,0.20)
rounded_box("LowerSkirt",(0,0,0.66),(2.72,10.84,0.70),LOWER,0.10)
rounded_box("AccentBelt",(0,-0.02,1.02),(2.735,10.78,0.11),ACCENT,0.025)
rounded_box("Roof",(0,0,3.30),(2.50,10.10,0.30),BODY,0.14)

# Windows: side panels on X surfaces, length along Y.
for side in (-1,1):
    x=side*1.342
    for i,y in enumerate([-4.15,-2.90,-1.65,-0.40,0.85,2.10,3.35,4.35]):
        rounded_box(f"SideWindow_{side}_{i}",(x,y,2.28),(0.045,0.98,1.08),GLASS,0.035)
    # luggage bay seams
    for y in (-3.4,-1.2,1.0,3.2):
        rounded_box(f"Luggage_{side}_{y}",(side*1.37,y,0.66),(0.026,1.85,0.035),CHROME,0.008)

# Front is -Y, rear is +Y.
wind=rounded_box("Windshield",(0,-5.40,2.30),(2.18,0.06,1.16),GLASS,0.07)
wind.rotation_euler.x=math.radians(8)
rounded_box("RearGlass",(0,5.40,2.30),(2.02,0.06,1.05),GLASS,0.07)
rounded_box("FrontMask",(0,-5.43,1.10),(2.30,0.13,0.62),LOWER,0.06)
rounded_box("FrontBumper",(0,-5.53,0.47),(2.42,0.20,0.27),CHROME,0.06)
rounded_box("RearBumper",(0,5.53,0.47),(2.42,0.20,0.27),CHROME,0.06)
for x in (-0.78,0.78):
    rounded_box(f"Headlight_{x}",(x,-5.52,0.96),(0.54,0.10,0.23),LAMP,0.05)
    rounded_box(f"Fog_{x}",(x,-5.58,0.60),(0.28,0.07,0.13),LAMP,0.035)
    rounded_box(f"Tail_{x}",(x,5.50,1.02),(0.44,0.08,0.58),RED,0.055)

# Passenger door, right side (+X), near front (-Y).
rounded_box("DoorFrame",(1.385,-4.18,1.55),(0.055,1.42,2.58),ACCENT,0.025)
rounded_box("DoorGlass",(1.405,-4.18,2.12),(0.040,1.18,1.22),GLASS,0.025)
rounded_box("DoorStep",(1.55,-4.30,0.26),(0.42,1.12,0.13),LOWER,0.04)

# Wheels: cylinder axis along X, so rotate 90° about Y.
for y in (-3.30,3.18):
    for side in (-1,1):
        cyl(f"Wheel_{side}_{y}",(side*1.38,y,0.55),0.53,0.34,BLACK,(0,math.radians(90),0),64)
        cyl(f"Hub_{side}_{y}",(side*1.56,y,0.55),0.24,0.055,CHROME,(0,math.radians(90),0),48)

# Mirrors and arms.
for side in (-1,1):
    arm=cyl(f"MirrorArm_{side}",(side*1.60,-4.80,2.45),0.035,0.52,CHROME,(0,math.radians(90),0),24)
    rounded_box(f"Mirror_{side}",(side*1.86,-4.82,2.47),(0.22,0.32,0.42),BLACK,0.07)

# Roof A/C
rounded_box("RoofAC1",(0,-1.55,3.52),(1.35,1.70,0.22),BODY,0.09)
rounded_box("RoofAC2",(0,1.50,3.52),(1.35,1.70,0.22),BODY,0.09)

# Distinct roof beacon on SAFIR bus.
if style == "safir":
    BEACON=mat("SafirBeacon",(0.82,0.54,0.08),0.45,0.16,emission=(1.0,0.55,0.06))
    cyl("SafirBeacon",(0,-3.95,3.62),0.18,0.12,BEACON,(0,0,0),40)

root=bpy.data.objects.new("CoachBus",None)
bpy.context.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is not root and o.parent is None:
        o.parent=root

bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',use_selection=True,
                          export_apply=True,export_yup=True,export_materials='EXPORT')
print("EXPORTED",style,os.path.abspath(out))
