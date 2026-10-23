import cat from '../../../docs/examples/zhuxianzhen/metadata.json';
import rabbit from '../../../docs/examples/bianxiu/metadata.json';
import tower from '../../../docs/examples/songhua/metadata.json';
import butterfly from '../../../docs/examples/qinghua/metadata.json';
import fox from '../../../docs/examples/jianzhi/metadata.json';
import { normalizeAnalysis, type GalleryCase } from '../services/caseService';

const files = import.meta.glob('../../../docs/examples/*/*.png', { eager: true, query: '?url', import: 'default' }) as Record<string, string>;

/**
 * 随仓库提交的五件真实案例。
 * 这些是编译期打包的：没有后端、没有网络也能完整展示与互动。
 * 运行期新生成的案例由 services/caseService.ts 从后端 /cases 拉取后合并进来。
 */
export const savedCases: GalleryCase[] = [cat, rabbit, tower, butterfly, fox].map((metadata) => ({
  caseId: metadata.styleId,
  caseOrigin: 'curated',
  styleId: metadata.styleId,
  styleName: metadata.styleName,
  artworkTitle: metadata.artworkTitle,
  theme: (metadata as { theme?: string }).theme ?? metadata.artworkTitle,
  generatedAt: metadata.generatedAt,
  styleStrength: metadata.styleStrength,
  analysisSource: metadata.analysisSource,
  provider: metadata.provider,
  model: metadata.model,
  visionAnalysis: normalizeAnalysis(metadata.visionAnalysis),
  cultureCard: (metadata as { cultureCard?: Record<string, string> }).cultureCard,
  referenceUrl: files[`../../../docs/examples/${metadata.styleId}/reference.png`],
  imageUrl: files[`../../../docs/examples/${metadata.styleId}/generated.png`],
  cardUrl: files[`../../../docs/examples/${metadata.styleId}/culture_card.png`],
}));

/**
 * 后续入库的案例（docs/examples 下除五件精选之外的目录）。
 *
 * 为什么编译期也要收：后端没启动时展厅只显示内置案例，新入库的作品会整个消失。
 * 这些目录由 `scripts/interactive/ingest_case.py` 或后端自动保存写出，
 * 带上 experienceId 之后卡片上就会同时出现三个互动入口。
 *
 * 注意：glob 在模块被重新编译时才会重新扫描磁盘，而 `docs/examples/` 在 Vite root
 * 之外、dev 的 watcher 覆盖不到；新目录要出现（或删掉的目录要消失），重启 dev 服务器
 * 或改动本文件触发重编译。
 */
const CURATED = new Set(['zhuxianzhen', 'bianxiu', 'songhua', 'qinghua', 'jianzhi']);

const extraMetadata = import.meta.glob('../../../docs/examples/*/metadata.json', {
  eager: true,
  import: 'default',
}) as Record<string, Record<string, unknown>>;

function folderOfCase(path: string): string | null {
  const match = /docs\/examples\/([^/]+)\//.exec(path);
  return match ? match[1] : null;
}

export const autoSavedCases: GalleryCase[] = Object.entries(extraMetadata)
  .map(([path, metadata]): GalleryCase | null => {
    const folder = folderOfCase(path);
    if (!folder || CURATED.has(folder)) return null;
    const meta = metadata as Record<string, unknown>;
    const styleId = String(meta.styleId ?? '');
    const experienceId = String(meta.experienceId ?? '');
    return {
      caseId: folder,
      caseOrigin: 'runtime' as const,
      experienceId: experienceId || undefined,
      styleId,
      styleName: String(meta.styleName ?? styleId),
      artworkTitle: String(meta.artworkTitle ?? folder),
      theme: String(meta.theme ?? meta.artworkTitle ?? folder),
      generatedAt: String(meta.generatedAt ?? ''),
      styleStrength: Number(meta.styleStrength ?? 0) || 0,
      analysisSource: String(meta.analysisSource ?? 'auto_ingest'),
      provider: meta.provider ? String(meta.provider) : undefined,
      model: meta.model ? String(meta.model) : undefined,
      visionAnalysis: normalizeAnalysis(meta.visionAnalysis),
      cultureCard: (meta.cultureCard as Record<string, string> | undefined) ?? undefined,
      referenceUrl: files[`../../../docs/examples/${folder}/reference.png`],
      imageUrl: files[`../../../docs/examples/${folder}/generated.png`] ?? '',
      cardUrl: files[`../../../docs/examples/${folder}/culture_card.png`],
    } satisfies GalleryCase;
  })
  .filter((item): item is GalleryCase => Boolean(item?.imageUrl))
  .sort((a, b) => (a.generatedAt < b.generatedAt ? 1 : -1));

export function loadSavedCase(item: GalleryCase) {
  localStorage.setItem('wenmai_latest_result', JSON.stringify({
    ...item,
    style: item.styleId,
    theme: item.theme || item.artworkTitle,
    createdAt: item.generatedAt,
    mode: 'image_to_image',
    savedExample: true,
    referencePreviewUrl: item.referenceUrl,
  }));
}