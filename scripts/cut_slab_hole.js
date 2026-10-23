/**
 * 在二层楼板（VER_Slab）上开一个楼梯井洞口。
 *
 * 背景：二层地面在 INT_F2_SLAB / INT_F2_BOARD 上确实留了洞，但外壳还有一块
 * VER_Slab（11.1 × 10.2 m 的整板，y≈3.52–3.60）横跨整个平面，把洞从下面又
 * 封了一块实心板——所以从二层看永远是一整片地面，楼梯成了「通了但看不见」。
 *
 * 做法：把这块板拆成围绕洞口的四块（左 / 右 / 前 / 后），洞口尺寸按楼梯井：
 * 世界坐标 x 0.56–4.04、z 1.76–4.14。
 *
 * 用法：node scripts/cut_slab_hole.js <in.glb> <out.glb>
 */
const fs = require('fs');

const GLB_MAGIC = 0x46546c67;
const CHUNK_JSON = 0x4e4f534a;
const CHUNK_BIN = 0x004e4942;

function parseGlb(file) {
  const buf = fs.readFileSync(file);
  const total = buf.readUInt32LE(8);
  let offset = 12;
  let json = null;
  let bin = null;
  while (offset < total) {
    const len = buf.readUInt32LE(offset);
    const type = buf.readUInt32LE(offset + 4);
    const data = buf.subarray(offset + 8, offset + 8 + len);
    if (type === CHUNK_JSON) json = JSON.parse(data.toString('utf8'));
    else if (type === CHUNK_BIN) bin = Buffer.from(data);
    offset += 8 + len + ((4 - (len % 4)) % 4);
  }
  return { json, bin };
}

function writeGlb(file, json, bin) {
  const jsonBuf = Buffer.from(JSON.stringify(json), 'utf8');
  const jsonPad = (4 - (jsonBuf.length % 4)) % 4;
  const jsonChunk = Buffer.concat([jsonBuf, Buffer.alloc(jsonPad, 0x20)]);
  const binPad = (4 - (bin.length % 4)) % 4;
  const binChunk = Buffer.concat([bin, Buffer.alloc(binPad, 0)]);
  const total = 12 + 8 + jsonChunk.length + 8 + binChunk.length;
  const header = Buffer.alloc(12);
  header.writeUInt32LE(GLB_MAGIC, 0);
  header.writeUInt32LE(2, 4);
  header.writeUInt32LE(total, 8);
  const jh = Buffer.alloc(8);
  jh.writeUInt32LE(jsonChunk.length, 0);
  jh.writeUInt32LE(CHUNK_JSON, 4);
  const bh = Buffer.alloc(8);
  bh.writeUInt32LE(binChunk.length, 0);
  bh.writeUInt32LE(CHUNK_BIN, 4);
  fs.writeFileSync(file, Buffer.concat([header, jh, jsonChunk, bh, binChunk]));
}

function main() {
  const [, , inFile, outFile] = process.argv;
  const { json, bin } = parseGlb(inFile);

  const nodeIndex = json.nodes.findIndex((n) => n.name === 'VER_Slab');
  if (nodeIndex < 0) throw new Error('找不到 VER_Slab');
  const node = json.nodes[nodeIndex];
  const mesh = json.meshes[node.mesh];
  const prim = mesh.primitives[0];
  const posAcc = json.accessors[prim.attributes.POSITION];
  const posView = json.bufferViews[posAcc.bufferView];
  const base = (posView.byteOffset || 0) + (posAcc.byteOffset || 0);
  const stride = posView.byteStride || 12;

  const positions = [];
  for (let i = 0; i < posAcc.count; i += 1) {
    positions.push([
      bin.readFloatLE(base + i * stride),
      bin.readFloatLE(base + i * stride + 4),
      bin.readFloatLE(base + i * stride + 8),
    ]);
  }
  const minX = Math.min(...positions.map((p) => p[0]));
  const maxX = Math.max(...positions.map((p) => p[0]));
  const minZ = Math.min(...positions.map((p) => p[2]));
  const maxZ = Math.max(...positions.map((p) => p[2]));

  // 洞口（节点局部坐标）：世界 x 0.56–4.04、z 1.76–4.14，减去节点平移
  const t = node.translation || [0, 0, 0];
  const hole = {
    x0: 0.56 - t[0],
    x1: 4.04 - t[0],
    z0: 1.76 - t[2],
    z1: 4.14 - t[2],
  };

  const rects = [
    { tag: 'A', x0: minX, x1: hole.x0, z0: minZ, z1: maxZ },
    { tag: 'B', x0: hole.x1, x1: maxX, z0: minZ, z1: maxZ },
    { tag: 'C', x0: hole.x0, x1: hole.x1, z0: minZ, z1: hole.z0 },
    { tag: 'D', x0: hole.x0, x1: hole.x1, z0: hole.z1, z1: maxZ },
  ];

  const newAccessors = [];
  const newViews = [];
  let cursor = bin.length;
  const newBytes = [];

  for (const rect of rects) {
    const data = Buffer.alloc(positions.length * 12);
    positions.forEach(([x, y, z], i) => {
      const nx = (x - minX) / (maxX - minX);
      const nz = (z - minZ) / (maxZ - minZ);
      data.writeFloatLE(rect.x0 + nx * (rect.x1 - rect.x0), i * 12);
      data.writeFloatLE(y, i * 12 + 4);
      data.writeFloatLE(rect.z0 + nz * (rect.z1 - rect.z0), i * 12 + 8);
    });
    const viewIndex = json.bufferViews.length;
    json.bufferViews.push({ buffer: 0, byteOffset: cursor, byteLength: data.length, target: 34962 });
    const accIndex = json.accessors.length;
    json.accessors.push({
      bufferView: viewIndex,
      componentType: 5126,
      count: positions.length,
      type: 'VEC3',
      min: [rect.x0, Math.min(...positions.map((p) => p[1])), rect.z0],
      max: [rect.x1, Math.max(...positions.map((p) => p[1])), rect.z1],
    });
    newAccessors.push(accIndex);
    newViews.push({ viewIndex, byteOffset: cursor, byteLength: data.length });
    newBytes.push(data);
    cursor += data.length;
  }

  const combined = Buffer.concat([bin, ...newBytes]);
  json.buffers[0].byteLength = combined.length;

  // 用四个片段替换原板
  for (let i = 0; i < rects.length; i += 1) {
    const newMeshIndex = json.meshes.length;
    json.meshes.push({
      name: 'VER_Slab_' + rects[i].tag,
      primitives: [
        {
          attributes: { ...prim.attributes, POSITION: newAccessors[i] },
          indices: prim.indices,
          material: prim.material,
          mode: prim.mode,
        },
      ],
    });
    json.nodes.push({
      name: 'VER_Slab_' + rects[i].tag,
      mesh: newMeshIndex,
      translation: node.translation,
      rotation: node.rotation,
      scale: node.scale,
    });
  }
  delete node.mesh; // 原整板不再渲染

  writeGlb(outFile, json, combined);
  console.log(
    JSON.stringify(
      {
        洞口: { x: [0.56, 4.04], z: [1.76, 4.14] },
        替换为: rects.map((r) => ({ tag: r.tag, x: [r.x0 + t[0], r.x1 + t[0]], z: [r.z0 + t[2], r.z1 + t[2]] })),
        输出: outFile,
      },
      null,
      2
    )
  );
}

main();