/**
 * 自动入库案例的加载器。
 *
 * 流水线 `scripts/interactive/ingest_case.py` 会把「新生成的图 + 自动生成的三折叙事 +
 * 自动估计的热点」写进 `docs/examples/<case>/experience.json`。这里用 glob 收进来，
 * 于是：**新图入库后不需要再改任何前端代码**，作品卡上就会同时出现
 * 「进入互动画境 / 一图一境 / 画境漫游」三个入口。
 *
 * 约束：
 *  - 只认 examples 下真实存在的 experience.json，没有就不加载；
 *  - 图必须用同一个案例目录里的 generated.png，不能借用同风格精选案例的图
 *    （那正是之前「标题写瑞猫、图里是童子」的错位来源）；
 *  - 自动案例的热点标为 approximate，前端据 locationStatus 显示「待复核」。
 *
 * 注意：`docs/examples/` 在 Vite root 之外，dev 的 watcher 覆盖不到新目录，
 * glob 只在本模块被重新编译时才会重新扫盘。新案例要立刻出现，重启 dev 服务器
 * 或改动本文件触发重编译；`npm run build` 会直接扫到最新状态。
 * 删除案例同理：文件删掉后要等下一次重编译，列表才会少掉那张卡。
 */
import type { CultureExperienceDraft } from '../features/culture-experience/types';

const manifests = import.meta.glob('../../../docs/examples/*/experience.json', {
  eager: true,
  import: 'default',
});

const images = import.meta.glob('../../../docs/examples/*/generated.png', {
  eager: true,
  query: '?url',
  import: 'default',
});

function folderOf(path: string): string | null {
  const match = /docs\/examples\/([^/]+)\//.exec(path);
  return match ? match[1] : null;
}

export interface AutoExperienceEntry {
  /** 案例目录名，同时也是 experienceId 与路由参数。 */
  folder: string;
  draft: CultureExperienceDraft;
  artworkUrl: string;
}

const imageByFolder = new Map<string, string>();
for (const [path, url] of Object.entries(images)) {
  const folder = folderOf(path);
  if (folder) imageByFolder.set(folder, url as string);
}

export const autoExperiences: AutoExperienceEntry[] = Object.entries(manifests)
  .map(([path, manifest]) => {
    const folder = folderOf(path);
    const draft = manifest as CultureExperienceDraft;
    if (!folder || !draft?.id) return null;
    const artworkUrl = imageByFolder.get(folder);
    if (!artworkUrl) {
      // 有清单没有图，说明目录被手改过；跳过而不是带着坏图渲染
      console.warn(`[auto-experience] ${folder} 缺少 generated.png，已跳过`);
      return null;
    }
    return { folder, draft, artworkUrl };
  })
  .filter((item): item is AutoExperienceEntry => Boolean(item))
  .sort((a, b) => a.folder.localeCompare(b.folder));

/** experienceId → 成图 URL，供 index.ts 注入 artworkUrl 用。 */
export const autoArtworkById = new Map(autoExperiences.map((item) => [item.draft.id, item.artworkUrl]));