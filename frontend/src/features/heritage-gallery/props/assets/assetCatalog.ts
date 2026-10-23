/**
 * 非遗器物（5.html 白名单 14 件）的元数据。
 *
 * 五个被用户明确排除的 ID 不在这里、也不在 PROP_BUILDERS 里：
 *   DIY_A06 / DIY_A10 / DIY_B05 / DIY_C03 / DIY_D05
 *
 * placement：
 *   floor   地面陈设，落地摆放
 *   surface 桌面陈设，可放在地面/桌面/展柜顶（吸附到承载物顶面）
 *   hang    顶部悬挂，必须吸附到梁架锚点，不允许悬空
 */

export type AssetGroup = 'general' | 'nianhua' | 'bianxiu' | 'songhua' | 'qinghua' | 'jianzhi';

export interface AssetDef {
  id: string;
  name: string;
  /** 英文名，来自原始 HTML 的 en 字段 */
  en: string;
  group: AssetGroup;
  placement: 'floor' | 'surface' | 'hang';
  /** 占地 [宽, 深]，米 */
  footprint: [number, number];
  /** 高度，米（构建后仍以真实包围盒为准） */
  height: number;
  /** 非遗说明，页面卡片用 */
  note: string;
  /** 专属互动的一句话说明 */
  interaction: string;
}

export const ASSET_GROUP_LABEL: Record<AssetGroup, string> = {
  general: '通用陈设',
  nianhua: '朱仙镇木版年画',
  bianxiu: '汴绣工坊',
  songhua: '宋画青绿山水',
  qinghua: '青花瓷艺术',
  jianzhi: '中国剪纸',
};

export const ASSET_DEFS: AssetDef[] = [
  {
    id: 'DIY_A01', name: '胡桃木博古架', en: 'bogujia_walnut', group: 'general',
    placement: 'floor', footprint: [1.2, 0.36], height: 1.85,
    note: '满彻攒接的多层博古架，抽屉与柜门可开合，格心留六处吸附点。',
    interaction: '抽屉依次拉出、柜门向两侧打开，再次点击复位',
  },
  {
    id: 'DIY_A02', name: '云纹玻璃展柜', en: 'display_case_cloud', group: 'general',
    placement: 'floor', footprint: [0.8, 0.8], height: 1.45,
    note: '黄铜升降导杆承托玻璃罩，罩内为独立展台，柜身束腰刻云头。',
    interaction: '玻璃罩沿导杆缓缓升起露出展品，再次点击闭合',
  },
  {
    id: 'DIY_A04', name: '宋式折叠屏风', en: 'folding_screen_song', group: 'general',
    placement: 'floor', footprint: [1.8, 0.25], height: 1.75,
    note: '四扇绞链联动，可按铰链自然折叠，屏心为《千里江山》通景。',
    interaction: '四扇联动折叠，再次点击展开',
  },
  {
    id: 'DIY_A05', name: '莲花暖光立灯', en: 'floor_lamp_lotus', group: 'general',
    placement: 'floor', footprint: [0.42, 0.42], height: 1.52,
    note: '三层 24 瓣尖攒莲花灯罩，中心为莲蓬灯芯，末端垂青玉流苏。',
    interaction: '莲花灯逐渐点亮、流苏轻摆，再次点击熄灭',
  },
  {
    id: 'DIY_A07', name: '六方悬挂宫灯', en: 'palace_lantern_hex', group: 'general',
    placement: 'hang', footprint: [0.48, 0.48], height: 0.86,
    note: '上下两层六方攒角木框，六面嵌青绿山水绢片，顶部黄铜提梁。',
    interaction: '绕悬挂轴轻转、流苏摆动、灯芯渐亮，再次点击停转',
  },
  {
    id: 'DIY_A09', name: '宋式铜座文化展签架', en: 'plaque_stand_song', group: 'general',
    placement: 'floor', footprint: [0.38, 0.26], height: 1.08,
    note: '厚重大理石须弥座配黄铜莲瓣压盘，顶部为 45° 倾斜展签牌。',
    interaction: '弹出该器物的文化解读卡，再次点击或关闭收起',
  },
  {
    id: 'DIY_B02', name: '木版套印工作台', en: 'woodblock_printing_table', group: 'nianhua',
    placement: 'floor', footprint: [1.2, 0.65], height: 0.78,
    note: '阳刻主墨线版、棕刷与朱砂石绿双色颜料碗，宣纸一端压于夹下。',
    interaction: '宣纸从雕版上缓缓揭起，再次点击回落',
  },
  {
    id: 'DIY_C02', name: '彩色丝线陈列架', en: 'silk_thread_rack', group: 'bianxiu',
    placement: 'surface', footprint: [0.7, 0.3], height: 0.95,
    note: '四排线轴陈列，木架承托，可逐排转动查看传统色名。',
    interaction: '指定一排线轴绕自身轴轻转，再次点击停止',
  },
  {
    id: 'DIY_D01', name: '宋式画案与矿物颜料', en: 'painting_desk_song', group: 'songhua',
    placement: 'floor', footprint: [1.4, 0.7], height: 0.85,
    note: '画案上置砚台、笔洗、笔架与矿物颜料盒，画卷半展。',
    interaction: '颜料盒盖开合、画卷轻展，再次点击收回',
  },
  {
    id: 'DIY_D04', name: '青绿山水微缩摆件', en: 'mini_landscape', group: 'songhua',
    placement: 'surface', footprint: [0.6, 0.4], height: 0.55,
    note: '石青石绿双峰、亭台与石拱桥，山间云雾成层。',
    interaction: '云雾缓缓流动，再次点击暂停',
  },
  {
    id: 'DIY_E01', name: '青花瓷梅瓶', en: 'meiping_qinghua', group: 'qinghua',
    placement: 'surface', footprint: [0.28, 0.28], height: 0.45,
    note: '小口丰肩，釉下青花缠枝，圈足露胎，下配紫檀五足座。',
    interaction: '瓷瓶绕自身竖轴缓转一周展示纹样，支座不动',
  },
  {
    id: 'DIY_E02', name: '青花瓷茶具套组', en: 'tea_set_qinghua', group: 'qinghua',
    placement: 'surface', footprint: [0.46, 0.3], height: 0.16,
    note: '一壶四杯一盘，壶盖可揭，杯内茶汤色如琥珀。',
    interaction: '壶盖轻揭，再次点击复位',
  },
  {
    id: 'DIY_E05', name: '青花瓷文创花灯', en: 'porcelain_lantern_qinghua', group: 'qinghua',
    placement: 'surface', footprint: [0.3, 0.3], height: 0.42,
    note: '六根青花瓷转角柱与上下六方瓷板围合，板心海棠开光透光。',
    interaction: '点亮内部暖光，再次点击熄灭',
  },
  {
    id: 'DIY_F05', name: '可旋转剪纸走马灯', en: 'revolving_papercut_lantern', group: 'jianzhi',
    placement: 'surface', footprint: [0.36, 0.36], height: 0.56,
    note: '黄铜主轴贯通上下，轴挂热气风车叶轮与八角剪纸转笼。',
    interaction: '内部剪纸转笼缓转、灯光投出剪影，再次点击停止',
  },
];

export const ASSET_BY_ID = new Map(ASSET_DEFS.map((def) => [def.id, def]));

export function isAssetId(id: string): boolean {
  return ASSET_BY_ID.has(id);
}