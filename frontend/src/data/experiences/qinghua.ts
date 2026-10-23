import type { CultureExperienceDraft } from '../../features/culture-experience/types';

/**
 * 青花瓷纹样 · 青花蝶韵
 * 注意：青花瓷是瓷器品种，不是非遗项目；文案不得称其为「非遗」。
 */
export const qinghuaExperience: CultureExperienceDraft = {
  id: 'qinghua-dieyun',
  styleId: 'qinghua',
  styleName: '青花瓷纹样',
  title: '青花蝶韵',
  subtitle: '白地蓝花，釉下之色',
  lead: '这一笔蓝，是烧出来的，不是画上去的。',
  artworkSize: { width: 1024, height: 1024 },
  theme: {
    accent: '#315F88',
    accentSoft: '#8EABC0',
    paper: '#F6F3EC',
    ink: '#2A3540',
    gold: '#B9A469',
  },
  visualAnalysis: {
    source: 'docs/examples/qinghua/metadata.json · visionAnalysis',
    observedSubjects: ['蝴蝶', '青花纹样', '蓝白配色'],
    visualFeatures: ['蓝白分明', '纹样密集', '翅脉清晰', '触角细长', '边缘点状装饰'],
    dominantColors: ['深蓝', '白', '浅灰'],
  },
  hotspots: [
    {
      id: 'butterfly-body',
      title: '蝴蝶身体',
      kicker: '主纹',
      shape: 'circle',
      geometry: { cx: 0.475, cy: 0.45, r: 0.05 },
      shortDescription: '细长的身体与两根外扬的触角',
      visualObservation: '画面正中一条细长身体，触角向外上方扬起，头胸腹以深浅不同的蓝分层，边缘有轻微晕散。',
      culturalExplanation:
        '青花属釉下彩：以氧化钴为着色剂，在素坯上描绘纹饰，再施透明釉、高温还原焰一次烧成。蓝色来自钴料发色，浓淡由青料与绘制手法决定，因此能看见笔触与晕散——它接近水墨，而不是涂料。',
      sourceIds: ['SRC-QH-JINGDEZHEN-001', 'SRC-MOTIF-CIWEN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'under-the-glaze',
    },
    {
      id: 'left-wing',
      title: '左翼纹样',
      kicker: '构图',
      shape: 'circle',
      geometry: { cx: 0.33, cy: 0.45, r: 0.1 },
      shortDescription: '以卷曲线与留白填满的翼面',
      visualObservation: '左翼展开，翼内以卷曲的线条与点状留白布满，靠翼缘处留出一圈白色瓷地。',
      culturalExplanation:
        '青花纹样以线条勾勒加渲染（分水）构成，留白处即白瓷地。翼内的卷曲形态与缠枝骨架在视觉上相近，但两者不是同一回事：缠枝是以枝干或蔓藤为骨架、枝叶相互缠绕的连续图案，蝶翼只是借用了这种「连绵不断」的排布节奏。',
      sourceIds: ['SRC-MOTIF-CIWEN-001', 'SRC-QH-JINGDEZHEN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'white-is-a-colour',
    },
    {
      id: 'right-wing',
      title: '右翼纹样',
      kicker: '构图',
      shape: 'circle',
      geometry: { cx: 0.62, cy: 0.45, r: 0.1 },
      shortDescription: '与左翼对称的翼面结构',
      visualObservation: '右翼与左翼基本对称，翼脉由身体向外辐射，翼缘的点状装饰更密。',
      culturalExplanation:
        '对称是器物装饰的常态：盘心或器身主纹居中，左右呼应，便于在任何角度观看。翅膀的对称也顺带完成了「主纹居中」这件事——这正是青花常见的构图逻辑。',
      sourceIds: ['SRC-MOTIF-CIWEN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'white-is-a-colour',
    },
    {
      id: 'vine',
      title: '缠枝花卉纹',
      kicker: '骨架式构图',
      shape: 'circle',
      geometry: { cx: 0.55, cy: 0.75, r: 0.1 },
      shortDescription: '连绵相扣的枝蔓与沿枝排布的叶片',
      visualObservation: '下方缠绕的枝蔓连绵相扣，叶片与小花沿枝排布，枝的转折处留出圆形白点。',
      culturalExplanation:
        '缠枝是青花装饰中最常见的骨架式构图之一：以枝干或蔓藤为骨架，枝叶相互缠绕，构成四方或二方连续图案，有缠枝莲、缠枝菊、缠枝牡丹等。故宫藏品说明中，同一件器物常分层布置主纹、辅助纹与边饰。',
      sourceIds: ['SRC-MOTIF-CIWEN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'skeleton-and-main',
    },
  ],
  chapters: [
    {
      id: 'under-the-glaze',
      index: 1,
      eyebrow: '第一折 · 釉下',
      title: '颜色被烧在釉下面',
      body: '先在素坯上用钴料描画，再罩一层透明釉，然后入窑高温还原焰一次烧成。蓝色被釉层封在里面，所以不怕磨损——这也是青花能长久保持鲜亮的原因。',
      focusHotspotIds: ['butterfly-body'],
      frame: { scale: 2.1, focusX: 0.475, focusY: 0.45 },
      sourceIds: ['SRC-QH-JINGDEZHEN-001', 'SRC-MOTIF-CIWEN-001'],
    },
    {
      id: 'white-is-a-colour',
      index: 2,
      eyebrow: '第二折 · 留白',
      title: '白也是一种颜色',
      body: '青花的白不是空着的背景，而是与蓝同等参与构图的「瓷地」。纹样之间的留白决定疏密：留得少则繁密，留得多则清朗。明代青花常被形容为豪放潇洒、疏密有致。',
      focusHotspotIds: ['left-wing', 'right-wing'],
      frame: { scale: 1.7, focusX: 0.5, focusY: 0.45 },
      sourceIds: ['SRC-MOTIF-CIWEN-001'],
    },
    {
      id: 'skeleton-and-main',
      index: 3,
      eyebrow: '第三折 · 骨',
      title: '骨架与主纹',
      body: '同一件器物上，主纹、辅助纹、边饰各司其职：中间是主角，四周是连绵的骨架，口沿或足墙再来一圈带状连续纹。看懂骨架，才知道哪一笔是「正在说的事」。',
      focusHotspotIds: ['vine', 'butterfly-body'],
      frame: { scale: 1.45, focusX: 0.5, focusY: 0.62 },
      sourceIds: ['SRC-MOTIF-CIWEN-001', 'SRC-QH-JINGDEZHEN-001'],
    },
  ],
  animation: {
    mode: 'world',
    world: {
      url: 'interactive/qinghua/world/world.json',
      depthNote: '单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格',
    },
    capabilityNote:
      '画境由这一幅青花画面做单目深度估计后生成深度网格：可以推近看青料的浓淡、小幅转头、在前后有限范围里移动；瓷器是曲面，这里的「前后」是模型对纹样与器形关系的估计，不能绕到瓶身背后，也不是三维重建。低性能设备与「减少动态效果」会自动降级为静止画面。',
    layerSource:
      'Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；蝶翼近景另按深度阈值抠像，让蝴蝶从釉面上浮起一点。',
  },
  provenance: {
    sourceCaseId: 'qinghua',
    knowledgeVersion: '1.0.0',
    authoredAt: '2026-10-20',
    hotspotMethod:
      '本地 Qwen3-VL(4b) 网格定位 + 最终几何裁切复核；同一物体上的多个元素分别定位，避免坐标重叠。',
    designNote: '青花瓷为瓷器品种，本项目不将其表述为非物质文化遗产项目。',
  },
};

export default qinghuaExperience;