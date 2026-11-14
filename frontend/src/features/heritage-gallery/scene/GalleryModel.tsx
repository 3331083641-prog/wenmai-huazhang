import { useMemo } from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_URL = `${import.meta.env.BASE_URL}models/pavilion-v15/model.json`;
/** Independent gzip parts keep every authored byte while fitting repository file limits. */
class PavilionLoader extends THREE.Loader<GLTF> {
  load(url: string, onLoad: (gltf: GLTF) => void, _progress?: unknown, onError?: (e: unknown) => void) {
    (async () => {
      const absolute = new URL(url, window.location.href);
      const response = await fetch(absolute);
      if (!response.ok) throw new Error(`展馆清单加载失败：${response.status}`);
      const manifest = await response.json();
      const binary = new Uint8Array(manifest.bytes);
      let offset = 0;
      for (const part of manifest.parts) {
        const response = await fetch(new URL(part.url, absolute));
        if (!response.ok || !response.body) throw new Error(`展馆分包加载失败：${part.url}`);
        const bytes = new Uint8Array(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
        const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))).map(b => b.toString(16).padStart(2, '0')).join('');
        if (bytes.length !== part.bytes || hash !== part.sha256) throw new Error(`展馆分包校验失败：${part.url}`);
        binary.set(bytes, offset); offset += bytes.length;
      }
      if (offset !== manifest.bytes) throw new Error('展馆文件长度不符');
      return new GLTFLoader(this.manager).parseAsync(binary.buffer, absolute.href);
    })().then(onLoad, onError);
  }
}
export interface GalleryLayers { roof: THREE.Object3D[]; roofOutlines: THREE.Mesh[]; meshes: THREE.Mesh[] }
export interface GalleryAssets {root: THREE.Group; layers: GalleryLayers; stats: {meshes:number;materials:number;triangles:number;lookDevMaterials:number;lookDevTweaked:number}}
function prepare(scene: THREE.Group): GalleryAssets {
  const root = scene.clone(true), meshes: THREE.Mesh[] = [], roof: THREE.Object3D[] = [];
  const mats = new Map<THREE.Material, THREE.Material>(); let triangles = 0;
  const remove: THREE.Object3D[] = [];
  root.traverse(object => {
    if ((object as THREE.Light).isLight || (object as THREE.Camera).isCamera) {remove.push(object); return;}
    const mesh = object as THREE.Mesh; if (!mesh.isMesh) return;
    mesh.geometry = mesh.geometry.clone();
    const clone = (original: THREE.Material) => {
      if (mats.has(original)) return mats.get(original)!;
      const m = original.clone() as THREE.MeshStandardMaterial;
      if (m.aoMap) m.aoMapIntensity = .55;
      m.envMapIntensity = 1.15;
      if (/glass/.test(m.name)) {m.transparent=true;m.opacity=.45;m.depthWrite=false;m.roughness=.12;}
      if (/foliage/.test(m.name)) {m.side=THREE.DoubleSide;m.roughness=.82;}
      if (/roof/.test(m.name) && m.normalMap) m.normalScale.set(.55,.55);
      mats.set(original,m);return m;
    };
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(clone) : clone(mesh.material);
    mesh.castShadow = mesh.receiveShadow = true;
    const names = (Array.isArray(mesh.material) ? mesh.material : [mesh.material]).map(m=>m.name).join(' ');
    if (/water|SKY13|dome|cloud|skybox/i.test(names+' '+mesh.name)) {mesh.visible=false;mesh.raycast=()=>{};return;}
    if (/roof/.test(names)) roof.push(mesh);
    meshes.push(mesh);triangles += (mesh.geometry.index?.count ?? mesh.geometry.attributes.position.count)/3;
  });
  remove.forEach(o=>o.removeFromParent());root.updateMatrixWorld(true);
  return {root,layers:{roof,roofOutlines:[],meshes},stats:{meshes:meshes.length,materials:mats.size,triangles,lookDevMaterials:0,lookDevTweaked:0}};
}
export function useGalleryAssets(): GalleryAssets { const gltf=useLoader(PavilionLoader, MODEL_URL);return useMemo(()=>prepare(gltf.scene),[gltf.scene]); }
export function releaseGalleryAssets(_root: THREE.Object3D): void { /* Cached loader data is shared between route visits. */ }
