"""Bind the approved v003 web geometry for the gallery; preserve review sources.
Run with the local Blender adapter against WenWen_v003_web.blend.
"""
import bpy,math,json,hashlib
from pathlib import Path
from mathutils import Vector
R=Path(r'D:/wenmai-huazhang');C=bpy.data.collections['WenWen_v003_EXPORT'];bpy.context.preferences.filepaths.save_version=0
objects=[o for o in C.objects if o.type=='MESH']
for o in objects:
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
armdata=bpy.data.armatures.new('WenWen_GalleryRig');arm=bpy.data.objects.new('WenWen_GalleryRig',armdata);C.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
def bone(name,a,b,parent=None,deform=True):
 q=armdata.edit_bones.new(name);q.head=a;q.tail=b;q.use_deform=deform
 if parent:q.parent=armdata.edit_bones[parent]
bone('Root',(0,0,0),(0,0,.1),deform=False)
bone('Body',(0,0,.30),(0,0,.60),'Root')
bone('Head',(0,-.2,.68),(0,-.2,.98),'Body')
bone('Tail',(.08,.28,.43),(.58,.45,.83),'Body')
feet={}
for side,sx in [('L',-1),('R',1)]:
 for tag,x,y in [('Front',.134,-.254),('Back',.202,.194)]:
  name=tag+side;feet[name]=(sx*x,y)
  bone(name,(sx*x,y,.36),(sx*x,y,.10),'Body')
bpy.ops.object.mode_set(mode='OBJECT')
for pb in arm.pose.bones:pb.rotation_mode='XYZ'
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def body_weights(p):
 x,y,z=p
 tail=smooth(.28,.37,y)*smooth(.08,.22,x)*smooth(.31,.42,z)
 leg=(1-smooth(.27,.49,z))*smooth(.045,.105,abs(x))*(1-tail)
 head=smooth(.62,.72,z)*(1-smooth(.02,.15,y))*(1-tail)
 name=min(feet,key=lambda k:(x-feet[k][0])**2+(y-feet[k][1])**2)
 w={'Tail':tail,name:leg,'Head':head};w['Body']=max(0,1-sum(w.values()));total=sum(w.values())
 return {k:v/total for k,v in w.items() if v>1e-5}
headprefix=('WenWen_Head','WenWen_Eye','WenWen_Iris','WenWen_Tearline','WenWen_Ear','WenWen_Nose','WenWen_Smile','WenWen_Philtrum','WenWen_FineWhiskers')
for o in objects:
 groups={n:o.vertex_groups.new(name=n) for n in ['Body','Head','Tail',*feet]}
 if o.name.startswith(headprefix):groups['Head'].add(list(range(len(o.data.vertices))),1,'REPLACE')
 elif o.name in ['WenWen_Body_Organic','WenWen_AllPawPads']:
  for v in o.data.vertices:
   for n,w in body_weights(v.co).items():groups[n].add([v.index],w,'REPLACE')
 elif o.name=='WenWen_PortableShortFur':
  for poly in o.data.polygons:
   p=sum((o.data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
   weights={'Head':1} if p.z>.67 and p.y<.05 else body_weights(p)
   for n,w in weights.items():groups[n].add(list(poly.vertices),w,'REPLACE')
 else:groups['Body'].add(list(range(len(o.data.vertices))),1,'REPLACE')
 o.parent=arm;m=o.modifiers.new('Gallery_Deform','ARMATURE');m.object=arm
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
arm.animation_data_create();fps=30;bpy.context.scene.render.fps=fps
durations={'Idle':2.4,'Walk':.9,'Run':.6,'Turn':1.2,'Spawn':.9,'Happy':1.1,'Interact':1.2,'Curious':1.8}
for name,seconds in durations.items():
 act=bpy.data.actions.new(name);act.use_fake_user=True;arm.animation_data.action=act
 end=round(seconds*fps)
 for frame in sorted(set([*range(0,end+1,2),end])):
  t=frame/end;wave=math.sin(math.tau*t)
  for pb in arm.pose.bones:pb.rotation_euler=(0,0,0);pb.location=(0,0,0);pb.scale=(1,1,1)
  arm.pose.bones['Tail'].rotation_euler.z=.035*wave
  if name in ['Walk','Run']:
   amp=.20 if name=='Walk' else .30
   for leg,phase in [('FrontL',0),('BackR',0),('FrontR',math.pi),('BackL',math.pi)]:
    v=math.sin(math.tau*t+phase);pb=arm.pose.bones[leg];pb.rotation_euler.x=amp*v;pb.location.y=-.010*max(0,v)
   arm.pose.bones['Body'].location.y=.008*(1-math.cos(2*math.tau*t))
   arm.pose.bones['Head'].rotation_euler.x=.015*wave
  elif name=='Idle':arm.pose.bones['Head'].rotation_euler.x=.010*wave
  elif name=='Turn':arm.pose.bones['Head'].rotation_euler.z=.06*wave
  elif name=='Spawn':arm.pose.bones['Head'].rotation_euler.x=-.10*math.sin(math.pi*t)
  elif name=='Happy':arm.pose.bones['Body'].location.y=.07*math.sin(math.pi*t)**2;arm.pose.bones['Head'].rotation_euler.x=-.06*math.sin(math.pi*t)
  elif name=='Interact':arm.pose.bones['Head'].rotation_euler.x=.10*math.sin(math.pi*t)
  elif name=='Curious':arm.pose.bones['Head'].rotation_euler.z=.11*math.sin(math.pi*t);arm.pose.bones['Tail'].rotation_euler.z=.06*wave
  for pb in arm.pose.bones:
   pb.keyframe_insert('rotation_euler',frame=frame);pb.keyframe_insert('location',frame=frame)
 act.frame_start=0;act.frame_end=end
 # Store every action in its own named track for deterministic glTF export.
 arm.animation_data.action=None
 track=arm.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,0,act);strip.action_slot=act.slots[0];strip.action_frame_start=0;strip.action_frame_end=end;track.mute=True
arm.animation_data.action=None
for pb in arm.pose.bones:pb.rotation_euler=(0,0,0);pb.location=(0,0,0)
bpy.context.scene.frame_set(0)
resized=[]
for im in bpy.data.images:
 if im.source=='FILE':
  if max(im.size)>1024:
   ratio=1024/max(im.size);old=list(im.size);im.scale(max(1,round(im.size[0]*ratio)),max(1,round(im.size[1]*ratio)));resized.append({'name':im.name,'before':old,'after':list(im.size)})
  im.pack()
blend=R/'assets/mascot/blender/WenWen_v003_gallery.blend';blend.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.object.select_all(action='DESELECT')
for o in [arm,*objects]:o.select_set(True)
bpy.context.view_layer.objects.active=arm
out=R/'frontend/public/models/WenWen_v003_gallery.glb'
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_def_bones=True,export_anim_slide_to_zero=True,export_force_sampling=True,export_cameras=False,export_lights=False,export_yup=True)
data=out.read_bytes();import struct
n=struct.unpack_from('<I',data,12)[0];doc=json.loads(data[20:20+n])
clips=[a['name'] for a in doc.get('animations',[])];assert set(clips)==set(durations),clips
assert doc.get('skins'), 'Missing skin'
report={'model':str(out),'blend':str(blend),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'animations':clips,'skins':len(doc['skins']),'bones':len(armdata.bones),'texture_limit':1024,'resized_images':resized,'note':'In-place basic gallery rig and eight clips; world movement belongs to the existing UI controller.'}
p=R/'docs/mascot/v003-integration';p.mkdir(parents=True,exist_ok=True);(p/'asset.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GALLERY_ASSET',json.dumps(report))
