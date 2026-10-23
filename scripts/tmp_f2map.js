const fs = require('fs');
const b = fs.readFileSync('frontend/public/models/wenmai_gallery_v5.glb');
const jl = b.readUInt32LE(12);
const j = JSON.parse(b.subarray(20, 20 + jl).toString('utf8'));
const rects = [];
for (const node of j.nodes) {
  if (!/INT_F2_(SLAB|BOARD)/.test(node.name || '')) continue;
  const t = node.translation || [0, 0, 0];
  const a = j.accessors[j.meshes[node.mesh].primitives[0].attributes.POSITION];
  rects.push({
    name: node.name,
    x0: a.min[0] + t[0], x1: a.max[0] + t[0],
    z0: a.min[2] + t[2], z1: a.max[2] + t[2],
  });
}
const covered = (x, z) => rects.some(r => x > r.x0 + 1e-3 && x < r.x1 - 1e-3 && z > r.z0 + 1e-3 && z < r.z1 - 1e-3);
let out = '';
for (let z = 4.2; z >= -3.2; z -= 0.2) {
  let line = '';
  for (let x = -4.1; x <= 4.1; x += 0.2) line += covered(x, z) ? '#' : '.';
  out += 'z=' + z.toFixed(1).padStart(5) + ' ' + line + '\n';
}
console.log('x -4.1..4.1 step 0.2, #=有楼板 .=洞');
console.log(out);
console.log(rects.map(r=>r.name+' x['+r.x0.toFixed(2)+','+r.x1.toFixed(2)+'] z['+r.z0.toFixed(2)+','+r.z1.toFixed(2)+']').join('\n'));
