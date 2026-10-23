/**
 * CultureExperience —— 交互式文化体验的统一数据结构。
 *
 * 三层信息必须分开存放，渲染时也要分栏呈现：
 *   1. visualObservation  画面里真实可见的细节（只描述像素）
 *   2. culturalExplanation 有来源支撑的文化知识 / 明确的审美解释
 *   3. provenance          数据怎么来的（案例、知识版本、热点定位方法）
 *
 * 坐标约定：所有几何量都是相对「图像本身的绘制区域」归一化到 0..1，
 * 与容器尺寸、object-fit、缩放、浏览器宽度无关。热点层因此可以在任何
 * 视口下与画面像素严格对齐（见 utils/geometry.ts）。
 */

export type HotspotShape = 'rect' | 'circle' | 'polygon';

/** 归一化矩形：x/y 为左上角，width/height 为相对整幅画面的比例。 */
export interface RectGeometry {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** 归一化圆：cx/cy 为圆心，r 以「画面短边」为基准。 */
export interface CircleGeometry {
  cx: number;
  cy: number;
  r: number;
}

/** 归一化多边形：点序列 [x, y]，首尾自动闭合。 */
export interface PolygonGeometry {
  points: Array<[number, number]>;
}

export type HotspotGeometry = RectGeometry | CircleGeometry | PolygonGeometry;

export type LocationStatus = 'verified' | 'approximate' | 'unverified';
export type ReviewStatus = 'confirmed' | 'pending';

export interface CultureHotspot {
  id: string;
  title: string;
  /** 小标签，如「主体刻画」「工艺特征」，用于面板上的分类眉标。 */
  kicker: string;
  shape: HotspotShape;
  geometry: HotspotGeometry;
  /** 一句话摘要，用于列表与悬停提示。 */
  shortDescription: string;
  /** 只写画面里看得见的东西，不做文化解读。 */
  visualObservation: string;
  /** 文化知识与审美解释，必须能对应到 sourceIds。 */
  culturalExplanation: string;
  sourceIds: string[];
  locationStatus: LocationStatus;
  reviewStatus: ReviewStatus;
  /** 关联的叙事章节 id，用于「在故事中继续」的跳转。 */
  relatedChapterId?: string;
}

/** 叙事章节的镜头参数：把画面某点按 scale 放大并居中。 */
export interface ChapterFrame {
  scale: number;
  focusX: number;
  focusY: number;
}

export interface CultureChapter {
  id: string;
  index: number;
  eyebrow: string;
  title: string;
  body: string;
  focusHotspotIds: string[];
  frame: ChapterFrame;
  sourceIds: string[];
}

/** 2.5D 分层素材。depth 越大越靠近观众。 */
export interface CultureLayer {
  id: string;
  url: string;
  depth: number;
  /** 该层遮罩的垂直渐变区间（0..1），用于羽化叠层边缘。 */
  maskFrom: number;
  maskTo: number;
  opacity?: number;
}

export type AnimationMode = 'static' | 'parallax' | 'layered' | 'world';

/** 画境清单（由 scripts/interactive/build_painting_world.py 生成）。 */
export interface CultureWorld {
  /** world.json 的 public 路径。 */
  url: string;
  /** 深度能力说明，例如「单图深度估计，有限视角」。 */
  depthNote?: string;
}

export interface CultureAnimation {
  mode: AnimationMode;
  layers?: CultureLayer[];
  world?: CultureWorld;
  /** 降级与性能说明，直接展示给用户，避免夸大。 */
  capabilityNote: string;
  /** 分层素材的来源说明（程序化分带 / 人工制作 / 深度模型）。 */
  layerSource?: string;
}

export interface ExperienceTheme {
  /** 主强调色（朱砂红 / 石绿 / 钴蓝 …）。 */
  accent: string;
  /** 强调色的低饱和衬色。 */
  accentSoft: string;
  /** 该风格的纸底色。 */
  paper: string;
  /** 正文色。 */
  ink: string;
  /** 描边与细线的金色。 */
  gold: string;
}

export interface VisualAnalysis {
  source: string;
  model?: string;
  observedSubjects: string[];
  visualFeatures: string[];
  dominantColors: string[];
}

export interface ExperienceProvenance {
  sourceCaseId?: string;
  knowledgeVersion?: string;
  authoredAt?: string;
  /** 热点定位方法说明，用于回答「坐标凭什么可信」。 */
  hotspotMethod?: string;
  /** 参考视频与开源方案只做技术参考，不复制素材。 */
  designNote?: string;
}

export interface CultureExperience {
  id: string;
  styleId: string;
  styleName: string;
  title: string;
  subtitle: string;
  /** 第一幕的一句文化引导文案。 */
  lead: string;
  artworkUrl: string;
  artworkSize: { width: number; height: number };
  referenceUrl?: string;
  cultureCardUrl?: string;
  theme: ExperienceTheme;
  visualAnalysis: VisualAnalysis;
  hotspots: CultureHotspot[];
  chapters: CultureChapter[];
  animation: CultureAnimation;
  provenance: ExperienceProvenance;
}

/** 作者态数据：资源 URL 由 data/experiences/index.ts 统一注入。 */
export type CultureExperienceDraft = Omit<
  CultureExperience,
  'artworkUrl' | 'artworkSize' | 'referenceUrl' | 'cultureCardUrl'
> & {
  artworkSize: { width: number; height: number };
};

export interface CultureSource {
  id: string;
  title: string;
  publisher: string;
  url: string;
  sourceType: string;
  retrievedAt: string;
  verification: 'verified' | 'unverified';
  verificationNote: string;
  supports: string[];
}