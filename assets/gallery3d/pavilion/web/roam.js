import * as THREE from 'three';
import {poolAt} from './pool-water.js';

const eye=1.65, radius=.27, step=.26;
const up=new THREE.Vector3(0,1,0),down=new THREE.Vector3(0,-1,0);
const ray=new THREE.Raycaster(), origin=new THREE.Vector3(), dir=new THREE.Vector3();
const offsets=[[0,0],[radius,0],[-radius,0],[0,radius],[0,-radius]];
// Main pavilion's exterior envelope. The front jamb faces bound the
// animated opening; the 4.2 m opening in the north wall leads to the garden.
const hallWalls=[
  [-13,-2.52,-.16,.16],[2.52,13,-.16,.16],
  [-13,-2.10,-18.16,-17.84],[2.10,13,-18.16,-17.84],
  [-13.16,-12.84,-18,0],[12.84,13.16,-18,0]
];

// Walking surface joins the leading edges of the 0.30 m treads. Only
// inward-facing risers are traversable; stringer sides and rails still block.
function stairRun(x,z) {
  const side=Math.sign(x), u=(z-12)*side, v=x*side-32;
  if(u< -2.405 || u>.905) return;
  const lower=v>=3.19 && v<=4.31, upper=v>=4.34 && v<=5.46;
  if(!lower && !upper) return;
  const t=THREE.MathUtils.clamp((lower?.90-u:u+2.40)/.30,0,10);
  return {height:(lower?.20:2.23)+(t+1)*(4.06/22),base:lower?.20:2.23};
}

export function createWalker(camera,keys,nearby,door,regionFloor,limit) {
  const p=camera.position;
  let vy=0,grounded=false,swimming=false,jump=false;
  function vertical(x,z,y,direction,reach,kind) {
    ray.set(origin.set(x,y,z),direction);
    ray.far=reach;
    for(const hit of ray.intersectObjects(nearby(kind,x,z),false)) {
      if(hit.face.normal.y * -direction.y>.5) return hit.point.y;
    }
    return null;
  }
  function ground(x,z,feet) {
    const surface=vertical(x,z,feet+step+.015,down,20,'floor');
    const run=stairRun(x,z);
    if(run && run.height<=feet+step+.02 && feet>=run.base-step && (surface===null || surface<=run.height+.01))
      return run.height;
    return surface ?? (poolAt(x,z)?.bed ?? regionFloor(x,z));
  }
  function blocked(x,z,nx,nz,swim) {
    if(door.blocked(nx,nz,p.y,radius)) return true;
    if(p.y>.30 && p.y-eye<8.8 && hallWalls.some(([x0,x1,z0,z1])=>
      Math.hypot(Math.max(x0-nx,0,nx-x1),Math.max(z0-nz,0,nz-z1))<radius)) return true;
    const dx=nx-x,dz=nz-z,len=Math.hypot(dx,dz);
    if(len<1e-7) return false;
    dir.set(dx/len,0,dz/len);
    const reach=len+radius;
    const candidates=nearby('wall',Math.min(x,nx)-radius,Math.min(z,nz)-radius,
                            Math.max(x,nx)+radius,Math.max(z,nz)+radius);
    // The capsule can approach the second riser before its centre reaches
    // the first tread. Sweep from the support height under its leading edge.
    const feet=p.y-eye;
    const leading=grounded && !swim ? ground(nx+dir.x*radius,nz+dir.z*radius,feet) : feet;
    const stepUp=THREE.MathUtils.clamp(leading-feet,0,step);
    const levels=swim ? [-.25,.05] : [-eye+step+.045+stepUp,-.71,.055];
    for(const h of levels) {
      for(const side of [0,-1,1]) {
        const shift=side*radius*.82;
        ray.set(origin.set(x-dir.z*shift,p.y+h,z+dir.x*shift),dir);
        ray.far=side ? len+radius*.56 : reach;
        for(const hit of ray.intersectObjects(candidates,false)) {
          if(Math.abs(hit.face.normal.y)>=.78) continue;
          if(grounded && hit.object.name==='MESH_stone_lite' && Math.abs(hit.face.normal.z)>.99) {
            const run=stairRun(hit.point.x,hit.point.z);
            if(run && feet>=run.base-step && Math.abs(run.height-feet)<.68 && hit.point.y<=run.height+.01) continue;
          }
          return true;
        }
      }
    }
    return false;
  }
  function moveAxis(dx,dz) {
    const x=p.x+dx,z=p.z+dz;
    const bounds=limit();
    if(bounds && (x<bounds.x0 || x>bounds.x1 || z<bounds.z0 || z>bounds.z1)) return;
    const pool=poolAt(p.x,p.z);
    if(swimming && pool && !poolAt(x+Math.sign(dx)*(radius+.05),z+Math.sign(dz)*(radius+.05))) {
      if(p.y<pool.surface+.04 || !keys.Space) return;
      // Climb the coping directly ahead, from the waterline. Check the
      // landing and headroom before committing the player's position.
      const tx=x+Math.sign(dx)*.80,tz=z+Math.sign(dz)*.80;
      if(poolAt(tx,tz)) return;
      const floor=ground(tx,tz,.10);
      if(floor<-.04 || floor>.28 || vertical(tx,tz,floor+.05,up,eye+.15,'wall')!==null) return;
      for(const h of [.42,1.1,eye]) {
        dir.set(tx-p.x,0,tz-p.z).normalize();
        ray.set(origin.set(p.x,floor+h,p.z),dir);
        ray.far=Math.hypot(tx-p.x,tz-p.z)+radius;
        if(ray.intersectObjects(nearby('wall',p.x,p.z,tx,tz),false).length) return;
      }
      p.set(tx,floor+eye,tz);
      vy=0;swimming=false;grounded=true;jump=false;return;
    }
    if(swimming && !poolAt(x,z)) return;
    if(!blocked(p.x,p.z,x,z,swimming)) {p.x=x;p.z=z;}
  }
  function tick(dt,yaw) {
    const pool=poolAt(p.x,p.z);
    swimming=!!pool && p.y<pool.surface+.90;
    let f=(keys.KeyW?1:0)-(keys.KeyS?1:0),s=(keys.KeyD?1:0)-(keys.KeyA?1:0);
    const len=Math.hypot(f,s);
    if(len) {
      const speed=swimming?1.8:(keys.ShiftLeft||keys.ShiftRight?5.9:2.9);
      const u=speed*dt/len;
      const dx=(f*Math.cos(yaw)-s*Math.sin(yaw))*u,dz=(f*Math.sin(yaw)+s*Math.cos(yaw))*u;
      if(dx) moveAxis(dx,0);
      if(dz) moveAxis(0,dz);
    }
    const basin=poolAt(p.x,p.z);
    swimming=!!basin && p.y<basin.surface+.90;
    if(swimming) {
      const dive=keys.KeyC||keys.ControlLeft||keys.ControlRight;
      const verticalSpeed=(keys.Space?1.35:0)-(dive?1.05:0);
      const floatHeight=basin.surface+.14;
      const target=verticalSpeed || THREE.MathUtils.clamp((floatHeight-p.y)*1.9,-1.3,.55);
      vy=THREE.MathUtils.damp(vy,target,5,dt);
      grounded=false;jump=false;
    } else {
      if(jump && grounded) {vy=5.35;grounded=false;}
      jump=false;
      vy=Math.max(-12,vy-12.8*dt);
    }
    let y=p.y+vy*dt;
    if(vy>0) {
      for(const [ox,oz] of offsets) {
        const cap=vertical(p.x+ox,p.z+oz,p.y+.075,up,vy*dt+.12,'wall');
        if(cap!==null) {y=Math.min(y,cap-.13);vy=0;break;}
      }
    }
    if(swimming) {
      const bed=ground(p.x,p.z,Math.min(basin.surface-.12,p.y));
      y=THREE.MathUtils.clamp(y,bed+.34,basin.surface+.17);
    } else {
      const feet=p.y-eye;
      const floor=ground(p.x,p.z,feet);
      if(basin && floor<basin.surface) {
        grounded=false;
      } else if(y<=floor+eye && vy<=0 && floor<=feet+step+.02) {
        y=floor+eye;vy=0;grounded=true;
      } else grounded=false;
    }
    p.y=y;
  }
  return {tick, get swimming(){return swimming;},requestJump(){jump=true;},
          reset(){vy=0;jump=grounded=swimming=false;}};
}
