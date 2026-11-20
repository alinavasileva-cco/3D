import bpy, os, numpy as np, hashlib
from mathutils import Vector
ROOT=r'C:\Users\alina\Desktop\Blender_AI\TABLE_02_PREPPY'
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'PREPPY_TABLE_02_blenderkit.blend'))
scene=bpy.context.scene
objs=[o for o in scene.objects if o.type=='MESH' and not any(x in o.name.lower() for x in ['ground','stage'])]
# Adjust leg-tip contact by 1 mm, preserving overall table geometry.
for o in objs:
 if o.name.startswith('SOLID_BEECH_LEG'):
  inv=o.matrix_world.inverted()
  for v in o.data.vertices:
   w=o.matrix_world @ v.co
   if w.z<0.03:
    w.z-=0.001
    v.co=inv @ w
mat=next(m for m in bpy.data.materials if m.name.startswith('TABLE_02_PREPPY |') and m.use_nodes)
nodes=mat.node_tree.nodes
tex=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'diffuse' in n.image.name.lower())
im=tex.image
colors=np.empty(len(im.pixels),dtype='float32');im.pixels.foreach_get(colors);colors=colors.reshape(-1,4)
# Bake Blender Mix(MULTIPLY, factor .72, walnut tint .48/.36/.29).
# Additional darkening in response to the comparison of original and Cycles render.
multiply=np.array([0.28+.72*.48,0.28+.72*.36,0.28+.72*.29],dtype='float32')
factor=np.array([.74,.70,.67],dtype='float32')
colors[:,:3]=np.clip(colors[:,:3]*multiply*factor,0.001,1)
img=bpy.data.images.new('PREPPY_WALNUT_REFERENCE_CALIBRATED',width=im.size[0],height=im.size[1],alpha=True,float_buffer=False)
img.pixels.foreach_set(colors.ravel())
img.filepath_raw=os.path.join(ROOT,'PREPPY_WALNUT_REFERENCE_CALIBRATED.png')
img.file_format='PNG';img.save()
newimage=bpy.data.images.load(img.filepath_raw,check_existing=False)
newimage.colorspace_settings.name='sRGB'
tex.image=newimage
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for l in list(mat.node_tree.links):
 if l.to_node==bsdf and l.to_socket.name=='Base Color':
  mat.node_tree.links.remove(l)
mat.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
bsdf.inputs['Metallic'].default_value=0
legs_mat=mat.copy();legs_mat.name='PREPPY_STAINED_BEECH_LEGS'
for o in objs:
 if o.name.startswith('SOLID_BEECH_LEG'):
  for i in range(len(o.data.materials)):o.data.materials[i]=legs_mat
mat.name='PREPPY_MDF_WALNUT_VENEER'
for ob in scene.objects:ob.select_set(False)
for ob in objs:ob.select_set(True)
bpy.context.view_layer.objects.active=objs[0]
coords=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
bb_min=[min(v[i] for v in coords) for i in range(3)]
bb_max=[max(v[i] for v in coords) for i in range(3)]
dims=[bb_max[i]-bb_min[i] for i in range(3)]
print('FINAL_BOUNDS',dims,'FLOOR',bb_min[2],flush=True)
assert abs(dims[0]-1.2)<.001 and abs(dims[1]-.62)<.001 and abs(dims[2]-.76)<.001
blend=os.path.join(ROOT,'PREPPY_TABLE_02_COLORFIX.blend')
glb=os.path.join(ROOT,'PREPPY_TABLE_02_COLORFIX.glb')
bpy.ops.wm.save_as_mainfile(filepath=blend,compress=True)
bpy.ops.export_scene.gltf(filepath=glb,export_format='GLB',use_selection=True,export_materials='EXPORT',export_yup=True,export_image_format='AUTO')
print('EXPORTED',os.path.getsize(glb),'SHA256',hashlib.sha256(open(glb,'rb').read()).hexdigest(),flush=True)
scene.render.engine='CYCLES';scene.cycles.samples=28
scene.render.resolution_x=1100;scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(ROOT,'PREPPY_TABLE_02_COLORFIX_cycles.png')
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',scene.render.filepath,flush=True)
