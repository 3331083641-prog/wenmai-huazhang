/**
 * 绾硅剦灞曢 路 妯″瀷鍔犺浇涓庡浘灞傛帶鍒? *
 * 妯″瀷鏉ヨ嚜 Blender锛歚assets/gallery3d/exports/wenmai_gallery.glb`
 * 锛堟瀯寤鸿剼鏈?`assets/gallery3d/scripts/build_all.py`锛屽鍑哄悗澶嶅埗鍒?public/models锛夈€? *
 * 杩欓噷鍙仛鍥涗欢浜嬶細
 *  1. 鍔犺浇 GLB 骞跺厠闅嗕竴浠斤紙drei 鐨勭紦瀛樻槸鍏变韩鐨勶紝鐩存帴娓叉煋浼氭薄鏌撲笅娆℃寕杞斤級锛? *  2. 鍓ユ帀 GLB 閲屽甫杩涙潵鐨勭浉鏈鸿妭鐐癸紝閬垮厤瀹冧滑鍙備笌灏勭嚎/鍖呭洿鐩掕绠楋紱
 *  3. 浜ょ粰涓夋覆浜屾ā鍧楅噸鍐欐潗璐ㄤ笌鎻忚竟锛? *  4. 鎸夊浘灞傚垎缁勶紝渚涖€屽瑙?/ 鍐呴儴銆嶆ā寮忔樉闅愬眿椤躲€? *
 * 鍧愭爣銆佸睍澧欍€佺敾妗嗛敋鐐归兘涓嶅湪杩欓噷璇?GLB锛岃€屾槸璇荤敱 Blender 鐩存帴瀵煎嚭鐨? * `gallery_layout.json`鈥斺€斿崟涓€鏁版嵁婧愶紝閬垮厤缃戦〉鍜屾ā鍨嬪悇鍐欎竴濂楀潗鏍囥€? */

import { useMemo } from 'react';
import { useGLTF } from '@react-three/drei';
import * as THREE from 'three';

import { applySanzhuan2, disposeToonResources, getOutlineMesh } from './sanzhuan2';

// The V5 GLB already carries authored PBR colours. The legacy toon pass
// overwrote them with a near-white ramp and washed the whole hall out, so it is
// switched off until it ramps the GLB base colour instead of replacing it.
const TOON_ENABLED = false;

export const MODEL_URL = '/models/wenmai_gallery_v5.glb?v=5w';

/** 灞嬮《鍥惧眰锛氬唴閮ㄦā寮忎笅涓€寰嬮殣钘忥紝鎵嶈兘鐪嬭繘灞嬮噷銆? *  浠?Blender 瀵煎嚭鐨勫懡鍚嶅墠缂€涓哄噯锛圧OOF_* 灞嬫灦 / TILE_* 鐡﹂潰锛夛紝
 *  澶栧姞鎸傚湪妾愪笅鐨勭伅绗尖€斺€斿畠璺熺潃灞嬮《涓€璧锋敹锛屽惁鍒欎細鎮湪鍗婄┖銆?*/
const ROOF_PREFIXES = ['ROOF_', 'TILE_'];
const ROOF_EXTRA = new Set(['LANTERN_Eave']);

function isRoofPart(name: string): boolean {
  if (ROOF_EXTRA.has(name)) return true;
  return ROOF_PREFIXES.some((prefix) => name.startsWith(prefix));
}

/** 骞曟爣銆佺伅绗肩瓑鎸傚湪灞嬪鐨勮楗帮紝鍐呴儴妯″紡淇濈暀锛堢伅绗兼槸瀹ゅ唴鍏夋簮锛?*/
const CAMERA_PREFIX = 'CAM_';

export interface GalleryLayers {
  /** 灞嬮《鐩稿叧缃戞牸锛屽唴閮ㄦā寮忛殣钘?*/
  roof: THREE.Object3D[];
  /** 灞嬮《缃戞牸鐨勫ⅷ绾胯疆寤擄紝鐩告満杩涘叆瀹ゅ唴鍚庤闅愯棌锛堣儗闈㈠鎺ㄥ３浠庡唴渚х湅鏄粦鏉匡級 */
  roofOutlines: THREE.Mesh[];
  /** 鍏ㄩ儴鍙覆鏌撶綉鏍硷紝鐢ㄤ簬缁熻鍜岃皟璇?*/
  meshes: THREE.Mesh[];
}

export interface GalleryAssets {
  root: THREE.Group;
  layers: GalleryLayers;
  stats: { meshes: number; materials: number; triangles: number };
}

function prepare(source: THREE.Group): GalleryAssets {
  const root = source.clone(true);
  const roof: THREE.Object3D[] = [];
  const meshes: THREE.Mesh[] = [];
  const cameras: THREE.Object3D[] = [];

  root.traverse((object) => {
    if ((object as THREE.Camera).isCamera || object.name.startsWith(CAMERA_PREFIX)) {
      cameras.push(object);
      return;
    }
    if (!(object as THREE.Mesh).isMesh) return;
    const mesh = object as THREE.Mesh;
    meshes.push(mesh);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    // 鎻忚竟涓庨槾褰遍兘鐢ㄤ笉鍒拌閿ヨ鍓互澶栫殑鎶€宸э紝淇濈暀榛樿
    if (isRoofPart(mesh.name)) roof.push(mesh);
  });

  // 鐩告満鑺傜偣鍙槸 Blender 鐨勫伐浣滃弬鑰冿紝缃戦〉閲岀敤甯冨眬 JSON 鐨勬満浣?  for (const camera of cameras) camera.removeFromParent();

  const result = TOON_ENABLED ? applySanzhuan2(root) : { materials: 0 };

  const roofOutlines = roof
    .map((object) => getOutlineMesh(object as THREE.Mesh))
    .filter((mesh): mesh is THREE.Mesh => Boolean(mesh));

  let triangles = 0;
  for (const mesh of meshes) {
    const geometry = mesh.geometry as THREE.BufferGeometry;
    const index = geometry.getIndex();
    const position = geometry.getAttribute('position');
    if (index) triangles += index.count / 3;
    else if (position) triangles += position.count / 3;
  }

  return {
    root,
    layers: { roof, roofOutlines, meshes },
    stats: { meshes: meshes.length, materials: result.materials, triangles: Math.round(triangles) },
  };
}

/** 鍔犺浇骞跺噯澶囧ソ灞曢妯″瀷锛涙暟鎹彧鍦ㄩ娆℃寕杞芥椂鏋勫缓涓€娆?*/
export function useGalleryAssets(): GalleryAssets {
  const gltf = useGLTF(MODEL_URL);
  return useMemo(() => prepare(gltf.scene as THREE.Group), [gltf.scene]);
}

/** 鍗歌浇鏃堕噴鏀句笁娓蹭簩妯″潡閲岀紦瀛樼殑鏉愯川涓庢笎鍙樿创鍥?*/
export function releaseGalleryAssets(): void {
  disposeToonResources();
}

useGLTF.preload(MODEL_URL);
