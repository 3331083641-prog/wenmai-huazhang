import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import type { CultureExperienceDraft, CultureSource } from '../src/features/culture-experience/types.ts';
import { parseExperienceDraft } from '../src/features/culture-experience/schema.ts';
import zhuxianzhen from '../src/data/experiences/zhuxianzhen.ts';
import bianxiu from '../src/data/experiences/bianxiu.ts';
import songhua from '../src/data/experiences/songhua.ts';
import qinghua from '../src/data/experiences/qinghua.ts';
import jianzhi from '../src/data/experiences/jianzhi.ts';

const here = dirname(fileURLToPath(import.meta.url));
const sourcesPath = resolve(here, '../../culture_knowledge/sources.json');
const registry = JSON.parse(readFileSync(sourcesPath, 'utf8')) as {
  version: string;
  updatedAt: string;
  sources: CultureSource[];
};
const drafts: CultureExperienceDraft[] = [zhuxianzhen, bianxiu, songhua, qinghua, jianzhi];

test('来源注册表结构完整：11 条、全部有 url 与核验状态', () => {
  assert.equal(registry.sources.length, 11);
  for (const source of registry.sources) {
    assert.match(source.id, /^SRC-[A-Z0-9-]+$/);
    assert.ok(source.url.startsWith('http'), `${source.id} 缺少可点开的地址`);
    assert.ok(['verified', 'unverified'].includes(source.verification));
    assert.ok(source.publisher.length > 0);
  }
});

test('每个作品的 sourceIds 都能在注册表中解析，且没有孤立来源', () => {
  const known = new Set(registry.sources.map((source) => source.id));
  const used = new Set<string>();
  for (const draft of drafts) {
    for (const hotspot of draft.hotspots) {
      for (const id of hotspot.sourceIds) {
        assert.ok(known.has(id), `${draft.styleId}/${hotspot.id} 引用了未知来源 ${id}`);
        used.add(id);
      }
    }
    for (const chapter of draft.chapters) {
      for (const id of chapter.sourceIds) {
        assert.ok(known.has(id), `${draft.styleId}/${chapter.id} 引用了未知来源 ${id}`);
        used.add(id);
      }
    }
  }
  const orphans = [...known].filter((id) => !used.has(id));
  assert.deepEqual(orphans, [], `存在没有被任何内容引用的来源：${orphans.join(', ')}`);
});

test('热点几何全部落在 0..1 内且非零尺寸', () => {
  for (const draft of drafts) {
    for (const hotspot of draft.hotspots) {
      const g = hotspot.geometry;
      if ('points' in g) {
        for (const [x, y] of g.points) {
          assert.ok(x >= 0 && x <= 1 && y >= 0 && y <= 1, `${draft.styleId}/${hotspot.id} 点越界`);
        }
        assert.ok(g.points.length >= 3);
        continue;
      }
      if ('r' in g) {
        assert.ok(g.r > 0.01 && g.r < 0.5, `${draft.styleId}/${hotspot.id} 半径异常`);
        assert.ok(g.cx - g.r >= -0.001 && g.cx + g.r <= 1.001, `${draft.styleId}/${hotspot.id} 圆越界`);
        assert.ok(g.cy - g.r >= -0.001 && g.cy + g.r <= 1.001, `${draft.styleId}/${hotspot.id} 圆越界`);
        continue;
      }
      assert.ok(g.width > 0.02 && g.height > 0.02, `${draft.styleId}/${hotspot.id} 尺寸过小`);
      assert.ok(g.x >= 0 && g.y >= 0 && g.x + g.width <= 1.001 && g.y + g.height <= 1.001);
    }
  }
});

test('每件作品至少 3 折、热点数量在 4–6 之间', () => {
  for (const draft of drafts) {
    assert.ok(draft.chapters.length >= 3, `${draft.styleId} 章节不足 3 折`);
    assert.ok(draft.hotspots.length >= 4 && draft.hotspots.length <= 6, `${draft.styleId} 热点数量异常`);
    const isIchor = ['zhuxianzhen', 'bianxiu', 'jianzhi'].includes(draft.styleId);
    assert.equal(
      draft.provenance.sourceCaseId === draft.styleId,
      true,
      `${draft.styleId} 的 provenance.sourceCaseId 必须指向自身案例`
    );
    assert.equal(typeof isIchor, 'boolean');
  }
});

test('文案纪律：不得出现虚构馆藏、排名与越界表述', () => {
  const forbidden = [
    '御窑孤品',
    '四大年画之首',
    '博物院珍藏',
    '故宫珍藏',
    '国家一级文物',
    '唯一传世',
    '世界第一',
  ];
  const all = JSON.stringify(drafts);
  for (const phrase of forbidden) {
    assert.equal(all.includes(phrase), false, `出现禁止表述：${phrase}`);
  }
});

test('文案纪律：非非遗品类不得自称非遗', () => {
  const nonIchor = drafts.filter((draft) => ['songhua', 'qinghua'].includes(draft.styleId));
  const text = JSON.stringify(nonIchor);
  // 允许出现「非物质文化遗产」这个说明性词语（S1 文档口径），但不得把作品/品类本身称为非遗项目
  assert.equal(/本[^"]{0,6}非遗/.test(text), false);
  assert.equal(text.includes('非遗项目'), false);
});

test('文案纪律：不得把传统工艺描述成现代工业化做法', () => {
  const text = JSON.stringify(drafts);
  for (const phrase of ['激光切割', '数码印花', '机器刺绣', '印刷仿制']) {
    assert.equal(text.includes(phrase), false, `出现工艺误述：${phrase}`);
  }
});

test('分层与画境素材必须声明来源与降级说明', () => {
  const spatial = drafts.filter(
    (draft) => draft.animation.mode === 'layered' || draft.animation.mode === 'world'
  );
  assert.ok(spatial.length >= 1, '至少应有一件空间化实验作品');
  assert.ok(
    drafts.some((draft) => draft.animation.mode === 'world'),
    '应有作品使用画境漫游（world）模式'
  );
  for (const draft of spatial) {
    assert.ok(draft.animation.capabilityNote.length > 10);
    assert.ok((draft.animation.layerSource ?? '').length > 10);
    if (draft.animation.mode === 'layered') {
      // 只有 layered 模式才真正渲染分层素材，因此只有它必须声明 layers
      assert.ok((draft.animation.layers ?? []).length >= 2);
    }
    if (draft.animation.mode === 'world') {
      const world = draft.animation.world;
      assert.ok(world && world.url.endsWith('.json'), '画境模式必须声明 world.json');
      assert.ok((world?.depthNote ?? '').length > 8, '画境模式必须说明深度来源与视角限制');
      // 画境的降级路径只读作品原图，不该再挂着已经没人渲染的旧分层素材
      assert.equal(
        (draft.animation.layers ?? []).length,
        0,
        '画境模式不应再声明旧的 layers 分层素材'
      );
    }
    for (const layer of draft.animation.layers ?? []) {
      assert.ok(layer.url.endsWith('.webp'), `${layer.url} 应为压缩后的 WebP`);
      assert.ok(layer.depth >= 0 && layer.depth <= 1);
      assert.ok(layer.maskFrom <= layer.maskTo);
    }
  }
});

test('五个真实案例都必须有画境漫游，且世界清单真实存在', () => {
  const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
  assert.equal(drafts.length, 5, '应当正好五件精选作品');
  for (const draft of drafts) {
    assert.equal(
      draft.animation.mode,
      'world',
      `${draft.styleId} 应是画境漫游模式（五件作品都要有「画境漫游」入口）`
    );
    const url = draft.animation.world?.url ?? '';
    assert.match(
      url,
      /^interactive\/[a-z0-9-]+\/world\/world\.json$/,
      `${draft.styleId} 的画境清单路径不规范：${url}`
    );
    const worldPath = resolve(repo, 'frontend', 'public', url);
    const manifest = JSON.parse(readFileSync(worldPath, 'utf8')) as {
      hotspots: Array<{ id: string; depth: number }>;
      art: { file: string };
      cutouts: unknown[];
    };
    assert.ok(manifest.art?.file, `${url} 缺少 art 字段`);
    // 热点数量必须和前端数据一一对应：清单是 3D 定位依据，多一个少一个都会错位
    assert.equal(
      manifest.hotspots.length,
      draft.hotspots.length,
      `${draft.styleId} 的 world.json 热点数与前端不一致`
    );
    const ids = new Set(manifest.hotspots.map((spot) => spot.id));
    for (const hotspot of draft.hotspots) {
      assert.ok(ids.has(hotspot.id), `${draft.styleId} 的清单缺少热点 ${hotspot.id}`);
    }
    for (const spot of manifest.hotspots) {
      assert.ok(spot.depth >= 0 && spot.depth <= 1, `${spot.id} 深度越界`);
    }
  }
});

test('自动入库的案例清单（流水线产物）结构合法', () => {
  const golden = resolve(
    dirname(fileURLToPath(import.meta.url)),
    '..',
    '..',
    'scripts',
    'interactive',
    '_probe',
    'pipeline-selftest',
    'experience.json'
  );
  const draft = JSON.parse(readFileSync(golden, 'utf8')) as CultureExperienceDraft;
  const sourceIds = new Set(
    (
      JSON.parse(
        readFileSync(
          resolve(dirname(fileURLToPath(import.meta.url)), '..', '..', 'culture_knowledge', 'sources.json'),
          'utf8'
        )
      ) as { sources: CultureSource[] }
    ).sources.map((source) => source.id)
  );

  assert.equal(draft.hotspots.length >= 4 && draft.hotspots.length <= 6, true, '热点应为 4–6 处');
  assert.equal(draft.chapters.length, 3, '自动生成应固定三折');
  assert.equal(draft.animation.mode, 'world', '自动案例必须带画境漫游');
  assert.match(draft.animation.world?.url ?? '', /^interactive\/[a-z0-9-]+\/world\/world\.json$/);

  for (const hotspot of draft.hotspots) {
    assert.equal(hotspot.locationStatus, 'approximate', '自动热点必须标 approximate');
    assert.equal(hotspot.reviewStatus, 'pending', '自动热点必须标 pending');
    assert.ok(hotspot.sourceIds.length >= 1, `${hotspot.id} 缺少来源编号`);
    for (const id of hotspot.sourceIds) {
      assert.ok(sourceIds.has(id), `${hotspot.id} 引用了不存在的来源 ${id}`);
    }
    assert.ok(hotspot.culturalExplanation.length > 20, `${hotspot.id} 文化解读过短`);
  }
  for (const chapter of draft.chapters) {
    assert.ok(chapter.frame.scale >= 1.1 && chapter.frame.scale <= 2.2, '自动章节镜头倍率越界');
    assert.ok(chapter.frame.focusX >= 0 && chapter.frame.focusX <= 1);
    assert.ok(chapter.frame.focusY >= 0 && chapter.frame.focusY <= 1);
    for (const id of chapter.focusHotspotIds) {
      assert.ok(
        draft.hotspots.some((hotspot) => hotspot.id === id),
        `章节引用了不存在的热点 ${id}`
      );
    }
  }
});

test('docs/examples 下每个自动入库清单都必须能通过 schema 校验', () => {
  const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
  const examplesDir = resolve(repo, 'docs', 'examples');
  const folders = readdirSync(examplesDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name);

  let checked = 0;
  for (const folder of folders) {
    const manifest = resolve(examplesDir, folder, 'experience.json');
    if (!existsSync(manifest)) continue;
    checked += 1;
    const draft = JSON.parse(readFileSync(manifest, 'utf8')) as CultureExperienceDraft;
    // 之前流水线把 dominantColors 写成空数组，dev 下校验直接抛错、整个展厅白屏。
    // 这条用例保证「以后每一份自动清单都先在这里被拦下」。
    assert.doesNotThrow(
      () => parseExperienceDraft(draft, draft.styleId),
      `${folder}/experience.json 未通过 schema 校验`
    );
    assert.ok(
      resolve(repo, 'frontend', 'public', draft.animation.world?.url ?? '___').startsWith(
        resolve(repo, 'frontend', 'public', 'interactive')
      ),
      `${folder} 的画境清单不在 public/interactive 下`
    );
  }
  assert.ok(checked >= 0, '计数仅作说明');
});

test('静态作品必须给出「不做自动运镜」的能力说明', () => {
  for (const draft of drafts.filter((item) => item.animation.mode === 'static')) {
    assert.ok(draft.animation.capabilityNote.includes('静帧'));
  }
});

test('热点 id 唯一、每处都写清画面观察与文化解读', () => {
  for (const draft of drafts) {
    const ids = draft.hotspots.map((hotspot) => hotspot.id);
    assert.equal(new Set(ids).size, ids.length, `${draft.styleId} 热点 id 重复`);
    for (const hotspot of draft.hotspots) {
      assert.ok(hotspot.visualObservation.length >= 20, `${hotspot.id} 画面观察过短`);
      assert.ok(hotspot.culturalExplanation.length >= 40, `${hotspot.id} 文化解读过短`);
      assert.notEqual(hotspot.visualObservation, hotspot.culturalExplanation);
    }
  }
});

test('首页互动入口的图片必须来自作品成图，不能用风格参考图', () => {
  const source = readFileSync(resolve(here, '../src/pages/Home.tsx'), 'utf8');

  const start = source.indexOf('const INTERACTIVE_ENTRIES');
  assert.ok(start > 0, '找不到 INTERACTIVE_ENTRIES');
  const end = source.indexOf('];', start);
  const block = source.slice(start, end);

  // 风格参考图（public/*.png）与作品成图是两套画面：
  // 曾出现「标题写瑞猫、图里却是童子年画」的错位，这里用测试挡住回归。
  const forbidden = /img:\s*.\/?(zhuxianzhen|bianxiu|songhua|qinghua|jianzhi)\.png./g;
  assert.equal(block.match(forbidden), null, '互动入口不能引用 public/ 下的风格参考图，应使用 experience.artworkUrl');

  const ids = [...block.matchAll(/experienceId:\s*.([^']+)./g)].map((m) => m[1]);
  assert.equal(ids.length, 3, '应有 3 个 experienceId，实际 ' + ids.length);
  assert.equal(new Set(ids).size, 3, '三张入口卡不能重复用同一件作品');

  // 三张卡统一走 experience.artworkUrl：出现自定义 imageUrl 就会和另外两张产生
  // 尺寸/裁切不一致（曾出现某张图带纸边、看起来比其他两张小一圈）。
  assert.equal(
    block.match(/imageUrl:/g),
    null,
    '首页入口图应统一由 experience.artworkUrl 提供，不要再单独指定 imageUrl'
  );

  // 图片、标题、跳转必须指向同一件作品：一图一境走 /story，画境漫游走 /wander。
  const entries = [...block.matchAll(/to:\s*'([^']+)',\s*experienceId:\s*'([^']+)'/g)].map((m) => ({
    to: m[1],
    id: m[2],
  }));
  assert.equal(entries.length, 3, '每条入口都应同时声明 to 与 experienceId');
  const allowed = ['/experience/', '/story/', '/wander/'];
  for (const entry of entries) {
    assert.ok(entry.to.endsWith(`/${entry.id}`), `${entry.to} 与作品 ${entry.id} 对不上`);
    assert.ok(
      allowed.some((prefix) => entry.to.startsWith(prefix)),
      `${entry.to} 不是已知的互动入口路由`
    );
  }
});
