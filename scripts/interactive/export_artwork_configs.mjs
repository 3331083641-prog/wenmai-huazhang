/**
 * 从 frontend/src/data/experiences/*.ts 抽出「热点几何」，写成画境构建器读的配置。
 *
 * 为什么要有这一步：热点坐标原本在 Python 构建器里手抄了一份，前端改了坐标、
 * 画境还是旧的，两边就悄悄错开。现在 TS 是唯一事实来源，这里只做搬运，
 * 构建器（build_painting_world.py）读导出结果，不再手写坐标。
 *
 * 用法：
 *   node scripts/interactive/export_artwork_configs.mjs
 *   node scripts/interactive/export_artwork_configs.mjs --check   # 只校验是否与 TS 一致
 *
 * 输出：scripts/interactive/artworks/<slug>.json
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '../..');
const outDir = resolve(here, 'artworks');

/** 每件作品的固定元信息（源图、标题、近景抠像候选）。热点几何不在这里写，从 TS 抽。 */
const ARTWORKS = [
  { slug: 'songhua', title: '云鹤临水楼', styleName: '宋画青绿山水',
    // 深度模型把鹤、云雾、楼阁和远山算成同一层；这三个值是逐点看画面定的人工校正，
    // 必须随配置一起导出，否则重跑导出会把它们洗掉（构建器会打印 warning 并退回夹取值）。
    hotspotDepthOverrides: { crane: 0.42, mist: 0.34, pavilion: 0.58 },
    cutouts: [{ id: 'pine', label: '松枝坡石', depth_min: 0.64,
      seed: { x: 0.15, y: 0.74 }, half: { w: 0.20, h: 0.24 } }] },
  { slug: 'zhuxianzhen', title: '瑞猫迎春', styleName: '朱仙镇木版年画',
    cutouts: [{ id: 'cat', label: '猫身与虎斑', depth_min: 0.60,
      seed: { x: 0.35, y: 0.45 }, half: { w: 0.22, h: 0.22 } }] },
  { slug: 'bianxiu', title: '绣兔牡丹', styleName: '汴绣',
    cutouts: [{ id: 'rabbit', label: '白兔与绣线', depth_min: 0.58,
      seed: { x: 0.35, y: 0.45 }, half: { w: 0.22, h: 0.22 } }] },
  { slug: 'qinghua', title: '青花蝶韵', styleName: '青花瓷纹样',
    cutouts: [{ id: 'butterfly', label: '青花蝶', depth_min: 0.55,
      seed: { x: 0.475, y: 0.45 }, half: { w: 0.26, h: 0.26 } }] },
  { slug: 'jianzhi', title: '剪影灵狐', styleName: '中国剪纸',
    cutouts: [{ id: 'fox', label: '狐狸剪影', depth_min: 0.55,
      seed: { x: 0.75, y: 0.35 }, half: { w: 0.22, h: 0.22 } }] },
];

/** 在文件里找到 hotspots: [ ... ] 的完整方括号区间（考虑字符串里的括号）。 */
function sliceHotspotsArray(source) {
  const key = source.indexOf('hotspots: [');
  if (key < 0) throw new Error('找不到 hotspots 数组');
  const start = source.indexOf('[', key);
  let depth = 0;
  let inString = null;
  for (let i = start; i < source.length; i += 1) {
    const ch = source[i];
    if (inString) {
      if (ch === '\\') { i += 1; continue; }
      if (ch === inString) inString = null;
      continue;
    }
    if (ch === "'" || ch === '"') { inString = ch; continue; }
    if (ch === '[' || ch === '{') depth += 1;
    else if (ch === ']' || ch === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start + 1, i);
    }
  }
  throw new Error('hotspots 数组没有闭合');
}

/** 把数组体按顶层对象切开。 */
function splitObjects(body) {
  const out = [];
  let depth = 0;
  let inString = null;
  let start = -1;
  for (let i = 0; i < body.length; i += 1) {
    const ch = body[i];
    if (inString) {
      if (ch === '\\') { i += 1; continue; }
      if (ch === inString) inString = null;
      continue;
    }
    if (ch === "'" || ch === '"') { inString = ch; continue; }
    if (ch === '{') { if (depth === 0) start = i; depth += 1; continue; }
    if (ch === '}') { depth -= 1; if (depth === 0 && start >= 0) out.push(body.slice(start, i + 1)); }
  }
  return out;
}

function parseHotspot(objectSource) {
  const id = /id:\s*'([^']+)'/.exec(objectSource)?.[1];
  if (!id) return null;
  const label = /title:\s*'([^']+)'/.exec(objectSource)?.[1] ?? id;
  const circle = /geometry:\s*\{\s*cx:\s*([\d.]+),\s*cy:\s*([\d.]+),\s*r:\s*([\d.]+)\s*\}/.exec(objectSource);
  const rect = /geometry:\s*\{\s*x:\s*([\d.]+),\s*y:\s*([\d.]+),\s*width:\s*([\d.]+),\s*height:\s*([\d.]+)\s*\}/.exec(objectSource);
  if (circle) {
    const [cx, cy, r] = circle.slice(1).map(Number);
    return { id, label, x: +cx.toFixed(4), y: +cy.toFixed(4), w: 0, h: 0, r: +r.toFixed(4) };
  }
  if (rect) {
    const [x, y, width, height] = rect.slice(1).map(Number);
    return {
      id, label,
      x: +(x + width / 2).toFixed(4), y: +(y + height / 2).toFixed(4),
      w: +width.toFixed(4), h: +height.toFixed(4), r: 0,
    };
  }
  return null;
}

function sourceFor(slug) {
  return `docs/examples/${slug}/generated.png`;
}

const checkOnly = process.argv.includes('--check');
mkdirSync(outDir, { recursive: true });
let drift = 0;

for (const art of ARTWORKS) {
  const tsPath = resolve(repo, `frontend/src/data/experiences/${art.slug}.ts`);
  const source = readFileSync(tsPath, 'utf8');
  const hotspots = splitObjects(sliceHotspotsArray(source))
    .map(parseHotspot)
    .filter(Boolean);

  if (hotspots.length < 4) {
    throw new Error(`${art.slug}: 只抽到 ${hotspots.length} 处热点，TS 数据可能改结构了`);
  }

  const config = {
    slug: art.slug,
    title: art.title,
    styleName: art.styleName,
    source: sourceFor(art.slug),
    // 说明：坐标从 TS 导出，不要手改这个文件，改 TS 后重跑导出。
    hotspotsSource: `frontend/src/data/experiences/${art.slug}.ts`,
    // 人工深度校正必须一起导出，否则重跑导出会把它们洗掉
    ...(art.hotspotDepthOverrides ? { hotspot_depth_overrides: art.hotspotDepthOverrides } : {}),
    hotspots,
    cutouts: art.cutouts,
  };
  const outPath = resolve(outDir, `${art.slug}.json`);
  const text = `${JSON.stringify(config, null, 2)}\n`;

  if (checkOnly) {
    if (!existsSync(outPath) || readFileSync(outPath, 'utf8') !== text) {
      console.error(`✖ ${art.slug}.json 与 TS 不一致，请重跑导出`);
      drift += 1;
    } else {
      console.log(`✔ ${art.slug}.json 一致（${hotspots.length} 处热点）`);
    }
    continue;
  }

  writeFileSync(outPath, text, 'utf8');
  console.log(`✔ ${art.slug}.json  ${hotspots.length} 处热点  ` +
    hotspots.map((h) => `${h.id}(${h.x},${h.y})`).join(' '));
}

if (checkOnly && drift > 0) process.exitCode = 1;