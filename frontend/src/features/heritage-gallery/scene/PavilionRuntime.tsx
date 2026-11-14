import { useEffect, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { mountDoor } from './pavilion/pavilion-door.js';
import { createWalker } from './pavilion/roam.js';
import { makePools } from './pavilion/pool-water.js';
import { buildCollision, makeWaterNormal } from './pavilion/collision.js';

/** Adapter only: geometry, stair support, door sweeps and swim physics come from D:/Design. */
export function PavilionRuntime({root,active}:{root:THREE.Group;active:boolean}) {
  const {camera,gl,scene}=useThree();
  const runtime=useRef<any>(null), activeRef=useRef(active);activeRef.current=active;
  useEffect(()=>{
    const button=document.createElement('button');button.hidden=true;button.dataset.testid='pavilion-door';
    button.style.cssText='position:absolute;bottom:110px;left:50%;transform:translateX(-50%);z-index:40;padding:12px 24px;background:#913221;color:#fff;border:1px solid #e1bd80;border-radius:24px;cursor:pointer';
    const hint=document.createElement('div');hint.dataset.testid='pavilion-roam-help';
    hint.style.cssText='position:absolute;top:75px;left:50%;transform:translateX(-50%);z-index:5;max-width:70%;text-align:center;padding:8px 14px;background:#fff9e9dc;color:#394953;border-radius:16px;font:12px sans-serif;pointer-events:none';
    gl.domElement.parentElement!.append(button,hint);
    const state={mode:activeRef.current?'roam':'overview',tween:null};
    let message='',until=0,yaw=-Math.PI/2,pitch=0,drag=false;
    const tell=(text:string)=>{message=text;until=performance.now()+2200;};
    const doors=mountDoor(root,button,camera,state,gl.shadowMap,tell);
    const collision=buildCollision(root),keys:Record<string,boolean>={};
    const bounds={x0:-40,x1:40,z0:-48,z1:48};
    const walker=createWalker(camera,keys,collision.nearby,doors,()=>0,()=>bounds);
    const water=makePools(scene,gl,makeWaterNormal());
    const look=()=>camera.lookAt(camera.position.clone().add(new THREE.Vector3(Math.cos(yaw)*Math.cos(pitch),Math.sin(pitch),Math.sin(yaw)*Math.cos(pitch))));
    function enter(){camera.position.set(0,2.05,6);(camera as THREE.PerspectiveCamera).fov=65;(camera as THREE.PerspectiveCamera).updateProjectionMatrix();yaw=-Math.PI/2;pitch=0;walker.reset();look();}
    const aliases:Record<string,string>={ArrowUp:'KeyW',ArrowDown:'KeyS',ArrowLeft:'KeyA',ArrowRight:'KeyD'};
    const key=(e:KeyboardEvent,down:boolean)=>{
      if(!activeRef.current || /INPUT|TEXTAREA|SELECT/.test((e.target as HTMLElement)?.tagName))return;
      const code=aliases[e.code]??e.code;
      if(['KeyW','KeyA','KeyS','KeyD','Space','KeyC','ControlLeft','ControlRight','ShiftLeft','ShiftRight','KeyE'].includes(code))e.preventDefault();
      keys[code]=down;
      if(down&&!e.repeat&&code==='Space')walker.requestJump();
      if(down&&!e.repeat&&code==='KeyE')doors.toggle();
    };
    const down=(e:KeyboardEvent)=>key(e,true),up=(e:KeyboardEvent)=>key(e,false);
    const clear=()=>{Object.keys(keys).forEach(k=>delete keys[k]);drag=false;};
    const pointerDown=(e:PointerEvent)=>{if(activeRef.current && e.button===0){drag=true;gl.domElement.setPointerCapture(e.pointerId);}};
    const pointerUp=()=>{drag=false;};
    const pointerMove=(e:PointerEvent)=>{if(!activeRef.current||!drag)return;yaw+=e.movementX*.003;pitch=THREE.MathUtils.clamp(pitch-e.movementY*.003,-1.3,1.3);look();};
    window.addEventListener('keydown',down);window.addEventListener('keyup',up);window.addEventListener('blur',clear);
    gl.domElement.addEventListener('pointerdown',pointerDown);gl.domElement.addEventListener('pointerup',pointerUp);gl.domElement.addEventListener('pointermove',pointerMove);
    runtime.current={state,walker,doors,water,enter,clear,keys,look,step:(dt:number)=>{walker.tick(dt,yaw);doors.tick(dt);},updateHint:()=>{hint.hidden=!activeRef.current;hint.textContent=performance.now()<until?message:walker.swimming?'WASD 游动 · 空格上浮 · C / Ctrl 下潜 · 岸边空格前进上岸':'按住拖动环顾 · WASD 行走 · Shift 疾行 · 空格跳跃 · 靠近门点击开关 / E';}};
    if(activeRef.current)enter();
    if(import.meta.env.DEV)(window as any).__pavilion={camera,scene,root,walker,doors,keys,aim:(a:number)=>{yaw=a;pitch=0;look();},step:runtime.current.step,place:(x:number,y:number,z:number,a=-Math.PI/2)=>{camera.position.set(x,y,z);yaw=a;pitch=0;walker.reset();look();}};
    return ()=>{
      window.removeEventListener('keydown',down);window.removeEventListener('keyup',up);window.removeEventListener('blur',clear);
      gl.domElement.removeEventListener('pointerdown',pointerDown);gl.domElement.removeEventListener('pointerup',pointerUp);gl.domElement.removeEventListener('pointermove',pointerMove);
      doors.dispose();water.dispose();collision.dispose();button.remove();hint.remove();runtime.current=null;
      if(import.meta.env.DEV)delete (window as any).__pavilion;
    };
  },[root,camera,gl,scene]);
  useEffect(()=>{const r=runtime.current;if(!r)return;r.state.mode=active?'roam':'overview';r.clear();if(active)r.enter();},[active]);
  useFrame(({clock},delta)=>{const r=runtime.current;if(!r)return;const dt=Math.min(delta,.05);if(active)r.walker.tick(dt,( ()=>{const d=new THREE.Vector3();camera.getWorldDirection(d);return Math.atan2(d.z,d.x);})());r.doors.tick(dt);r.water.tick(clock.elapsedTime,camera,active&&r.walker.swimming);r.updateHint();});
  return null;
}
