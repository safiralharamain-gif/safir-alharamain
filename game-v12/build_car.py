import bpy, math, os, sys

# Simple game-ready sedan, Blender axes X=width, Y=length, Z=up.
argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
out=argv[0] if argv else "traffic_car.glb"

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

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
        bs.inputs["Emission Color"].default_value=(*em,1)
        bs.inputs["Emission Strength"].default_value=2.0
    return m

BODY=mat("CarPaint",(0.18,0.23,0.32),0.72,0.18)
GLASS=mat("CarGlass",(0.02,0.045,0.065),0.10,0.08,0.78)
RUBBER=mat("Rubber",(0.012,0.014,0.018),0.02,0.85)
CHROME=mat("Chrome",(0.46,0.48,0.50),0.90,0.10)
LAMP=mat("Lamp",(0.95,0.88,0.66),0.05,0.18,1.0,(1.0,0.78,0.38))
RED=mat("Tail",(0.58,0.01,0.01),0.05,0.22,1.0,(0.72,0.01,0.005))

def box(name,loc,size,ma,bev=.08):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o=bpy.context.object; o.name=name
    o.scale=(size[0]/2,size[1]/2,size[2]/2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    md=o.modifiers.new("B",'BEVEL'); md.width=bev; md.segments=4
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=md.name)
    o.data.materials.append(ma); return o

def cyl(name,loc,r,d,ma):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=d,location=loc,rotation=(0,math.radians(90),0))
    o=bpy.context.object; o.name=name; o.data.materials.append(ma); return o

box("Body",(0,0,0.70),(1.84,4.35,0.68),BODY,.16)
box("Cabin",(0,0.18,1.22),(1.62,2.55,0.82),BODY,.22)
box("Windshield",(0,-1.12,1.30),(1.48,0.06,0.62),GLASS,.04)
box("RearWindow",(0,1.42,1.30),(1.42,0.06,0.58),GLASS,.04)
for side in (-1,1):
    for y in (-0.45,0.72):
        box(f"SideGlass_{side}_{y}",(side*.84,y,1.30),(.04,.88,.55),GLASS,.035)
for y in (-1.35,1.42):
    for side in (-1,1):
        cyl(f"Wheel_{side}_{y}",(side*.91,y,.47),.34,.22,RUBBER)
        cyl(f"Hub_{side}_{y}",(side*1.03,y,.47),.15,.04,CHROME)
for x in (-.62,.62):
    box(f"Head_{x}",(x,-2.20,.75),(.38,.08,.18),LAMP,.04)
    box(f"Tail_{x}",(x,2.20,.76),(.38,.08,.18),RED,.04)
box("FrontBumper",(0,-2.26,.47),(1.72,.12,.18),CHROME,.04)
box("RearBumper",(0,2.26,.47),(1.72,.12,.18),CHROME,.04)

root=bpy.data.objects.new("TrafficCar",None); bpy.context.collection.objects.link(root)
for o in list(bpy.context.scene.objects):
    if o is not root and o.parent is None: o.parent=root
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=os.path.abspath(out),export_format='GLB',use_selection=True,
                          export_apply=True,export_yup=True,export_materials='EXPORT')
print("EXPORTED",os.path.abspath(out))
