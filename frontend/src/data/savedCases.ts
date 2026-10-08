import cat from '../../../docs/examples/zhuxianzhen/metadata.json';
import rabbit from '../../../docs/examples/bianxiu/metadata.json';
import tower from '../../../docs/examples/songhua/metadata.json';
import butterfly from '../../../docs/examples/qinghua/metadata.json';
import fox from '../../../docs/examples/jianzhi/metadata.json';
import type { VisionAnalysis } from '../services/generationService';

const files = import.meta.glob('../../../docs/examples/*/*.png', { eager: true, query: '?url', import: 'default' }) as Record<string, string>;
export const savedCases = [cat, rabbit, tower, butterfly, fox].map((metadata) => ({
  ...metadata,
  visionAnalysis: metadata.visionAnalysis as VisionAnalysis,
  referenceUrl: files[`../../../docs/examples/${metadata.styleId}/reference.png`],
  imageUrl: files[`../../../docs/examples/${metadata.styleId}/generated.png`],
  cardUrl: files[`../../../docs/examples/${metadata.styleId}/culture_card.png`],
}));

export function loadSavedCase(item: typeof savedCases[number]) {
  localStorage.setItem('wenmai_latest_result', JSON.stringify({
    ...item, style: item.styleId, theme: 'theme' in item ? item.theme : item.artworkTitle,
    createdAt: item.generatedAt, mode: 'image_to_image', savedExample: true,
    referencePreviewUrl: item.referenceUrl,
  }));
}
