import type { CultureExperienceDraft } from '../../features/culture-experience/types';

/**
 * 中国剪纸 · 剪影灵狐
 * 注意：剪纸的工具是剪刀与刻刀并用；不得表述为激光切割、数码印花。
 */
export const jianzhiExperience: CultureExperienceDraft = {
  id: 'jianzhi-linghu',
  styleId: 'jianzhi',
  styleName: '中国剪纸',
  title: '剪影灵狐',
  subtitle: '一纸之内，正负两形',
  lead: '先数一数留下多少纸，再看那只狐狸。',
  artworkSize: { width: 1024, height: 1024 },
  theme: {
    accent: '#A52225',
    accentSoft: '#D98C7A',
    paper: '#FBF3E9',
    ink: '#3A2320',
    gold: '#D7B16A',
  },
  visualAnalysis: {
    source: 'docs/examples/jianzhi/metadata.json · visionAnalysis',
    observedSubjects: ['赤狐', '花卉装饰'],
    visualFeatures: ['镂空结构', '红白对比', '对称布局', '毛发细节', '花鸟图案'],
    dominantColors: ['红色', '白色'],
  },
  hotspots: [
    {
      id: 'fox-head',
      title: '赤狐头部',
      kicker: '阳刻轮廓',
      shape: 'circle',
      geometry: { cx: 0.75, cy: 0.35, r: 0.085 },
      shortDescription: '尖耳立起、口鼻收成细角',
      visualObservation: '头部朝侧上方，双耳尖立，眼眶留出白色小孔，口鼻以细尖收束，外轮廓连续无断点。',
      culturalExplanation:
        '剪纸的阳刻保留轮廓线、线线相连，画面因此玲珑细致。兽首的辨识度几乎全靠外轮廓与少量内部镂空完成：耳、眼、吻都用最省的线交代，因为每多切一刀，就多一分断裂的风险。',
      sourceIds: ['SRC-JZ-PAPER-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'yin-and-yang',
    },
    {
      id: 'fox-body',
      title: '狐身与毛发镂空',
      kicker: '镂空',
      shape: 'rect',
      geometry: { x: 0.52, y: 0.42, width: 0.26, height: 0.26 },
      shortDescription: '成组月牙形镂空与相连的纸筋',
      visualObservation: '身体与尾部以成组的月牙形镂空表现毛发，镂空之间留下细窄的纸筋，红白交替排列。',
      culturalExplanation:
        '剪纸大面积镂空，正负形互为图底，空白与实体同等参与造型。毛发这类细节不靠颜色，而靠「留多少纸」来表现疏密：留得少是腹部，留得多是背部，光影被改写成了密度。',
      sourceIds: ['SRC-JZ-PAPER-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'negative-space',
    },
    {
      id: 'flower-tl',
      title: '花卉环饰（左上）',
      kicker: '对称',
      shape: 'circle',
      geometry: { cx: 0.25, cy: 0.15, r: 0.1 },
      shortDescription: '花瓣以连续弧线剪出的角花',
      visualObservation: '左上角花枝展开，花瓣以连续弧线剪出，花心留一个小孔，枝叶向画面内侧伸展。',
      culturalExplanation:
        '折叠剪纸可以让花卉得到四面或六面均齐的对称形状：纸对折两三次后一次剪成，展开就是重复的图案。角花因此常被用来「围」住主体——四角开花，中间才像一个被围起来的场。',
      sourceIds: ['SRC-JZ-PAPER-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'folded-symmetry',
    },
    {
      id: 'flower-br',
      title: '花卉环饰（右下）',
      kicker: '环饰',
      shape: 'circle',
      geometry: { cx: 0.85, cy: 0.75, r: 0.1 },
      shortDescription: '与左上呼应的角花',
      visualObservation: '右下角花枝与左上呼应，花瓣层数略多，叶片以细长条剪出，末端带小齿。',
      culturalExplanation:
        '剪纸按制作方法可分为单色剪纸、彩色剪纸、立体剪纸三类，这里呈现的是单色一路：只有一种纸色，层次全靠镂空疏密与线条粗细。所谓「红白对比」，其实是纸与空的关系。',
      sourceIds: ['SRC-JZ-PAPER-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'folded-symmetry',
    },
  ],
  chapters: [
    {
      id: 'yin-and-yang',
      index: 1,
      eyebrow: '第一折 · 刀',
      title: '剪刀与刻刀，都是主要工具',
      body: '剪纸并不只用剪刀。阴刻刻去表示物象结构的轮廓线，线与线不相连，块面厚重；阳刻保留轮廓线、线线相连，画面玲珑细致。同一幅里阴阳并用，红线才会有粗有细。',
      focusHotspotIds: ['fox-head'],
      frame: { scale: 2.0, focusX: 0.75, focusY: 0.35 },
      sourceIds: ['SRC-JZ-PAPER-001'],
    },
    {
      id: 'negative-space',
      index: 2,
      eyebrow: '第二折 · 空',
      title: '空的地方也在造型',
      body: '剪纸大面积镂空，正负形互为图底。狐身的毛发不是画出来的，是切掉一部分纸之后剩下的形状——空白与实体同等参与造型，这是它和绘画最不一样的地方。',
      focusHotspotIds: ['fox-body'],
      frame: { scale: 1.75, focusX: 0.62, focusY: 0.55 },
      sourceIds: ['SRC-JZ-PAPER-001'],
    },
    {
      id: 'folded-symmetry',
      index: 3,
      eyebrow: '第三折 · 折',
      title: '折一次，得到一倍',
      body: '折叠后剪制会形成重复图案：折两三次，花卉就能得到四面或六面均齐的形状。折痕即是镜像轴，展开时对称自动成立——这是剪纸最经济的一招，也是它最容易被认出的长相。',
      focusHotspotIds: ['flower-tl', 'flower-br'],
      frame: { scale: 1.3, focusX: 0.5, focusY: 0.5 },
      sourceIds: ['SRC-JZ-PAPER-001'],
    },
  ],
  animation: {
    mode: 'world',
    world: {
      url: 'interactive/jianzhi/world/world.json',
      depthNote: '单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格',
    },
    capabilityNote:
      '画境由这一张剪纸做单目深度估计后生成深度网格：可以推近看镂空的边界、小幅转头、在前后有限范围里移动；剪纸只有一层纸，深度是模型对图案层次的估计，不能绕到狐狸背后，也不是三维重建。低性能设备与「减少动态效果」会自动降级为静止画面。',
    layerSource:
      'Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；狐狸主体另按深度阈值抠像，让纸样在视差里略微抬起。',
  },
  provenance: {
    sourceCaseId: 'jianzhi',
    knowledgeVersion: '1.0.0',
    authoredAt: '2026-10-20',
    hotspotMethod:
      '本地 Qwen3-VL(4b) 网格定位 + 最终几何裁切复核；同一动物上的头/身分别定位。',
    designNote: '剪纸于 2006 年列入第一批国家级非遗名录（Ⅶ-16），2009 年入选联合国教科文组织人类非遗代表作名录。',
  },
};

export default jianzhiExperience;