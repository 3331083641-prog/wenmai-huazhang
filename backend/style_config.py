from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
OUTPUT_DIR = BACKEND_DIR / "outputs"
UPLOAD_DIR = BACKEND_DIR / "uploads"
STYLE_REFS_DIR = BACKEND_DIR / "style_refs"
ASSETS_STYLE_REFS_DIR = PROJECT_ROOT / "assets" / "style_refs"
FRONTEND_PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"
EXTERNAL_INSTANTSTYLE_DIR = PROJECT_ROOT / "external" / "InstantStyle"


@dataclass(frozen=True)
class StyleConfig:
    id: str
    name: str
    filename: str
    culture_source: str
    visual_features: str
    symbolic_meaning: str
    tag: str
    description: str
    palette: tuple[str, str, str]
    recommended_scenes: tuple[str, ...] = ()
    literary_references: tuple[str, ...] = ()
    culture_interpretation_guide: str = ""

    @property
    def refImagePath(self) -> str:
        return str(STYLE_REFS_DIR / self.filename)


@dataclass(frozen=True)
class OutputPreset:
    id: str
    label: str
    prompt_hint: str


@dataclass(frozen=True)
class CompositionPreset:
    id: str
    label: str
    width: int
    height: int
    prompt_hint: str


STYLE_LIBRARY: Dict[str, StyleConfig] = {
    "zhuxianzhen": StyleConfig(
        id="zhuxianzhen",
        name="朱仙镇木版年画",
        filename="zhuxianzhen.png",
        culture_source="河南开封朱仙镇木版年画",
        visual_features="红绿黄配色、粗黑轮廓线、门神式构图、吉祥纹样、木版印刷肌理",
        symbolic_meaning="祥云、水纹、花卉与门神形象可作年画装饰参考；具体寓意需结合作品与地域语境理解",
        tag="年画",
        description="以套色印刷、醒目轮廓和吉祥题材为视觉参考，侧重节庆装饰氛围。",
        palette=("#B81E24", "#F1C24B", "#226B4D"),
        recommended_scenes=("节庆主题海报", "民俗文创", "校园美育"),
        literary_references=("王安石《元日》：千门万户曈曈日，总把新桃换旧符。",),
        culture_interpretation_guide="岁时节庆里，门神与瑞兽守护门庭，花卉、祥云铺陈迎祥纳福的愿望；朱红明黄与饱满构图，把年节的热烈和盼望带入画面。",
    ),
    "bianxiu": StyleConfig(
        id="bianxiu",
        name="汴绣纹样",
        filename="bianxiu.png",
        culture_source="河南汴绣",
        visual_features="丝线质感、牡丹花鸟纹样、细密针脚、柔和渐变、典雅刺绣装饰",
        symbolic_meaning="花鸟、牡丹等题材可作刺绣视觉参考；具体寓意因作品语境而异",
        tag="刺绣",
        description="针法细密、色彩温润，擅长花鸟与传统纹样表达。",
        palette=("#8E2F3C", "#D9A7A0", "#2E6F5E"),
        recommended_scenes=("文创海报", "明信片", "校园美育"),
        literary_references=("刘禹锡《赏牡丹》：唯有牡丹真国色，花开时节动京城。",),
        culture_interpretation_guide="牡丹花鸟的丰茂与温婉，是传统刺绣装饰中的审美意象；细密针线般的视觉效果，将枝叶、花瓣与灵动小兽收束在一方柔和天地。",
    ),
    "songhua": StyleConfig(
        id="songhua",
        name="宋画青绿山水",
        filename="songhua.png",
        culture_source="宋代青绿山水美学",
        visual_features="青绿设色、山水长卷、云雾留白、楼阁意象、传统绘画审美",
        symbolic_meaning="山水意象体现宋韵美学、自然秩序和文人精神",
        tag="山水",
        description="以青绿设色、层峦构图与云雾留白作为传统山水画的视觉参考。",
        palette=("#2F6F73", "#7EA17A", "#D6C48E"),
        recommended_scenes=("数字展陈", "文化主题海报", "长幅背景"),
        literary_references=("王维《山居秋暝》：明月松间照，清泉石上流。",),
        culture_interpretation_guide="青绿设色让层峦溪谷焕发清润光泽，云雾留白使空间可行、可望、可游、可居；山水成为寄放心境与自然理想的天地。",
    ),
    "qinghua": StyleConfig(
        id="qinghua",
        name="青花瓷纹样",
        filename="qinghua.png",
        culture_source="青花瓷器纹样",
        visual_features="蓝白配色、缠枝莲、云纹、水波纹、白瓷质感、釉下青花韵味",
        symbolic_meaning="莲花、云纹与水波等可作器物装饰纹样参考；具体寓意需结合器物语境理解",
        tag="陶瓷",
        description="以蓝白配色、钴蓝纹样和缠枝花卉等器物装饰元素作为视觉参考。",
        palette=("#1F4E8C", "#F7F8F4", "#6D9AC5"),
        recommended_scenes=("杯垫图案", "明信片", "家居纹样"),
        literary_references=("汉乐府《江南》：鱼戏莲叶间。", "周敦颐《爱莲说》：出淤泥而不染，濯清涟而不妖。"),
        culture_interpretation_guide="莲与鱼相伴、水纹相连，令人想起‘鱼戏莲叶间’的灵动；缠枝纹绵延不绝，云纹引向天光，蓝白之间兼见清雅、丰盈与流动。",
    ),
    "jianzhi": StyleConfig(
        id="jianzhi",
        name="中国剪纸",
        filename="jianzhi.png",
        culture_source="中国民间剪纸",
        visual_features="红色剪纸、镂空结构、对称构图、民俗花卉、节庆氛围",
        symbolic_meaning="红色、对称纹样与花卉题材常见于节庆剪纸表达；具体寓意因地区与主题而异",
        tag="剪纸",
        description="注重阴阳正负形与红白强对比的民间视觉语言。",
        palette=("#C8171E", "#FFF7EF", "#7A0F16"),
        recommended_scenes=("节庆窗花", "文创书签", "活动海报"),
        literary_references=(),
        culture_interpretation_guide="红纸的阴阳正负形以镂空、对称连接花鸟万物，常把团圆、生长、纳福的愿望剪进窗花；利落线条让日常祝愿变成鲜明图景。",
    ),
}


OUTPUT_PRESETS: Dict[str, OutputPreset] = {
    "poster": OutputPreset("poster", "数字海报视觉稿", "poster layout, clear visual center, readable composition"),
    "postcard": OutputPreset("postcard", "文旅明信片效果预览", "travel postcard layout, scenic composition"),
    "bag": OutputPreset("bag", "帆布袋图案视觉设计", "tote bag graphic preview, clean silhouette, centered motif"),
    "bookmark": OutputPreset("bookmark", "文创书签视觉设计", "bookmark illustration, vertical decorative composition"),
    "coaster": OutputPreset("coaster", "陶瓷杯垫图案预览", "ceramic coaster graphic, circular-friendly composition"),
    "social": OutputPreset("social", "手机分享图版式示意", "mobile social post layout, clear foreground"),
    "screen": OutputPreset("screen", "数字展陈屏效果示意", "digital exhibition screen layout, wide composition"),
    "ticket": OutputPreset("ticket", "纪念票版式示意", "commemorative ticket layout, ornamental frame"),
}


COMPOSITION_PRESETS: Dict[str, CompositionPreset] = {
    "portrait": CompositionPreset("portrait", "竖向主体布局提示", 768, 1024, "vertical visual emphasis, strong foreground subject"),
    "landscape": CompositionPreset("landscape", "横向层次布局提示", 1024, 576, "wide scenic emphasis, layered depth"),
    "object": CompositionPreset("object", "主体居中留白提示", 1024, 1024, "centered object, clean negative space"),
}


def ensure_runtime_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    STYLE_REFS_DIR.mkdir(parents=True, exist_ok=True)


def get_style(style_id: Optional[str]) -> StyleConfig:
    if style_id and style_id in STYLE_LIBRARY:
        return STYLE_LIBRARY[style_id]
    return STYLE_LIBRARY["zhuxianzhen"]


def get_output_preset(output_type: Optional[str]) -> OutputPreset:
    if output_type and output_type in OUTPUT_PRESETS:
        return OUTPUT_PRESETS[output_type]
    return OUTPUT_PRESETS["poster"]


def get_composition_preset(composition_mode: Optional[str]) -> CompositionPreset:
    if composition_mode and composition_mode in COMPOSITION_PRESETS:
        return COMPOSITION_PRESETS[composition_mode]
    return COMPOSITION_PRESETS["portrait"]


def resolve_style_ref_path(style: StyleConfig) -> Optional[Path]:
    candidate = STYLE_REFS_DIR / style.filename
    return candidate if candidate.exists() else None


def missing_style_refs() -> list[str]:
    return [style.filename for style in STYLE_LIBRARY.values() if resolve_style_ref_path(style) is None]


def style_refs_ready() -> bool:
    return not missing_style_refs()
