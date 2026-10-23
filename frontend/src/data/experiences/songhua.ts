import type { CultureExperienceDraft } from '../../features/culture-experience/types';

/**
 * 宋画青绿山水 · 云鹤临水楼
 *
 * 画境漫游样板：animation.mode = 'world'。
 * 画境由单图作品做单目深度估计（Depth Anything V2 Small）后生成深度网格，
 * 叠加水面/云雾/植被三通道羽化遮罩与近景松石抠像，再由着色器驱动视差与微动；
 * 素材由 scripts/interactive/build_painting_world.py 生成。
 * 不是三维重建、不是点云、不是 mesh 还原——文案与 UI 都必须按这个口径描述。
 * 降级路径只读作品原图（docs/examples/songhua/generated.png），不再依赖旧的分层素材。
 */
export const songhuaExperience: CultureExperienceDraft = {
  id: 'songhua-yunhe',
  styleId: 'songhua',
  styleName: '宋画青绿山水',
  title: '云鹤临水楼',
  subtitle: '石青石绿，三远之间',
  lead: '光会在画里走。移动指针，让远近自己分开。',
  artworkSize: { width: 1024, height: 1024 },
  theme: {
    accent: '#426C62',
    accentSoft: '#8FA9A0',
    paper: '#F4F1E6',
    ink: '#2F3A36',
    gold: '#B99A5B',
  },
  visualAnalysis: {
    source: 'docs/examples/songhua/metadata.json · visionAnalysis',
    observedSubjects: ['双层楼阁', '仙鹤', '青绿山峦', '松树', '云雾'],
    visualFeatures: ['青绿设色层峦', '双层楼阁木构', '云雾留白空间', '仙鹤展翼飞掠', '松枝斜出岸石'],
    dominantColors: ['青绿', '灰褐', '白', '浅蓝'],
  },
  hotspots: [
    {
      id: 'pavilion',
      title: '双层楼阁',
      kicker: '点景建筑',
      shape: 'rect',
      geometry: { x: 0.44, y: 0.44, width: 0.22, height: 0.22 },
      shortDescription: '居中偏右的水榭，比例远小于山体',
      visualObservation: '画面中部偏右一处双层楼阁，屋面以深色块面概括，柱身用竖线分隔，台基压在水面之上。',
      culturalExplanation:
        '青绿山水里的建筑多为点景：水榭楼台、茅屋草舍各依地势环境而设，尺度远小于山体。《千里江山图》即以长桥与流水沟通各段景物，楼阁因此承担「让人落脚」的叙事作用，而不是画面主角。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'scenery-dots',
    },
    {
      id: 'crane',
      title: '仙鹤',
      kicker: '点景禽鸟',
      shape: 'circle',
      geometry: { cx: 0.34, cy: 0.25, r: 0.085 },
      shortDescription: '展翼掠过云气的白鹤',
      visualObservation: '左上方一只白鹤展翼，身形以白粉提亮，翅尖收成尖角，身下是一条淡色的云带。',
      culturalExplanation:
        '禽鸟在青绿山水中同样属点景，比例细小如豆，靠姿态而非细节辨认。鹤是后世常入画的瑞禽，此处借它清逸的姿态为画面定一个「轻」的重心。需要提醒：这是生成图的选择，不能据此推断某幅宋画里有鹤。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'scenery-dots',
    },
    {
      id: 'mountains',
      title: '青绿山峦',
      kicker: '主色',
      shape: 'rect',
      geometry: { x: 0.005, y: 0.03, width: 0.28, height: 0.24 },
      shortDescription: '石青石绿分层积染的峰峦',
      visualObservation: '左上群峰以石青、石绿分层积染，峰脊处留出赭色过渡，山脚被云雾截断。',
      culturalExplanation:
        '青绿法以石青、石绿等矿物质为主要颜料，敷色夸张、具有一定装饰性；山体分层积染，轮廓与皴笔被色彩部分覆盖。这正是青绿一路「色中求变化」的特点——同色系内分层，浓淡并用，而不是一块平涂的蓝绿。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'three-distances',
    },
    {
      id: 'mist',
      title: '云雾留白',
      kicker: '空间处理',
      shape: 'circle',
      geometry: { cx: 0.355, cy: 0.435, r: 0.1 },
      shortDescription: '把前后山体分开的一带云气',
      visualObservation: '中部一带云气由淡墨与留白相接，前山在此收边，后山从云后重新起势。',
      culturalExplanation:
        '青绿山水以云雾留白营造空间层次：留白不是「没画」，而是承担分隔与呼吸的结构。山体被云截断，观者才会自行补出它后面的深远——这也是长卷能一段段读下去的原因。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'three-distances',
    },
    {
      id: 'pine',
      title: '松树与坡石',
      kicker: '近景压角',
      shape: 'circle',
      geometry: { cx: 0.15, cy: 0.75, r: 0.1 },
      shortDescription: '左下斜出的松枝与坡石',
      visualObservation: '左下松枝斜向伸出，针叶以短促的放射状线条成组，坡石用赭墨勾皴并压住画面下缘。',
      culturalExplanation:
        '松石是山水画常见的前景元素，用较重的墨色压住画面下缘，与远景的青绿形成「近实远虚」。前景越实，远山才显得越远——这是很朴素的视觉经验，也是三远法能成立的前提。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'three-distances',
    },
    {
      id: 'water',
      title: '水面与汀岸',
      kicker: '水法',
      shape: 'circle',
      geometry: { cx: 0.75, cy: 0.85, r: 0.1 },
      shortDescription: '层层排列的细弧水纹',
      visualObservation: '右下水面以细弧线层层排列，近处线距较宽、远处渐密，岸线呈不规则的折线。',
      culturalExplanation:
        '《千里江山图》以细笔逐笔画出微波水纹，渔舟游船点缀其间。水纹的排线方向即水面的「势」：线从近往远收，视线就跟着往远处走——水面因此成为连接各段景物的通道。',
      sourceIds: ['SRC-SH-QINGLU-001'],
      locationStatus: 'verified',
      reviewStatus: 'confirmed',
      relatedChapterId: 'azure-from-mineral',
    },
  ],
  chapters: [
    {
      id: 'three-distances',
      index: 1,
      eyebrow: '第一折 · 远',
      title: '三远不是三种角度',
      body: '高远、深远、平远在同一幅画里穿插使用：抬头看峰是「高」，越过前山看后山是「深」，顺着水面望出去是「平」。它们不是机位，而是让一段长卷可以持续读下去的节奏。',
      focusHotspotIds: ['mountains', 'mist', 'pine'],
      frame: { scale: 1.35, focusX: 0.42, focusY: 0.4 },
      sourceIds: ['SRC-SH-QINGLU-001'],
    },
    {
      id: 'azure-from-mineral',
      index: 2,
      eyebrow: '第二折 · 色',
      title: '青绿是从矿里来的',
      body: '石青、石绿都是矿物质颜料，覆盖力强、色彩沉稳，敷色可以夸张而带装饰性。为了不让大片冷色发闷，画师以赭色作衬底与过渡——层次就是这样被「压」出来的。',
      focusHotspotIds: ['mountains', 'water'],
      frame: { scale: 1.5, focusX: 0.35, focusY: 0.25 },
      sourceIds: ['SRC-SH-QINGLU-001'],
    },
    {
      id: 'scenery-dots',
      index: 3,
      eyebrow: '第三折 · 点',
      title: '楼与鹤：画面里最小的人',
      body: '楼台、舟桥、禽鸟、人物都是点景，比例极小，却给山水定下尺度。没有那只鹤，山只是颜色；有了它，才知道山有多高、云有多厚。',
      focusHotspotIds: ['pavilion', 'crane'],
      frame: { scale: 1.75, focusX: 0.55, focusY: 0.55 },
      sourceIds: ['SRC-SH-QINGLU-001'],
    },
  ],
  animation: {
    mode: 'world',
    world: {
      url: 'interactive/songhua/world/world.json',
      depthNote: '单图深度估计（Depth Anything V2 Small）驱动的 2.5D 深度网格',
    },
    capabilityNote:
      '画境由单张作品做单目深度估计后生成深度网格：可推进、可小幅转头、可在前后有限范围内移动；' +
      '不能绕到山石或楼阁背后，也不是三维重建。低性能设备与「减少动态效果」会自动降级为静止画面。',
    layerSource:
      'Depth Anything V2 Small（单目深度估计）+ 逐像素深度网格；末端的松石抠像沿用深度阈值与种子漫水，' +
      '非人工逐笔绘制。',
    // 旧的 CSS 三层视差素材与 layers 声明已移除：降级路径改为「原画倾斜 + 线索胶囊」，
    // 只用到作品原图，不再加载 layer-far/mid/near.webp。
  },
  provenance: {
    sourceCaseId: 'songhua',
    knowledgeVersion: '1.0.0',
    authoredAt: '2026-10-20',
    hotspotMethod:
      '本地 Qwen3-VL(4b) 网格定位 + 最终几何裁切复核；复核内容与目标一致才记为 verified。',
    designNote:
      '画境为自研 three.js / React Three Fiber 实现：单张作品经 Depth Anything V2 Small ' +
      '估计相对深度，生成一整块连续的深度位移网格（不分层拼贴，因此不会出现层缝），' +
      '配自写着色器做云雾流动、水面波纹与枝叶轻摆；雾、水、叶三类区域由图像统计自动生成遮罩，' +
      '不是人工绘制。旧的 CSS 三层视差保留作为降级路径。参考了开源项目的分层视差与深度漫游思路，' +
      '未复制其代码与素材。',
  },
};

export default songhuaExperience;