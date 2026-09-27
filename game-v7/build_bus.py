import bpy, math, os, sys
from mathutils import Vector

# Realistic coach-bus generator for SAFIR Hajj & Umrah Training v7.
# Uses only Blender primitives/materials and exports a self-contained GLB.

argv = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out = argv[0] if argv else "coach_bus.glb"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def mat(name, color, metallic=0.0, rough=0.5, transmission=0.0, alpha=1.0):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color, alpha)
    m.use_nodes=True
    bs=m.node_tree.nodes.get("Principled BSDF")
    bs.inputs["Base Color"].default_value=(*color,1)
    bs.inputs["Metallic"].default_value=metallic
    bs.inputs["Roughness"].default_value=rough
    if "Transmission Weight" in bs.inputs:
        bs.inputs["Transmission Weight"].default_value=transmission
    if alpha<1:
        bs.inputs["Alpha"].default_value=alpha
        m.surface_render_method='DITHERED'
    return m

WHITE=mat("CoachPearl",(0.94,0.93,0.88),0.12,0.28)
GOLD=mat("SafirGold",(0.56,0.40,0.12),0.72,0.22)
BLACK=mat("Rubber",(0.018,0.020,0.024),0.05,0.72)
GLASS=mat("TintedGlass",(0.025,0.065,0.10),0.18,0.10,0.18,0.72)
CHROME=mat("Chrome",(0.42,0.45,0.48),0.92,0.12)
LIGHT=mat("Lamp",(1.0,0.86,0.52),0.05,0.18)
RED=mat("TailLamp",(0.66,0.025,0.018),0.05,0.24)
DARK=mat("LowerBody",(0.08,0.095,0.11),0.38,0.34)

def rounded_box(name, loc, scale, material, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object
    o.name=name
    o.scale=(scale[0]/2,scale[1]/2,scale[2]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel>0:
        mod=o.modifiers.new("SoftCoachEdges",'BEVEL')
        mod.width=bevel
        mod.segments=4
        bpy.context.view_layer.objects.active=o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(material)
    return o

def cyl(name, loc, radius, depth, material, rot=(0,0,0), verts=48):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=radius,depth=depth,location=loc,rotation=rot)
    o=bpy.context.object
    o.name=name
    o.data.materials.append(material)
    return o

# Main coach body: 2.65m wide x 3.35m tall x 10.8m long.
rounded_box("CoachShell",(0,1.78,0),(2.66,3.18,10.7),WHITE,0.22)
rounded_box("LowerSkirt",(0,0.72,0),(2.72,0.72,10.82),DARK,0.10)
rounded_box("GoldBelt",(0,1.02,0),(2.73,0.10,10.75),GOLD,0.03)

# Rounded roof cap.
rounded_box("Roof",(0,3.30,0),(2.54,0.34,10.20),WHITE,0.16)

# Side windows — individual panes with body pillars.
for side in (-1,1):
    x=side*1.342
    for i,z in enumerate([-3.85,-2.55,-1.25,0.05,1.35,2.65,3.95]):
        pane=rounded_box(f"SideWindow_{side}_{i}",(x,2.27,z),(0.045,1.12,1.05),GLASS,0.035)
    # lower luggage-bay seams
    for z in [-3.0,-1.0,1.0,3.0]:
        rounded_box(f"LuggageSeam_{side}_{z}",(side*1.37,0.75,z),(0.025,0.04,1.75),CHROME,0.01)

# Windshield and rear glass, angled slightly.
front=rounded_box("Windshield",(0,2.27,-5.38),(2.20,1.18,0.055),GLASS,0.08)
front.rotation_euler.x=math.radians(-8)
rear=rounded_box("RearGlass",(0,2.30,5.38),(2.08,1.10,0.055),GLASS,0.08)

# Front fascia/grille and bumper.
rounded_box("FrontMask",(0,1.05,-5.43),(2.30,0.65,0.12),DARK,0.06)
rounded_box("FrontBumper",(0,0.47,-5.53),(2.42,0.26,0.20),CHROME,0.07)
for x in (-0.78,0.78):
    rounded_box(f"Headlight{x}",(x,0.96,-5.52),(0.52,0.22,0.10),LIGHT,0.06)
    rounded_box(f"Fog{x}",(x,0.60,-5.58),(0.30,0.14,0.08),LIGHT,0.04)
for x in (-0.72,0.72):
    rounded_box(f"Tail{x}",(x,1.02,5.48),(0.46,0.62,0.08),RED,0.07)
rounded_box("RearBumper",(0,0.48,5.52),(2.42,0.28,0.18),CHROME,0.07)

# Passenger door on right side near front, plus step.
rounded_box("DoorGlass",(1.37,2.18,-4.22),(0.055,1.35,1.15),GLASS,0.04)
rounded_box("DoorFrame",(1.39,1.45,-4.22),(0.065,2.56,1.31),GOLD,0.025)
rounded_box("DoorStep",(1.54,0.28,-4.30),(0.42,0.14,1.18),DARK,0.04)

# Wheels, hubs, wheel arches accents.
for z in (-3.25,3.18):
    for side in (-1,1):
        wheel=cyl(f"Wheel_{side}_{z}",(side*1.36,0.55,z),0.53,0.34,BLACK,(0,math.radians(90),0),64)
        hub=cyl(f"Hub_{side}_{z}",(side*1.55,0.55,z),0.24,0.055,CHROME,(0,math.radians(90),0),48)

# Mirrors + arms.
for side in (-1,1):
    arm=cyl(f"MirrorArm_{side}",(side*1.62,2.42,-4.82),0.035,0.55,CHROME,(0,math.radians(90),0),24)
    rounded_box(f"Mirror_{side}",(side*1.88,2.46,-4.82),(0.22,0.42,0.32),BLACK,0.08)

# Roof HVAC units.
rounded_box("RoofAC1",(0,3.56,-1.4),(1.35,0.24,1.65),WHITE,0.10)
rounded_box("RoofAC2",(0,3.56,1.4),(1.35,0.24,1.65),WHITE,0.10)

# Side SAFIR wordmark as raised geometry (Latin for portability).
for side in (-1,1):
    bpy.ops.object.text_add(location=(side*1.385,1.32,0.3),rotation=(math.radians(90),0,math.radians(90 if side<0 else -90)))
    t=bpy.context.object
    t.name=f"SAFIR_{side}"
    t.data.body="SAFIR"
    t.data.align_x='CENTER'
    t.data.size=0.48
    t.data.extrude=0.012
    t.data.bevel_depth=0.008
    t.data.materials.append(GOLD)

# Parent all to one root for easier Godot placement.
root=bpy.data.objects.new("CoachBus",None)
bpy.context.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is not root and o.parent is None:
        o.parent=root

# Select everything and export.
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_materials='EXPORT')
print("EXPORTED",os.path.abspath(out))
