import * as THREE from 'three';
export function makeWaterNormal() {
  const s = 256;
  const c = document.createElement('canvas');
  c.width = s; c.height = s;
  const g = c.getContext('2d');
  const img = g.createImageData(s, s);
  for (let y = 0; y < s; y++) {
    for (let x = 0; x < s; x++) {
      const nx = Math.sin(x * 0.10 + Math.sin(y * 0.045) * 2.0) * 16 + Math.cos(y * 0.07) * 8;
      const ny = Math.cos(y * 0.11 + Math.sin(x * 0.05) * 1.8) * 16 + Math.sin(x * 0.06) * 8;
      const i = (y * s + x) * 4;
      img.data[i] = 128 + nx;
      img.data[i + 1] = 128 + ny;
      img.data[i + 2] = 255;
      img.data[i + 3] = 255;
    }
  }
  g.putImageData(img, 0, 0);
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(14, 14);
  tex.colorSpace = THREE.NoColorSpace;
  return tex;
}


export function buildCollision(root){
const floorMeshes=[],waterMeshes=[];let blockMeshes=[];const collisionCells=new Map(),collisionFallback={floor:[],wall:[]},CELL_SIZE=4;
function collectFloors(root) {
  const floorNames = new Set(['stone_lite', 'stone_dark', 'wood_lite', 'wood_dark', 'brick', 'pond', 'silk', 'stone', 'wood']);
  root.traverse((o) => {
    if (!o.isMesh || o.userData.movingDoor) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    const names = mats.map((m) => String(m?.name || '').toLowerCase());
    if (names.some((n) => floorNames.has(n)) && !waterMeshes.includes(o)) floorMeshes.push(o);
  });
  if (!floorMeshes.length) {
    root.traverse((o) => {
      if (!o.isMesh) return;
      if (waterMeshes.includes(o)) return;
      if (/(roof|foliage|water)/i.test(o.name)) return;
      floorMeshes.push(o);
    });
  }
  /* 墙、窗、屋面和地坪使用双面碰撞网格；活动门单独随铰链检测。 */
  blockMeshes = floorMeshes.filter((o) => !waterMeshes.includes(o));
  root.traverse((o) => {
    if (!o.isMesh || o.userData.movingDoor || blockMeshes.includes(o)) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    if (mats.some((m) => /wall|glass|roof/i.test(String(m?.name || '')))) blockMeshes.push(o);
  });
  root.updateMatrixWorld(true);
  buildCollisionCells();
  console.info('[文脉] 地面网格数', floorMeshes.length, '水面网格数', waterMeshes.length);
}

// 按世界 XZ 切分静态碰撞用索引；渲染仍使用完整模型。跨格三角形写入每个覆盖格。
function buildCollisionCells() {
  const floorSet = new Set(floorMeshes);
  const collisionMaterial=new THREE.MeshBasicMaterial({side:THREE.DoubleSide});
  for (const mesh of blockMeshes) {
    const isFloor = floorSet.has(mesh);
    const g = mesh.geometry, pos = g.getAttribute('position');
    if (!pos || mesh.isSkinnedMesh || mesh.isInstancedMesh || g.morphAttributes.position ||
        Array.isArray(mesh.material) || !mesh.visible) {
      collisionFallback.wall.push(mesh);
      if (isFloor) collisionFallback.floor.push(mesh);
      continue;
    }
    const gx = new Int32Array(pos.count), gz = new Int32Array(pos.count);
    const world = mesh.matrixWorld.elements;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      gx[i] = Math.floor((world[0]*x + world[4]*y + world[8]*z + world[12]) / CELL_SIZE);
      gz[i] = Math.floor((world[2]*x + world[6]*y + world[10]*z + world[14]) / CELL_SIZE);
    }
    const bins = new Map(), index = g.index;
    const end = Math.min(index ? index.count : pos.count, g.drawRange.start + g.drawRange.count);
    for (let i = g.drawRange.start; i + 2 < end; i += 3) {
      const a = index ? index.getX(i) : i;
      const b = index ? index.getX(i+1) : i+1;
      const c = index ? index.getX(i+2) : i+2;
      // Above the highest walkable storey plus jump/head clearance there is
      // no player traffic. Keep high roof tiles out of the collision index.
      if (pos.getY(a)>7.8 && pos.getY(b)>7.8 && pos.getY(c)>7.8) continue;
      const maxX = Math.max(gx[a],gx[b],gx[c]), maxZ = Math.max(gz[a],gz[b],gz[c]);
      for (let ix = Math.min(gx[a],gx[b],gx[c]); ix <= maxX; ix++) {
        for (let iz = Math.min(gz[a],gz[b],gz[c]); iz <= maxZ; iz++) {
          const key = ix + ',' + iz;
          let indices = bins.get(key);
          if (!indices) bins.set(key, indices = []);
          indices.push(a,b,c);
        }
      }
    }
    if (!g.boundingSphere) g.computeBoundingSphere();
    for (const [key, indices] of bins) {
      const subset = new THREE.BufferGeometry();
      subset.setAttribute('position', pos);
      subset.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1));
      subset.boundingSphere = g.boundingSphere;
      subset.boundingBox = g.boundingBox;
      const proxy = new THREE.Mesh(subset, collisionMaterial);
      proxy.name=mesh.name;
      proxy.matrixWorld.copy(mesh.matrixWorld);
      let bin = collisionCells.get(key);
      if (!bin) collisionCells.set(key, bin = { floor: [], wall: [] });
      bin.wall.push(proxy);
      if (isFloor) bin.floor.push(proxy);
    }
  }
}

function nearbyMeshes(type, x0, z0, x1=x0, z1=z0) {
  const found = collisionFallback[type].slice();
  const maxX = Math.floor(Math.max(x0,x1)/CELL_SIZE), maxZ = Math.floor(Math.max(z0,z1)/CELL_SIZE);
  for (let x = Math.floor(Math.min(x0,x1)/CELL_SIZE); x <= maxX; x++) {
    for (let z = Math.floor(Math.min(z0,z1)/CELL_SIZE); z <= maxZ; z++) {
      const bucket = collisionCells.get(x + ',' + z);
      if (bucket) found.push(...bucket[type]);
    }
  }
  return found;
}


collectFloors(root);return {nearby:nearbyMeshes,dispose(){const materials=new Set();for(const bin of collisionCells.values())for(const m of bin.wall){m.geometry.dispose();materials.add(m.material);}materials.forEach(m=>m.dispose());collisionCells.clear();}};
}