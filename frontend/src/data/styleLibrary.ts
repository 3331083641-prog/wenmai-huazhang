export interface CultureCard {
  title: string;
  cultureSource: string;
  visualFeatures: string;
  symbolicMeaning: string;
  applicationScenario?: string;
}

export interface StyleData {
  id: string;
  name: string;
  img: string;
  category: string;
  shortDescription: string;
  visualFeatures: string[];
  promptVisualFeatures: string;
  recommendedScenes: string[];
  cardTheme: 'zhuxianzhen' | 'bianxiu' | 'qinglv' | 'qinghua' | 'jianzhi';
  cultureSource: string;
  symbolicMeaning: string;
  tag: string;
  categoryLabel: string;
  desc: string;
  tags: string[];
  scene: string;
}

export const cultureCardThemes = {
  zhuxianzhen: { primary: '#a92822', secondary: '#d9a93f', ink: '#49392f', paper: '#fff8e9', motif: 'auspicious' },
  bianxiu: { primary: '#a64c54', secondary: '#c5a56b', ink: '#51423e', paper: '#fff9f2', motif: 'floral' },
  qinglv: { primary: '#426c62', secondary: '#b99a5b', ink: '#384941', paper: '#f8f5e9', motif: 'scroll' },
  qinghua: { primary: '#315f88', secondary: '#8eabc0', ink: '#344958', paper: '#f5f9fb', motif: 'key' },
  jianzhi: { primary: '#a52225', secondary: '#d7b16a', ink: '#4b3030', paper: '#fff8f1', motif: 'cutpaper' },
} as const;

export const STYLES: StyleData[] = [
  {
    id: 'zhuxianzhen',
    name: '朱仙镇木版年画',
    img: '/zhuxianzhen.png',
    category: '非遗木版年画',
    shortDescription: '以套色印刷、醒目轮廓和吉祥题材为视觉参考，侧重节庆装饰氛围。',
    visualFeatures: ['朱红与明黄', '醒目轮廓', '饱满构图', '吉祥纹样'],
    promptVisualFeatures: '高饱和红绿黄配色、粗黑轮廓线、门神式构图、吉祥纹样、木版印刷肌理',
    recommendedScenes: ['节庆主题海报', '民俗文创', '校园美育'],
    cardTheme: 'zhuxianzhen',
    cultureSource: '朱仙镇木版年画',
    symbolicMeaning: '祥云、水纹、花卉与门神形象可作年画装饰参考；具体寓意需结合作品与地域语境理解',
    tag: '年画',
    categoryLabel: '非遗技艺 · 木版年画',
    desc: '以套色印刷、醒目轮廓和吉祥题材为视觉参考，侧重节庆装饰氛围。',
    tags: ['红绿黄配色', '粗黑线条', '门神式构图'],
    scene: '可用于节庆主题海报、门神题材插画与民俗文创概念设计。'
  },
  {
    id: 'bianxiu',
    name: '汴绣纹样',
    img: '/bianxiu.png',
    category: '传统刺绣工艺',
    shortDescription: '以细密针脚、丝线质感和花鸟题材作为视觉参考，呈现层次丰富的装饰效果。',
    visualFeatures: ['细密线条', '柔和设色', '花卉纹样', '丝线质感'],
    promptVisualFeatures: '丝线质感、牡丹花鸟纹样、细密针脚、柔和渐变、典雅刺绣装饰',
    recommendedScenes: ['文创海报', '明信片', '织物纹样'],
    cardTheme: 'bianxiu',
    cultureSource: '汴绣',
    symbolicMeaning: '花鸟、牡丹等题材可作刺绣视觉参考；具体寓意因作品语境而异',
    tag: '刺绣',
    categoryLabel: '传统刺绣工艺',
    desc: '以细密针脚、丝线质感和花鸟题材作为视觉参考，呈现层次丰富的装饰效果。',
    tags: ['丝线质感', '细密针脚', '花鸟题材'],
    scene: '可用于服饰纹样、织物图案与纪念品的概念设计。'
  },
  {
    id: 'songhua',
    name: '宋画青绿山水',
    img: '/songhua.png',
    category: '传统绘画风格',
    shortDescription: '参考宋代青绿山水的设色与构图，以石青石绿、层峦和留白组织画面。',
    visualFeatures: ['石青石绿', '层峦构图', '山水留白', '卷轴意境'],
    promptVisualFeatures: '石青、石绿为主的青绿设色、层峦构图与传统山水画审美',
    recommendedScenes: ['数字展陈', '文化主题海报', '长幅背景'],
    cardTheme: 'qinglv',
    cultureSource: '宋代青绿山水',
    symbolicMeaning: '山水、云雾与楼阁意象呈现传统山水画的空间和自然主题',
    tag: '山水',
    categoryLabel: '传统绘画风格',
    desc: '参考宋代青绿山水代表作的设色与构图；青绿山水是传统绘画风格，不属于非遗项目类别。',
    tags: ['石青石绿设色', '层峦构图', '着色山水'],
    scene: '可用于长幅画面、数字展陈背景与文化主题海报的创作参考。'
  },
  {
    id: 'qinghua',
    name: '青花瓷纹样',
    img: '/qinghua.png',
    category: '传统器物装饰',
    shortDescription: '以青白配色、钴蓝纹样和缠枝花卉等器物装饰元素作为视觉参考。',
    visualFeatures: ['青白配色', '钴蓝纹样', '缠枝花卉', '器物留白'],
    promptVisualFeatures: '蓝白配色、钴蓝纹样、缠枝莲、云纹、水波纹、白瓷质感',
    recommendedScenes: ['杯垫图案', '明信片', '家居纹样'],
    cardTheme: 'qinghua',
    cultureSource: '青花瓷',
    symbolicMeaning: '莲花、云纹与水波等可作器物装饰纹样参考；具体寓意需结合器物语境理解',
    tag: '陶瓷',
    categoryLabel: '传统器物装饰',
    desc: '以蓝白配色、钴蓝纹样和缠枝花卉等器物装饰元素作为视觉参考。',
    tags: ['蓝白配色', '缠枝纹样', '器物装饰'],
    scene: '可用于杯垫、扇面与家居用品的图案概念设计。'
  },
  {
    id: 'jianzhi',
    name: '中国剪纸',
    img: '/jianzhi.png',
    category: '民间剪纸艺术',
    shortDescription: '以阴阳正负形、连贯线条与镂空效果作为民间剪纸的视觉参考。',
    visualFeatures: ['正负形关系', '镂空结构', '对称纹样', '连贯线条'],
    promptVisualFeatures: '剪纸的正负形、镂空效果与连贯线条；红纸是常见的材料色彩表现之一',
    recommendedScenes: ['节庆窗花', '文创书签', '活动海报'],
    cardTheme: 'jianzhi',
    cultureSource: '中国剪纸',
    symbolicMeaning: '红色、对称纹样与花卉题材常见于节庆剪纸表达；具体寓意因地区与主题而异',
    tag: '剪纸',
    categoryLabel: '民间剪纸艺术',
    desc: '以阴阳正负形、连贯线条与镂空效果作为民间剪纸的视觉参考。',
    tags: ['正负形关系', '镂空结构', '连贯线条'],
    scene: '可用于节庆窗花、书签与文化活动视觉概念设计。'
  }
];
