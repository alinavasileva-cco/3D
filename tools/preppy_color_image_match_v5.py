"""iModern Preppy: image-derived walnut veneer PBR, exact size, Blender master/GLB.
Requires the original 3 manufacturer photos in the working Preppy folder.
Never changes the main cabinet .blend.
"""
import bpy, os, numpy as np, json, hashlib
from mathutils import Vector
ROOT=r'C:\Users\alina\Desktop\Blender_AI\TABLE_02_PREPPY'
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'PREPPY_TABLE_02_blenderkit.blend'))
scene=bpy.context.scene
objects=[o for o in scene.objects if o.type=='MESH' and not any(t in o.name.lower() for t in ('ground','stage'))]
# Compare manufacturer photo wood-pixel medians in linear RGB, excluding white backgrounds.
def image_array(img):
 a=np.empty(len(img.pixels),dtype=np.float32)
 img.pixels.foreach_get(a)
 return a.reshape((img.size[1],img.size[0],4))[:,:,:3]
ref_medians=[]
for name in ('PREPPY_ORIGINAL_1.jpg','PREPPY_ORIGINAL_2.jpg','PREPPY_ORIGINAL_4.jpg'):
 img=bpy.data.images.load(os.path.join(ROOT,name),check_existing=False)
 a=image_array(img)
 s=np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
 mask=(s[:,:,0]>.12)&(s[:,:,0]>s[:,:,1]*1.07)&(s[:,:,1]>s[:,:,2]*1.045)&(s[:,:,0]<.93)&(s[:,:,1]<.78)
 assert mask.sum()>20000, (name,mask.sum())
 m=np.median(a[mask],axis=0)
 ref_medians.append(m)
 print('REFERENCE',name,'WOOD_MEDIAN_LINEAR',m,'SAMPLES',int(mask.sum()),flush=True)
 bpy.data.images.remove(img)
target=np.median(np.array(ref_medians),axis=0)
# Correct the verified 1-mm source-model clearance without changing width/depth.
world=[(o,v,o.matrix_world@v.co) for o in objects for v in o.data.vertices]
zmin=min(w.z for _,_,w in world);zmax=max(w.z for _,_,w in world)
assert abs((zmax-zmin)-.759)<.002
for o in objects:
 inv=o.matrix_world.inverted()
 for v in o.data.vertices:
  w=o.matrix_world@v.co
  w.z=(w.z-zmin)*(.760/(zmax-zmin))
  v.co=inv@w
 o.data.update()
bpy.context.view_layer.update()
material=next(m for m in bpy.data.materials if m.name.startswith('TABLE_02_PREPPY |') and m.use_nodes)
nodes=material.node_tree.nodes
tex=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'diffuse' in n.image.name.lower())
source=tex.image
rgba=np.empty(len(source.pixels),dtype=np.float32)
source.pixels.foreach_get(rgba)
rgba=rgba.reshape((-1,4))
source_median=np.median(rgba[:,:3],axis=0)
scaling=target/source_median
# Conserve measured median while increasing wood-grain contrast without a fixed arbitrary HEX.
contrast=1.30
rgba[:,:3]=np.clip(target[None,:]+(rgba[:,:3]-source_median[None,:])*scaling[None,:]*contrast,0.015,0.96)
print('ALBEDO_TARGET_LINEAR',target,'SOURCE_MEDIAN',source_median,'SCALE',scaling,flush=True)
corrected=bpy.data.images.new('PREPPY_02_WALNUT_IMAGE_MATCHED',width=source.size[0],height=source.size[1],alpha=True,float_buffer=False)
corrected.pixels.foreach_set(rgba.ravel())
path=os.path.join(ROOT,'PREPPY_02_WALNUT_IMAGE_MATCHED.jpg')
corrected.filepath_raw=path
corrected.file_format='JPEG'
scene.render.image_settings.quality=95
corrected.save()
newimg=bpy.data.images.load(path,check_existing=False)
newimg.colorspace_settings.name='sRGB'
tex.image=newimg
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for l in list(material.node_tree.links):
 if l.to_node==bsdf and l.to_socket.name=='Base Color':material.node_tree.links.remove(l)
material.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
bsdf.inputs['Metallic'].default_value=0.0
material.name='PREPPY_02_MDF_WALNUT_VENEER'
legs=material.copy();legs.name='PREPPY_02_SOLID_BEECH_WALNUT_STAIN'
for o in objects:
 if o.name.startswith('SOLID_BEECH_LEG'):
  for i in range(len(o.data.materials)):o.data.materials[i]=legs
for o in scene.objects:o.select_set(False)
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
v=[o.matrix_world@vert.co for o in objects for vert in o.data.vertices]
minimum=[float(min(p[i] for p in v)) for i in range(3)]
maximum=[float(max(p[i] for p in v)) for i in range(3)]
size=[maximum[i]-minimum[i] for i in range(3)]
assert abs(size[0]-1.2)<.0001 and abs(size[1]-.62)<.0001 and abs(size[2]-.76)<.0001 and abs(minimum[2])<.0001
print('MODEL_DIMENSIONS',size,'MIN',minimum,flush=True)
blend=os.path.join(ROOT,'PREPPY_TABLE_02_V5_IMAGE_MATCHED.blend')
glb=os.path.join(ROOT,'PREPPY_TABLE_02_V5_IMAGE_MATCHED.glb')
bpy.ops.wm.save_as_mainfile(filepath=blend,compress=True)
bpy.ops.export_scene.gltf(filepath=glb,export_format='GLB',use_selection=True,export_materials='EXPORT',export_yup=True,export_image_format='AUTO')
sha=hashlib.sha256(open(glb,'rb').read()).hexdigest()
print('GLB',os.path.getsize(glb),'sha256',sha,flush=True)
report={'source':['imodern.ru','inmyroom.ru'],'dimensions_m':size,'material':'walnut veneer MDF; walnut-stained beech legs','reference_linear_median_rgb':target.tolist(),'source_albedo_linear_median_rgb':source_median.tolist(),'correction_factors':scaling.tolist(),'texture_grain_contrast':contrast,'glb_sha256':sha,'glb_bytes':os.path.getsize(glb),'color_limit':'photo-based estimation, not spectrophotometric match'}
open(os.path.join(ROOT,'PREPPY_TABLE_02_V5_report.json'),'w',encoding='utf-8').write(json.dumps(report,ensure_ascii=False,indent=2))
scene.render.engine='CYCLES';scene.cycles.samples=22
scene.render.resolution_x=1100;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.exposure=-0.85
scene.render.image_settings.file_format='PNG'
scene.render.filepath=os.path.join(ROOT,'PREPPY_TABLE_02_V5_cycles.png')
bpy.ops.render.render(write_still=True)
print('RENDER_COMPLETE',scene.render.filepath,flush=True)
