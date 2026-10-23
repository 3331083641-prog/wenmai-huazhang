/**
 * 纹脉展馆 · 共享类型
 *
 * 约定：
 *  - 画框位置一律使用「墙面局部坐标」（u ∈ [0,1] 横向，v ∈ [0,1] 纵向），
 *    而不是世界坐标。这样墙面移动、缩放、旋转时画框自动跟随，也便于持久化。
 *  - 所有坐标都是归一化值，渲染时再乘以墙面的实际尺寸。
 */

/** 一面可布展的墙。id 在配置里唯一。 */
export interface GalleryWall {
  id: string;
  /** 楼层：1 = 一层，2 = 二层 */
  floor: 1 | 2;
  /** 墙面中心的世界坐标 */
  center: [number, number, number];
  /** 墙面朝向（弧度，绕 Y 轴）。0 = 面向 +Z */
  rotationY: number;
  /** 墙面实际尺寸（米）：[宽, 高] */
  size: [number, number];
  /** 这面墙最多允许挂几幅（用于防重叠的粗略上限） */
  capacity: number;
  /** 人类可读的名字，用于面板显示 */
  label: string;
}

/** 一个画框位。位置是墙面局部归一化坐标。 */
export interface FrameSlot {
  id: string;
  wallId: string;
  /** 墙面局部归一化坐标，0..1 */
  u: number;
  v: number;
  /** 画框外框尺寸（米）：[宽, 高] */
  size: [number, number];
  /** 默认挂载的作品 id；空字符串表示空框 */
  defaultArtworkId: string;
}

/** 可挂载的一件作品。来源必须是项目里真实存在的案例。 */
export interface GalleryArtwork {
  id: string;
  title: string;
  styleId: string;
  styleName: string;
  /** 正图（挂到画框上的那张） */
  imageUrl: string;
  /** 缩略图（面板里用，缺省时用 imageUrl） */
  thumbUrl: string;
  /** 文化卡，可选 */
  cultureCardUrl?: string;
  /** 参考图，可选 */
  referenceUrl?: string;
  /** 一句话说明，来自案例的文化解读 */
  summary: string;
  /** 视觉特征标签 */
  features: string[];
  /** 生成时间 */
  generatedAt: string;
  /** 数据来源：curated = 随仓库提交；runtime = 运行期自动保存 */
  origin: 'curated' | 'runtime';
  /** 主题色，用于画框高亮与面板强调 */
  accent: string;
}

/** 布展方案：只存「哪个画框挂了哪件作品」以及画框位置。 */
export interface CurationState {
  /** frameSlotId -> artworkId（空字符串表示空框） */
  assignments: Record<string, string>;
  /** frameSlotId -> 局部坐标（用户拖拽后的位置） */
  positions: Record<string, { u: number; v: number }>;
}

/** 画框交互态 */
export type FrameInteraction =
  | { kind: 'idle' }
  | { kind: 'selected'; frameId: string }
  | { kind: 'dragging'; frameId: string };

/** 摄像机预设：外观、一层、二层 */
export interface CameraPreset {
  id: string;
  label: string;
  position: [number, number, number];
  target: [number, number, number];
  /** 该机位对应的水平视场角（度），来自 Blender 相机焦距换算；网页按 4:3 换成垂直角 */
  fov?: number;
}

/**
 * 浏览模式：
 *  - exterior  外观：屋顶保留，机位只给外部
 *  - interior  内部：屋顶隐藏，机位只给楼层
 *  - curation  布展：内部取景 + 画框高亮 + 图库面板常开
 */
export type GalleryMode = 'exterior' | 'interior' | 'curation';
