/**
 * 删掉导览牌（SITE_GUIDE）后面的两根斜撑。
 *
 * 背景：导览牌的立柱和斜撑合并在同一个 mesh 里（4 个 12 面连通块：
 * 两根立柱 + 两根斜撑），所以不能靠隐藏节点名来去掉，只能改索引缓冲。
 * 这里按「连通块的包围盒 z 向跨度 > 0.3」挑出两根斜撑（立柱是 0.1 见方，
 * 斜撑因为绕 X 轴转了 24° 才有 0.5 的进深），把它们的三角形从索引里剔除。
 *
 * 用法：node scripts/strip_guide_braces.js <输入.glb> <输出.glb>
 */
const fs = require('fs');

const GLB_MAGIC = 0x46546c67;
const CHUNK_JSON = 0x4e4f534a;
const CHUNK_BIN = 0x004e4942;

function parseGlb(file) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== GLB_MAGIC) throw new Error('不是 GLB 文件');
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
  const jsonHeader = Buffer.alloc(8);
  jsonHeader.writeUInt32LE(jsonChunk.length, 0);
  jsonHeader.writeUInt32LE(CHUNK_JSON, 4);
  const binHeader = Buffer.alloc(8);
  binHeader.writeUInt32LE(binChunk.length, 0);
  binHeader.writeUInt32LE(CHUNK_BIN, 4);
  fs.writeFileSync(file, Buffer.concat([header, jsonHeader, jsonChunk, binHeader, binChunk]));
}

function accReader(json, bin) {
  return (index) => {
    const a = json.accessors[index];
    const view = json.bufferViews[a.bufferView];
    const offset = (view.byteOffset || 0) + (a.byteOffset || 0);
    const count = a.count;
    if (a.componentType === 5126) {
      const out = new Float64Array(count * 3);
      for (let k = 0; k < count * 3; k += 1) out[k] = bin.readFloatLE(offset + k * 4);
      return out;
    }
    if (a.componentType === 5123) {
      const out = new Uint32Array(count);
      for (let k = 0; k < count; k += 1) out[k] = bin.readUInt16LE(offset + k * 2);
      return out;
    }
    if (a.componentType === 5125) {
      const out = new Uint32Array(count);
      for (let k = 0; k < count; k += 1) out[k] = bin.readUInt32LE(offset + k * 4);
      return out;
    }
    throw new Error('不支持的组件类型 ' + a.componentType);
  };
}

function main() {
  const [, , inFile, outFile] = process.argv;
  if (!inFile || !outFile) throw new Error('用法: node strip_guide_braces.js <in.glb> <out.glb>');
  const { json, bin } = parseGlb(inFile);
  const read = accReader(json, bin);

  const nodeIndex = json.nodes.findIndex((n) => n.name === 'SITE_GUIDE');
  if (nodeIndex < 0) throw new Error('找不到 SITE_GUIDE 节点');
  const mesh = json.meshes[json.nodes[nodeIndex].mesh];
  const prim = mesh.primitives[0];
  const positions = read(prim.attributes.POSITION);
  const indices = read(prim.indices);
  const vertexCount = json.accessors[prim.attributes.POSITION].count;
  const triCount = indices.length / 3;

  // 顶点焊接（导出时法线拆分会产生重复点），再按三角形连通性分组
  const weldKey = (i) =>
    [positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]].map((v) => Math.round(v * 1e4)).join(',');
  const weldMap = new Map();
  const weld = new Int32Array(vertexCount);
  for (let i = 0; i < vertexCount; i += 1) {
    const key = weldKey(i);
    if (!weldMap.has(key)) weldMap.set(key, weldMap.size);
    weld[i] = weldMap.get(key);
  }
  const parent = new Int32Array(weldMap.size).map((_, i) => i);
  const find = (x) => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  };
  const union = (a, b) => {
    const ra = find(a);
    const rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  };
  for (let t = 0; t < indices.length; t += 3) {
    union(weld[indices[t]], weld[indices[t + 1]]);
    union(weld[indices[t]], weld[indices[t + 2]]);
  }

  const groups = new Map();
  for (let t = 0; t < triCount; t += 1) {
    const root = find(weld[indices[t * 3]]);
    if (!groups.has(root)) groups.set(root, []);
    groups.get(root).push(t);
  }

  // 斜撑特征：连通块包围盒 z 向跨度 > 0.3（立柱只有 0.1）
  const drop = new Set();
  const report = [];
  for (const [root, tris] of groups) {
    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const t of tris) {
      for (let k = 0; k < 3; k += 1) {
        const vi = indices[t * 3 + k];
        for (let c = 0; c < 3; c += 1) {
          const v = positions[vi * 3 + c];
          if (v < min[c]) min[c] = v;
          if (v > max[c]) max[c] = v;
        }
      }
    }
    const size = max.map((v, i) => v - min[i]);
    const center = max.map((v, i) => (v + min[i]) / 2);
    const isBrace = size[2] > 0.3 && size[1] > 0.5;
    report.push({ tris: tris.length, size: size.map((v) => +v.toFixed(3)), center: center.map((v) => +v.toFixed(3)), drop: isBrace });
    if (isBrace) tris.forEach((t) => drop.add(t));
  }

  if (!drop.size) throw new Error('没有找到斜撑连通块，未做修改');

  const kept = [];
  for (let t = 0; t < triCount; t += 1) {
    if (drop.has(t)) continue;
    kept.push(indices[t * 3], indices[t * 3 + 1], indices[t * 3 + 2]);
  }

  // 新的索引缓冲：追加 bufferView + accessor，指向同一份 BIN
  const indexBytes = Buffer.alloc(kept.length * 2);
  kept.forEach((v, i) => indexBytes.writeUInt16LE(v, i * 2));
  const binPad = (4 - (bin.length % 4)) % 4;
  const binWithPad = Buffer.concat([bin, Buffer.alloc(binPad, 0)]);
  const newView = {
    buffer: 0,
    byteOffset: binWithPad.length,
    byteLength: indexBytes.length,
    target: 34963,
  };
  json.bufferViews.push(newView);
  const newAccessor = {
    bufferView: json.bufferViews.length - 1,
    componentType: 5123,
    count: kept.length,
    type: 'SCALAR',
    min: [Math.min(...kept)],
    max: [Math.max(...kept)],
  };
  json.accessors.push(newAccessor);
  prim.indices = json.accessors.length - 1;
  json.buffers[0].byteLength = binWithPad.length + indexBytes.length;

  writeGlb(outFile, json, Buffer.concat([binWithPad, indexBytes]));

  console.log(
    JSON.stringify(
      {
        节点: 'SITE_GUIDE',
        原三角形: triCount,
        删除三角形: drop.size,
        剩余三角形: triCount - drop.size,
        连通块: report,
        输出: outFile,
      },
      null,
      2
    )
  );
}

main();