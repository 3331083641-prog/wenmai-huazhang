import type { CultureExperienceDraft } from '../../features/culture-experience/types';

/**
 * 朱仙镇木版年画 · 瑞猫迎春
 *
 * 热点几何来自本地 Qwen3-VL 候选定位 + 逐点裁切复核（见 docs/interactive_v2/S1_INTERACTIVE_PAINTING.md）。
 * 文案纪律：visualObservation 只写像素可见内容；culturalExplanation 只写
 * culture_knowledge/zhuxianzhen.json 支持的事实，以及明确标注的审美解释。
 */
export const zhuxianzhenExperience: CultureExperienceDraft = {
  id: 'zhuxianzhen-ruimao',
  styleId: 'zhuxianzhen',
  styleName: '朱仙镇木版年画',
  title: '瑞猫迎春',
  subtitle: '墨线立骨，一色一版',
  lead: '先看它怎么被印出来，再看它为什么这样看。',
  artworkSize: { width: 1024, height: 1024 },
  theme: {
    accent: '#9E241B',
    accentSoft: '#C4573C',
    paper: '#F8EEDC',
    ink: '#3F2B1F',
    gold: '#D2A14A',
  },
  visualAnalysis: {
    source: 'docs/examples/zhuxianzhen/metadata.json · visionAnalysis',
    observedSubjects: ['狸花猫', '牡丹花', '祥云纹', '海水纹', '吉祥横幅'],
    visualFeatures: ['粗黑刀刻式轮廓', '木版套色错版肌理', '平面化形体', '吉祥纹样围合', '红黄绿高对比色块'],
    dominantColors: ['朱红', '明黄', '松绿', '墨黑'],
  },
  hotspots: [
    {
      id: 'cat-face',
      title: '猫的脸部',
      kicker: '主体刻画',
      shape: 'circle',
      geometry: { cx: 0.35, cy: 0.45, r: 0.085 },
      shortDescription: '圆眼外挑、鼻梁单线挑起的兽面',
      visualObservation:
        '猫的双眼与口鼻集中在中部偏左，眼形圆而外挑，鼻梁用一道细线挑起，整张脸由粗黑轮廓圈定，内部基本是平涂色块。',
      culturalExplanation:
        '朱仙镇木版年画以墨线版作为全画的骨架，轮廓线粗犷遒劲，造型古朴夸张，不追求写实比例。主体面部往往是刀口最深、线条最密的地方——因为它要在套印时把各块色版的位置钉死。这张脸因此更像一枚被刻出来的印章，而不是一张写生的猫脸。',
      sourceIds: ['SRC-ZXZ-NIANHUA-001', 'SRC-ZXZ-CRAFT-002'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'ink-line-first',
    },
    {
      id: 'tiger-stripe',
      title: '虎斑条纹',
      kicker: '线刻转译',
      shape: 'rect',
      geometry: { x: 0.4, y: 0.51, width: 0.3, height: 0.28 },
      shortDescription: '把毛发转成一组有节奏的线刻',
      visualObservation:
        '猫身披有条纹，条纹随体块起伏改变方向，条纹之间留出横向的浅色带，没有一根根细毛的描绘。',
      culturalExplanation:
        '分色套印把画面拆成色块：墨线版负责边界，各色版负责填色，一幅完整年画通常需要五到九块雕版。所以虎斑不是毛发质感，而是一组服务于套准的线刻节奏。看见条纹的疏密，就看见了刻版时的刀路。',
      sourceIds: ['SRC-ZXZ-CRAFT-002'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'one-colour-one-block',
    },
    {
      id: 'peony',
      title: '牡丹花',
      kicker: '花卉母题',
      shape: 'circle',
      geometry: { cx: 0.105, cy: 0.75, r: 0.1 },
      shortDescription: '左下角层叠花头的边缘装饰',
      visualObservation:
        '左下角一朵层叠花头，外层花瓣以数道弧线分层，花心收拢成小圆，花瓣之间以深色线分隔。',
      culturalExplanation:
        '牡丹是传统装饰中常见的花卉母题，在瓷器上可见折枝牡丹、缠枝牡丹等构成方式。本幅把它放在边缘作陪衬，与中心主体形成主次。需要说明的是：这里的牡丹是生成图的装饰结果，不能反推某件具体年画作品的花卉程式。',
      sourceIds: ['SRC-MOTIF-MUDAN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'border-order',
    },
    {
      id: 'cloud-motif',
      title: '祥云纹',
      kicker: '边角呼应',
      shape: 'circle',
      geometry: { cx: 0.15, cy: 0.15, r: 0.1 },
      shortDescription: '左上角两三笔回旋的云头',
      visualObservation: '左上角一组卷云头，云头由两三道回旋弧线概括，末端蜷成小钩。',
      culturalExplanation:
        '祥云在宫殿建筑彩画中是常用的脊步题材，云彩自古被赋予吉祥寓意。建筑彩画的祥云程式与年画的云纹画法并不通用，这里只借用「云头回旋」这一形态共性，不能把两者当作同一套纹样规范。',
      sourceIds: ['SRC-MOTIF-XIANGYUN-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'border-order',
    },
    {
      id: 'wave-band',
      title: '海水纹',
      kicker: '带状边饰',
      shape: 'rect',
      geometry: { x: 0.62, y: 0.875, width: 0.26, height: 0.12 },
      shortDescription: '底缘连续波状线，波峰内填层叠弧线',
      visualObservation: '画面底缘一条连续的波状线带，波峰内部填充层叠弧线，节奏由密到疏再回密。',
      culturalExplanation:
        '海水纹在传统装饰里常作边饰使用。故宫藏明代御窑青花器中可见「青花海水纹」一类组合，织绣上也有海水江崖的绣制实例。年画底缘的水纹同样是「带状连续边饰」的用法，但不同材质的画法程式各自独立，不能互相证明形态。',
      sourceIds: ['SRC-QH-JINGDEZHEN-001', 'SRC-MOTIF-HAISHUI-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'border-order',
    },
    {
      id: 'title-banner',
      title: '顶部题名横带',
      kicker: '图文同构',
      shape: 'rect',
      geometry: { x: 0.59, y: 0.005, width: 0.32, height: 0.1 },
      shortDescription: '承托题名的横向色带',
      visualObservation: '画面顶端一条横向色带，色带上压着深色笔画，与下方图案区以一道细线分隔。',
      culturalExplanation:
        '传统年画常在画面留出题字位置，文字与图像共同完成叙事，题名本身也是构图的一部分。故宫的科普说明把祥瑞图案的构成逻辑分为特定寓意型、谐音型与直抒胸臆型三类——直接在画面里写出吉语，正属于第三类。需要提醒：这条横带与带上的文字是这张生成图自带的，不是历史题跋，也不构成对某件旧作的引用。',
      sourceIds: ['SRC-ZXZ-NIANHUA-001', 'SRC-MOTIF-JIXIANG-001'],
      locationStatus: 'approximate',
      reviewStatus: 'confirmed',
      relatedChapterId: 'one-colour-one-block',
    },
  ],
  chapters: [
    {
      id: 'ink-line-first',
      index: 1,
      eyebrow: '第一折 · 骨',
      title: '先有线，才有色',
      body: '年画的制作从起稿、雕版开始。墨线主版先被刻出来，它决定所有色块的位置——之后每一次换版，都要回到这套线上对准。所以画面里最重的黑不是阴影，而是骨架。',
      focusHotspotIds: ['cat-face'],
      frame: { scale: 1.85, focusX: 0.35, focusY: 0.45 },
      sourceIds: ['SRC-ZXZ-CRAFT-002'],
    },
    {
      id: 'one-colour-one-block',
      index: 2,
      eyebrow: '第二折 · 色',
      title: '一色一版，先淡后重',
      body: '一套雕版由一块墨线主版和数块分色版组成，一幅完整年画需五到九块版。印刷时先印墨线，再逐次换色版套印，讲究先淡后重——浅色在下、深色在上，叠压处才会留下层次。',
      focusHotspotIds: ['tiger-stripe', 'title-banner'],
      frame: { scale: 1.4, focusX: 0.5, focusY: 0.62 },
      sourceIds: ['SRC-ZXZ-CRAFT-002'],
    },
    {
      id: 'border-order',
      index: 3,
      eyebrow: '第三折 · 围',
      title: '边框把祝福围起来',
      body: '云头压角、花枝落地、水纹铺底，这些边饰不是填空。它们把主体围在中央，也把吉祥话的语义收束成一圈：从四个方向往中间读，视线最后都会落回主体身上。',
      focusHotspotIds: ['cloud-motif', 'peony', 'wave-band'],
      frame: { scale: 1.15, focusX: 0.5, focusY: 0.5 },
      sourceIds: ['SRC-ZXZ-NIANHUA-001', 'SRC-MOTIF-XIANGYUN-001', 'SRC-MOTIF-MUDAN-001'],
    },
  ],
  animation: {
    mode: 'world',
    world: {
      url: 'interactive/zhuxianzhen/world/world.json',
      depthNote: '单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格',
    },
    capabilityNote:
      '画境由这一张木版年画做单目深度估计后生成深度网格：可以推近看墨线与套色、小幅转头、在前后有限范围里移动；年画本身是印在纸上的平面，深度是模型对画面前后关系的估计，不能绕到猫或花枝背后，也不是三维重建。低性能设备与「减少动态效果」会自动降级为静止画面。',
    layerSource:
      'Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；猫身近景另按深度阈值抠像，让主体在视差里略微浮出纸面。',
  },
  provenance: {
    sourceCaseId: 'zhuxianzhen',
    knowledgeVersion: '1.0.0',
    authoredAt: '2026-10-20',
    hotspotMethod:
      '本地 Qwen3-VL(4b) 在 10×10 网格上定位候选，再按最终几何逐点裁切复核；未通过复核的点不写入数据。',
    designNote: '交互形式参考「可探索的画」这一通用产品形态；四个短视频链接均只返回平台风控中间页，未取得任何画面内容。',
  },
};

export default zhuxianzhenExperience;