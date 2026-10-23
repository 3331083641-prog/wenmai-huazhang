/**
 * 展馆 GLB 的小手术：按名字删网格、按轴收缩一块楼板。
 *
 * 场景：二层楼梯口在模型里被「x 0.56–2.0 / z 2.86–4.14」这一条楼板压住，
 * 楼梯下半跑从这条楼板底下钻过去，站在二层看过去只有一个围栏、看不到楼梯，
 * 视觉上像楼梯不通。这里把这条楼板收到靠后墙的 0.35 m 窄条（保住后墙落脚），
 * 同时把井口两侧的栏杆删掉，井口由前端补一段新栏杆。
 *
 * 用法：
 *   node scripts/gallery_edit.js delete <in.glb> <out.glb> NAME1 NAME2 ...
 *   node scripts/gallery_edit.js shrink <in.glb> <out.glb> NAME axis(min|max) value
 */
const fs = require('fs');

const GLB_MAGIC = 0x46546c67;
const CHUNK_JSON = 0x4e4f534a;
const CHUNK_BIN = 0x004e4942;

function parseGlb(file) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== GLB_MAGIC) throw new Error('不是 GLB');
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
  const [, , mode, inFile, outFile, ...rest] = process.argv;
  const { json, bin } = parseGlb(inFile);
  const removed = [];
  const changed = [];

  if (mode === 'delete') {
    const names = new Set(rest);
    for (const node of json.nodes) {
      if (node.name && names.has(node.name) && node.mesh !== undefined) {
        delete node.mesh;
        removed.push(node.name);
      }
    }
  } else if (mode === 'shrink') {
    const [name, axis, which, valueRaw] = rest;
    const value = Number(valueRaw);
    const node = json.nodes.find((n) => n.name === name);
    if (!node || node.mesh === undefined) throw new Error('找不到节点 ' + name);
    const prim = json.meshes[node.mesh].primitives[0];
    const accessor = json.accessors[prim.attributes.POSITION];
    const view = json.bufferViews[accessor.bufferView];
    const stride = view.byteStride || 12;
    const base = (view.byteOffset || 0) + (accessor.byteOffset || 0);
    const comp = axis === 'x' ? 0 : axis === 'y' ? 1 : 2;
    const offset = node.translation ? node.translation[comp] : 0;
    const target = value - offset; // 传世界坐标，换成节点局部
    const coords = [];
    for (let i = 0; i < accessor.count; i += 1) coords.push(bin.readFloatLE(base + i * stride + comp * 4));
    const extreme = which === 'min' ? Math.min(...coords) : Math.max(...coords);
    let moved = 0;
    for (let i = 0; i < accessor.count; i += 1) {
      if (Math.abs(coords[i] - extreme) < 1e-5) {
        bin.writeFloatLE(target, base + i * stride + comp * 4);
        moved += 1;
      }
    }
    accessor.min[comp] = Math.min(...coords.map((v) => (Math.abs(v - extreme) < 1e-5 ? target : v)));
    accessor.max[comp] = Math.max(...coords.map((v) => (Math.abs(v - extreme) < 1e-5 ? target : v)));
    changed.push({ name, moved, axis, which, from: extreme + offset, to: value });
  } else {
    throw new Error('未知模式 ' + mode);
  }

  writeGlb(outFile, json, bin);
  console.log(JSON.stringify({ mode, removed, changed }, null, 2));
}


main();