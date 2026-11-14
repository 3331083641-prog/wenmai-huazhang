from pathlib import Path
import os,json,time,sys,math
sys.stdout.reconfigure(encoding='utf8')
W=Path(__file__).resolve().parents[1]/'.work/pavilion-ui-qa';W.mkdir(parents=True,exist_ok=True);out=W/'qa';out.mkdir(exist_ok=True)
for var,leaf in {'TMP':'tmp','TEMP':'tmp','TMPDIR':'tmp','APPDATA':'roaming','LOCALAPPDATA':'local','USERPROFILE':'profile','XDG_CACHE_HOME':'cache','PLAYWRIGHT_BROWSERS_PATH':'pw','BREAKPAD_DUMP_LOCATION':'crash'}.items():
 p=W/'runtime'/leaf;p.mkdir(parents=True,exist_ok=True);os.environ[var]=str(p)
from playwright.sync_api import sync_playwright
result={'checks':{},'errors':[],'traces':{}}
def save():(out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
def record(name,value):result['checks'][name]=bool(value);print(name,bool(value),flush=True);save()
with sync_playwright() as pw:
 ctx=pw.chromium.launch_persistent_context(user_data_dir=str(W/'runtime'/('accept'+str(time.time_ns()))),headless=False,env=dict(os.environ),timeout=60000,executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',args=['--no-proxy-server','--disable-crash-reporter','--enable-unsafe-swiftshader','--no-first-run','--disable-sync','--disable-component-update','--disable-breakpad','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-features=msEdgeSpotlight,msEdgeFirstRunExperience,msSmartScreenProtection','--disk-cache-dir='+str(W/'runtime/cache')])
 page=ctx.pages[0];page.set_default_timeout(30000);page.set_viewport_size({'width':1440,'height':960})
 page.on('pageerror',lambda e:(result['errors'].append(str(e)),print('ERROR',str(e),flush=True),save()))
 page.on('console',lambda m:result['errors'].append(m.text) if m.type=='error' else None)
 try:
  page.goto(os.environ.get('PAVILION_URL','http://127.0.0.1:5173/heritage-gallery'),wait_until='domcontentloaded',timeout=120000);page.bring_to_front()
  page.wait_for_function('window.__pavilion && window.__galleryStats',timeout=240000);page.wait_for_timeout(4000)
  record('thirty_frames',page.evaluate('__galleryStats.frames===30'))
  record('mascot_removed',page.get_by_text('灵宠',exact=False).count()==0 and page.locator('[data-testid="mascot-wake"]').count()==0)
  record('original_sky',page.evaluate('!!__pavilion.scene.getObjectByName("time-sky-dome")'))
  record('door_prompt_hidden_overview',page.locator('[data-testid="pavilion-door"]').is_hidden())
  page.screenshot(path=str(out/'heritage-gallery.jpg'),quality=92,timeout=90000)
  def view(label):
   page.get_by_role('button',name='视角',exact=True).click();page.get_by_role('button',name=label,exact=True).click();page.wait_for_timeout(1600)
  view('一层');page.screenshot(path=str(out/'heritage-interior.jpg'),quality=92,timeout=90000)
  view('二层');page.screenshot(path=str(out/'heritage-upper.jpg'),quality=92,timeout=90000)
  page.get_by_role('button',name='视角',exact=True).click();page.get_by_role('button',name='第一人称（站在展厅内部平视漫游）',exact=True).click()
  page.wait_for_timeout(800)
  get=lambda:page.evaluate('__pavilion.camera.position.toArray()')
  def at(p,yaw=-math.pi/2):page.evaluate('a=>__pavilion.place(...a)',[*p,yaw])
  def motion(name,keys,n):
   for k in keys:page.keyboard.down(k)
   try:
    trace=page.evaluate('n=>{let t=[];for(let i=0;i<n;i++){__pavilion.step(.016);t.push(__pavilion.camera.position.toArray());}Object.keys(__pavilion.keys).forEach(k=>__pavilion.keys[k]=false);return t}',n)
   finally:
    for k in keys:page.keyboard.up(k)
   result['traces'][name]={'start':trace[0],'end':trace[-1],'minY':min(p[1] for p in trace),'maxY':max(p[1] for p in trace)};save();return trace
  door=page.locator('[data-testid="pavilion-door"]')
  at([0,1.95,2.3]);t=motion('closed',['w','Shift'],48);record('closed_main_blocks',.24<t[-1][2]<.65)
  at([0,1.95,2.2]);motion('prompt',[],3);page.screenshot(path=str(out/'door-closed.jpg'),quality=92,timeout=90000)
  door.click();motion('opening',[],60);t=motion('enter',['w'],77);record('main_enter',t[-1][2]<-1.1)
  at([5.5,1.95,2]);motion('settle_wall',[],30);t=motion('wall',['w','Space','Shift'],71);record('sprint_jump_wall_blocks',t[-1][2]>.3 and max(a[1] for a in t)>2.4)
  at([0,1.65,8]);motion('settle',[],10);t=motion('jump',['Space'],75);record('jump_lands',max(a[1] for a in t)>2.4 and abs(t[-1][1]-1.65)<.17)
  for name,x,z,level,bed in [('front',4.9,12.7,-.55,-3.05),('rear',5,-25.8,-.3,-2.45)]:
   at([x,1.65,z]);inward,outward=('s','w') if name=='front' else ('w','s')
   motion(name+'_entry',[inward],108);motion(name+'_float',[],100);record(name+'_swim',get()[1]<level+.4)
   t=motion(name+'_dive',['c',inward],150);record(name+'_dive',bed+.29<=t[-1][1]<level-.75)
   t=motion(name+'_surface',['Space'],135);record(name+'_surface',level+.02<t[-1][1]<level+.3)
   t=motion(name+'_exit',['Space',outward],500);record(name+'_exit',t[-1][1]>1.5)
  for id,sign,z,north in [('zhuxianzhen',-1,30,False),('songhua',-1,12,True),('bianxiu',1,30,False),('qinghua',1,12,True),('jianzhi',0,42,False)]:
   cx=32*sign if sign else -20;ux,uz=(0,sign) if sign else (1,0);inset=5.675 if sign else 3.215;base=.2 if sign else .15
   def world(u,v):return (cx+ux*u+uz*v,z+uz*u-ux*v)
   def local():
    x,y,zz=get();return ((x-cx)*ux+(zz-z)*uz,(x-cx)*uz-(zz-z)*ux)
   def aim(du,dv):page.evaluate('a=>__pavilion.aim(a)',math.atan2(uz*du-ux*dv,ux*du+uz*dv))
   def walk(name,u,v):
    a,b=local();aim(u-a,v-b);page.keyboard.down('w')
    try:
     page.evaluate('''([x,z])=>{let prev=1e6;for(let i=0;i<230;i++){let p=__pavilion.camera.position,g=Math.hypot(p.x-x,p.z-z);if(g<.045||(i>3&&g>prev+.003))break;prev=g;__pavilion.step(.016);}__pavilion.keys.KeyW=false;}''',list(world(u,v)))
    finally:page.keyboard.up('w')
    a,b=local();gap=math.hypot(a-u,b-v);result['traces'][name]={'end':get(),'gap':gap};save();return gap<.24
   x,zz=world(0,-inset-1);at([x,base+1.65,zz]);aim(0,1);motion(id+'_closed',['w'],58);record(id+'_closed_blocks',-inset-.6<local()[1]<-inset-.23)
   door.click();motion(id+'_opening',[],60);record(id+'_enter',walk(id+'_entry',0,-inset+2.2))
   door.click();motion(id+'_closing',[],60);aim(0,-1);motion(id+'_inside',['w'],60);record(id+'_inside_blocks',-inset+.22<local()[1]<-inset+.7)
   walk(id+'_clear',0,-inset+2.25);door.click();motion(id+'_reopen',[],60)
   if north:
    aisle=1.95 if id=='songhua' else 1.65;path=[(aisle,-3.2),(aisle,1.75),(aisle,3.75),(.95,3.75),(-3.1,3.75),(-3.1,4.88),(1.52,4.88)]
    for i,(u,v) in enumerate(path):record(id+'_stairs_up_'+str(i),walk(id+'_up_'+str(i),u,v))
    record(id+'_upper_height',abs(get()[1]-5.91)<.08)
    for i,(u,v) in enumerate(reversed(path[:-1])):record(id+'_stairs_down_'+str(i),walk(id+'_down_'+str(i),u,v))
    record(id+'_lower_height',abs(get()[1]-(base+1.65))<.1);walk(id+'_return',0,-inset+2.25)
   record(id+'_exit',walk(id+'_exit',0,-inset-1.4))
  page.get_by_role('button',name='布展模式',exact=True).click();page.get_by_role('button',name='器物库',exact=False).first.click();page.wait_for_timeout(1000)
  record('diy_panel_retained',page.get_by_text('器物图库',exact=False).count()>0)
  page.screenshot(path=str(out/'heritage-diy.jpg'),quality=92,timeout=90000)
  page.set_viewport_size({'width':390,'height':844});record('mobile_no_overflow',page.evaluate('document.documentElement.scrollWidth===390'));page.screenshot(path=str(out/'mobile.jpg'),quality=90,timeout=90000)
  record('clean_console',not result['errors'])
 except Exception as e:
  result['exception']=repr(e);print(repr(e),flush=True);save();page.screenshot(path=str(out/'acceptance-failure.jpg'),quality=85,timeout=90000)
 finally:save();ctx.close()
if result.get('exception') or not all(result['checks'].values()):sys.exit(1)
