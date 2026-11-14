import * as THREE from 'three';

// Metres in the delivered GLB. u follows the opening, v points into the room.
// The jambs and transoms stay in the static architectural mesh.
const entrances=[
  {name:'主殿',x:0,z:.03,ux:1,uz:0,half:2.52,width:2.52,bottom:.445,top:5.885,thickness:.105,main:true},
  ...[['刊木堂',-32,30],['澄怀轩',-32,12],['针经阁',32,30],['素肌堂',32,12]].map(([name,cx,z])=>({
    name,x:cx-Math.sign(cx)*5.675,z,ux:0,uz:Math.sign(cx),half:1.675,width:1.67,bottom:.22,top:3.972,thickness:.0275
  })),
  {name:'镂金坊',x:-20,z:45.215,ux:1,uz:0,half:1.475,width:1.47,bottom:.17,top:2.922,thickness:.0275}
];
const angle=Math.PI*85/180;
const margin=.00015;
function coords(d,x,z) {
  const dx=x-d.x,dz=z-d.z;
  return [dx*d.ux+dz*d.uz,dx*d.uz-dz*d.ux];
}
function overlaps(d,x,z,eye,radius,fraction) {
  if(eye+.12<d.bottom || eye-1.65>d.top) return false;
  const [u,v]=coords(d,x,z);
  if(Math.abs(u)>d.half+radius+.15 || Math.abs(v)>d.width+radius+.15) return false;
  const theta=fraction*angle,c=Math.cos(theta),s=Math.sin(theta);
  for(const side of [-1,1]) {
    const a=(u-side*d.half)*-side;
    const along=a*c+v*s,across=-a*s+v*c;
    if(Math.hypot(Math.max(0,-along,along-d.width),Math.max(0,Math.abs(across)-d.thickness))<radius) return true;
  }
  return false;
}
function vertexPanel(doors,x,y,z,material) {
  for(let i=0;i<doors.length;i++) {
    const d=doors[i];
    if(y<d.bottom-margin || y>d.top+margin || Math.abs(x-d.x)>d.half+.2 || Math.abs(z-d.z)>d.half+.2) continue;
    if(material==='bronze' && !d.main) continue;
    const [u,v]=coords(d,x,z);
    const limit=d.main?d.half-.009:d.half+margin;
    if(Math.abs(u)>limit || v>d.thickness+margin || v< -d.thickness-(d.main?.05:0)-margin) continue;
    return 2*i+(u<0?1:2);
  }
  return 0;
}

export function mountDoor(root,button,camera,state,shadowMap,tell) {
  const original=[];
  const doors=entrances.map(spec=>{
    const d={...spec,fraction:0,target:0};
    d.wings=[-1,1].map(side=>{
      const wing=new THREE.Group();
      wing.name=d.name+(side<0?'左扇':'右扇');
      wing.position.set(d.x+side*d.half*d.ux,0,d.z+side*d.half*d.uz);
      return wing;
    });
    return d;
  });
  const allWings=doors.flatMap(d=>d.wings);
  root.traverse(mesh=>{
    if(!mesh.isMesh || !['wood_dark','glass','bronze'].includes(mesh.material.name)) return;
    const g=mesh.geometry,pos=g.attributes.position,index=g.index;
    const labels=new Uint8Array(pos.count);
    for(let i=0;i<pos.count;i++) labels[i]=vertexPanel(doors,pos.getX(i),pos.getY(i),pos.getZ(i),mesh.material.name);
    const keep=[],panels=allWings.map(()=>[]);
    for(let i=0;i<(index?.count??pos.count);i+=3) {
      const a=index?index.getX(i):i,b=index?index.getX(i+1):i+1,c=index?index.getX(i+2):i+2,id=labels[a];
      (id && id===labels[b] && id===labels[c]?panels[id-1]:keep).push(a,b,c);
    }
    panels.forEach((indices,j)=>{
      if(!indices.length) {
        if(mesh.material.name!=='bronze' || j<2) throw new Error('门扇几何缺失 '+allWings[j].name+' '+mesh.material.name);
        return;
      }
      const geo=new THREE.BufferGeometry();
      for(const [key,attr] of Object.entries(g.attributes)) geo.setAttribute(key,attr);
      geo.setIndex(indices);
      const wing=allWings[j],leaf=new THREE.Mesh(geo,mesh.material);
      leaf.position.copy(wing.position).negate();
      leaf.castShadow=leaf.receiveShadow=true;leaf.userData.movingDoor=true;
      wing.add(leaf);
    });
    original.push([g,g.index]);
    g.setIndex(keep);
  });
  root.add(...allWings);
  function nearby() {
    if(state.mode!=='roam' || state.tween) return;
    const p=camera.position;
    return doors.find(d=>{
      if(p.y<=d.bottom || p.y>=d.top) return false;
      const [u,v]=coords(d,p.x,p.z);
      return Math.abs(u)<d.half+.12 && Math.hypot(Math.max(0,Math.abs(u)-d.half),v)<3.25;
    });
  }
  function toggle() {
    const d=nearby();
    if(d) d.target=1-d.target;
  }
  function tick(dt) {
    for(const d of doors) {
      const next=d.fraction+Math.sign(d.target-d.fraction)*Math.min(Math.abs(d.target-d.fraction),dt*1.12);
      if(next===d.fraction) continue;
      const p=camera.position;
      if(state.mode==='roam' && overlaps(d,p.x,p.z,p.y,.27,next)) {
        d.target=next>d.fraction?0:1;
        tell('请让开门扇摆动的位置');
        continue;
      }
      d.fraction=next;
      d.wings[0].rotation.y=next*angle;d.wings[1].rotation.y=-next*angle;
      shadowMap.needsUpdate=true;
    }
    const d=nearby();
    button.hidden=!d || (document.getElementById('helpMask')?.hidden===false);
    if(d) {
      button.textContent=d.target?'点击关门':'点击开门';
      button.setAttribute('aria-label',d.name+' · '+button.textContent);
      button.setAttribute('aria-expanded',String(!!d.target));
    }
  }
  button.addEventListener('click',toggle);
  return {tick,toggle,dispose(){button.removeEventListener('click',toggle);for(const [g,index] of original)g.setIndex(index);allWings.forEach(w=>{w.traverse(o=>{if(o.isMesh)o.geometry.dispose();});w.removeFromParent();});},get wings(){return nearby()?.wings??[];},
    blocked:(x,z,eye,r)=>doors.some(d=>overlaps(d,x,z,eye,r,d.fraction))};
}
