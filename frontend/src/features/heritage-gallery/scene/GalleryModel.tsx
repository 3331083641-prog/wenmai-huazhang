import { useMemo } from 'react';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/addons/loaders/GLTFLoader.js';

const MODEL_URL = `${import.meta.env.BASE_URL}models/pavilion-v15/model.json`;
type PavilionModel = GLTF & { gatePlaque?: THREE.Group };

/** Independent gzip parts keep every authored byte while fitting repository file limits. */
class PavilionLoader extends THREE.Loader<PavilionModel> {
  load(url: string, onLoad: (gltf: PavilionModel) => void, _progress?: unknown, onError?: (e: unknown) => void) {
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
      const loader = new GLTFLoader(this.manager);
      const [model, gatePlaque] = await Promise.all([
        loader.parseAsync(binary.buffer, absolute.href),
        manifest.gatePlaque ? loader.loadAsync(new URL(manifest.gatePlaque, absolute).href) : undefined,
      ]);
      return { ...model, gatePlaque: gatePlaque?.scene };
    })().then(onLoad, onError);
  }
}
export interface GalleryLayers { roof: THREE.Object3D[]; roofOutlines: THREE.Mesh[]; meshes: THREE.Mesh[] }
export interface GalleryAssets {root: THREE.Group; layers: GalleryLayers; stats: {meshes:number;materials:number;triangles:number;lookDevMaterials:number;lookDevTweaked:number}}

function replaceGatePlaque(root: THREE.Group, replacement: THREE.Group) {
  const bronze = root.getObjectByName('MESH_bronze');
  const plaque = replacement.getObjectByName('gate_bianzi');
  if (!(bronze instanceof THREE.Mesh) || !(plaque instanceof THREE.Mesh) ||
      !(bronze.material instanceof THREE.MeshStandardMaterial)) {
    throw new Error('展馆门匾网格不完整');
  }

  // The v15 export combines all bronze geometry. Only the old lettering fits this local box.
  const box = new THREE.Box3(
    new THREE.Vector3(-1.12, 7.35, 46.151),
    new THREE.Vector3(1.12, 8.13, 46.176),
  );
  const geometry = bronze.geometry;
  const index = geometry.getIndex();
  const position = geometry.getAttribute('position');
  if (!index || !position) throw new Error('展馆门匾几何无效');
  const point = new THREE.Vector3();
  const kept = new Uint32Array(index.count);
  let keptCount = 0;
  for (let face = 0; face < index.count; face += 3) {
    const first = index.getX(face);
    const second = index.getX(face + 1);
    const third = index.getX(face + 2);
    if (box.containsPoint(point.fromBufferAttribute(position, first)) &&
        box.containsPoint(point.fromBufferAttribute(position, second)) &&
        box.containsPoint(point.fromBufferAttribute(position, third))) continue;
    kept[keptCount++] = first;
    kept[keptCount++] = second;
    kept[keptCount++] = third;
  }
  if (index.count - keptCount !== 860 * 3) throw new Error('展馆门匾字形数量不匹配');
  bronze.geometry = geometry.clone();
  bronze.geometry.setIndex(new THREE.BufferAttribute(kept.subarray(0, keptCount), 1));

  const lettering = plaque.clone();
  lettering.material = bronze.material.clone();
  // The door runtime reserves the name `bronze` for its merged structural mesh.
  lettering.material.name = 'gate_plaque_bronze';
  // The original AO texture is baked to the old lettering's UV layout.
  lettering.material.aoMap = null;
  bronze.add(lettering);
  return bronze;
}

function prepare(scene: THREE.Group, gatePlaque?: THREE.Group): GalleryAssets {
  const root = scene.clone(true), meshes: THREE.Mesh[] = [], roof: THREE.Object3D[] = [];
  const gateBronze = gatePlaque && replaceGatePlaque(root, gatePlaque);
  const mats = new Map<THREE.Material, THREE.Material>(); let triangles = 0;
  const remove: THREE.Object3D[] = [];
  root.traverse(object => {
    if ((object as THREE.Light).isLight || (object as THREE.Camera).isCamera) {remove.push(object); return;}
    const mesh = object as THREE.Mesh; if (!mesh.isMesh) return;
    if (mesh !== gateBronze) mesh.geometry = mesh.geometry.clone();
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
export function useGalleryAssets(): GalleryAssets {
  const { scene, gatePlaque } = useLoader(PavilionLoader, MODEL_URL);
  return useMemo(() => prepare(scene, gatePlaque), [scene, gatePlaque]);
}
export function releaseGalleryAssets(_root: THREE.Object3D): void { /* Cached loader data is shared between route visits. */ }
