import type { CultureExperienceDraft } from '../../features/culture-experience/types';

/**
 * 汴绣 · 绣兔牡丹
 * 热点几何与文案纪律同 zhuxianzhen.ts。
 */
export const bianxiuExperience: CultureExperienceDraft = {
  id: 'bianxiu-xiutu',
  styleId: 'bianxiu',
  styleName: '汴绣',
  title: '绣兔牡丹',
  subtitle: '针脚即笔触',
  lead: '把画面放大到针脚那么大，才看得见它怎么被一针一针做出来。',
  artworkSize: { width: 1024, height: 1024 },
  theme: {
    accent: '#A64C54',
    accentSoft: '#D9A6A0',
    paper: '#F9F2E8',
    ink: '#3A2B28',
    gold: '#C5A56B',
  },
  visualAnalysis: {
    source: 'docs/examples/bianxiu/metadata.json · visionAnalysis',
    observedSubjects: ['白兔', '牡丹', '枝叶'],
    visualFeatures: ['丝线质感', '细密针脚', '渐变色彩', '凹凸肌理', '经纬纹理'],
    dominantColors: ['米白', '粉红', '青绿'],
  },
  hotspots: [
    {
      id: 'rabbit-head',
      title: '白兔头部',
      kicker: '造型',
      shape: 'circle',
      geometry: { cx: 0.35, cy: 0.45, r: 0.09 },
      shortDescription: '侧向的兔首，耳部斜出',
      visualObservation: '白兔头部侧向，耳部斜着向上分出，面部轮廓以细线勾出，明暗靠浅到深的色阶过渡。',
      culturalExplanation:
        '汴绣长于绣制花鸟虫鱼、飞禽走兽，绣作讲求针法严谨工致、技艺精巧细腻。兔首的立体感来自丝线色阶的层层过渡，而不是大块平涂的明暗——这是「以线代面」的绣法结果。',
      sourceIds: ['SRC-BX-KAIFENG-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'stitch-is-brush',
    },
    {
      id: 'rabbit-body',
      title: '绣线肌理',
      kicker: '工艺特征',
      shape: 'rect',
      geometry: { x: 0.41, y: 0.52, width: 0.28, height: 0.26 },
      shortDescription: '方向一致的细密线痕',
      visualObservation:
        '身体区域可见方向一致的细密横向纹理，色阶由浅到深层层排布，边缘处线迹略有不齐。',
      culturalExplanation:
        '汴绣的针法体系共 36 种（来源只给出总数，未列具体名目）。针脚排列方向配合丝线反光，形成温润的织物质感；这里可以把它读作「针脚方向即造型方向」——线往哪里走，体积就往哪里转。',
      sourceIds: ['SRC-BX-KAIFENG-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'stitch-is-brush',
    },
    {
      id: 'peony',
      title: '牡丹花',
      kicker: '花卉题材',
      shape: 'circle',
      geometry: { cx: 0.25, cy: 0.75, r: 0.1 },
      shortDescription: '柔和过渡的层叠花瓣',
      visualObservation: '左侧花头层层叠瓣，粉白到浅红过渡柔和，花瓣边缘有细微的高光线迹。',
      culturalExplanation:
        '花鸟题材是汴绣的传统表现范围。牡丹在传统装饰中常见折枝、缠枝两种构成，刺绣则以花瓣分层与丝线色阶表现花头体积：同一片花瓣上，不同深浅的线并置，远看就成了一个圆。',
      sourceIds: ['SRC-BX-KAIFENG-001', 'SRC-MOTIF-MUDAN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'palette-by-thread',
    },
    {
      id: 'leaf',
      title: '枝叶',
      kicker: '层次',
      shape: 'circle',
      geometry: { cx: 0.75, cy: 0.85, r: 0.1 },
      shortDescription: '叶脉以深色线迹分行排列',
      visualObservation: '右下枝叶以较深的线勾出脉络，叶片边缘留出浅色高光，叶与叶之间以针脚方向区分。',
      culturalExplanation:
        '刺绣里的叶脉通常以较深的线迹分行排列，形成「线中有面」的效果。与年画用墨线一次定形不同，刺绣的边界由线迹一点点累积出来，所以边缘更柔，也更容易表现叶片的转折。',
      sourceIds: ['SRC-BX-KAIFENG-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'palette-by-thread',
    },
    {
      id: 'stitch-field',
      title: '针脚与织物',
      kicker: '近观',
      shape: 'circle',
      geometry: { cx: 0.45, cy: 0.35, r: 0.08 },
      shortDescription: '平行线痕与细微交错',
      visualObservation: '画面局部可见细密的平行线痕，经纬方向略有交错，转角处线迹略密。',
      culturalExplanation:
        '这是绣面本身的纹理特征。汴绣以丝线在织物上刺绣，绣面平整、针脚细密平齐；正因为线是「有方向」的，光打上去会随视角变化泛出丝质光泽，这也是绣品难以被印刷完全复现的原因。',
      sourceIds: ['SRC-BX-KAIFENG-001'],
      locationStatus: 'approximate',
      reviewStatus: 'confirmed',
      relatedChapterId: 'stitch-is-brush',
    },
  ],
  chapters: [
    {
      id: 'stitch-is-brush',
      index: 1,
      eyebrow: '第一折 · 线',
      title: '一根线就是一笔',
      body: '刺绣没有「填色」这一步。同一片花瓣上，不同深浅的丝线被并排放置，针脚方向随形体转折——远看是渐变，近看是一行行方向不同的线。',
      focusHotspotIds: ['rabbit-head', 'rabbit-body', 'stitch-field'],
      frame: { scale: 1.75, focusX: 0.42, focusY: 0.5 },
      sourceIds: ['SRC-BX-KAIFENG-001'],
    },
    {
      id: 'palette-by-thread',
      index: 2,
      eyebrow: '第二折 · 色',
      title: '色阶不是调出来的',
      body: '绣作的色彩古朴典雅，层次主要靠丝线色阶与针脚疏密形成。想得到更深的红，就换一支更深的线；想让它变浅，就少叠一层。色不是混出来的，是一支一支选出来的。',
      focusHotspotIds: ['peony', 'leaf'],
      frame: { scale: 1.5, focusX: 0.5, focusY: 0.7 },
      sourceIds: ['SRC-BX-KAIFENG-001', 'SRC-MOTIF-MUDAN-001'],
    },
    {
      id: 'song-embroidery',
      index: 3,
      eyebrow: '第三折 · 名',
      title: '为什么叫「宋绣」',
      body: '汴绣也称宋绣，因产生于北宋都城汴京（开封）而得名。北宋时汴京刺绣业兴盛，靖康二年（1127）后逐渐衰落；新中国建立后，几代艺人整理宋代刺绣技艺，并借鉴苏绣、湘绣等长处，总结出 36 种针法。',
      focusHotspotIds: ['rabbit-body', 'leaf'],
      frame: { scale: 1.2, focusX: 0.5, focusY: 0.55 },
      sourceIds: ['SRC-BX-KAIFENG-001'],
    },
  ],
  animation: {
    mode: 'world',
    world: {
      url: 'interactive/bianxiu/world/world.json',
      depthNote: '单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格',
    },
    capabilityNote:
      '画境由这一幅绣品做单目深度估计后生成深度网格：可以推近看针脚与色阶、小幅转头、在前后有限范围里移动；刺绣是平面的，深度来自画面明暗与丝线反光的估计，不能绕到白兔或花枝背后，也不是三维重建。低性能设备与「减少动态效果」会自动降级为静止画面。',
    layerSource:
      'Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；白兔近景另按深度阈值抠像，让主体与底料拉开一前一后。',
  },
  provenance: {
    sourceCaseId: 'bianxiu',
    knowledgeVersion: '1.0.0',
    authoredAt: '2026-10-20',
    hotspotMethod:
      '本地 Qwen3-VL(4b) 网格定位 + 最终几何裁切复核；仅在裁切内容与目标一致时写入 verified。',
    designNote: '「放大到针脚」的交互思路来自工艺本身的尺度特征，未参考任何外部视频画面。',
  },
};

export default bianxiuExperience;