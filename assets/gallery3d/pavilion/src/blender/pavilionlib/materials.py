"""材质库 —— Metallic-Roughness 工作流 + ORM 打包 + glTF 遮挡通道。

设计要点
--------
* 每个材质 key 对应 **一张 ORM 贴图**：R=AO / G=Roughness / B=Metallic（任务书 §3.3）。
* ORM 同时接：SeparateColor.G→Roughness、.B→Metallic，以及
  `glTF Material Output`.Occlusion→R，使 Blender glTF 导出器把 occlusion 与
  metallicRoughness 指向**同一个 image**，Three.js 侧只需一次纹理请求即可拿到 aoMap。
* 贴图缺失时自动回退到纯色常量，保证建模阶段可无贴图运行。
"""
from __future__ import annotations

import os

import bpy

TEX_DIR = r"D:\Design\textures"

# ---------------------------------------------------------------- 材质定义
# key: (中文名, basecolor(hex), roughness, metallic, tex_size)
# 2026-11-09 全案重构：晴和天章 —— 严禁死黑花岗岩 / 炭化黑木 / 黑冷死水。
MAT_META = {
    "roof_dai":   ("宋韵青灰琉璃瓦",       "#87949B", 0.74, 0.02, 2048),
    "wood_dark":  ("温润金丝楠木",         "#8A6A4C", 0.58, 0.00, 2048),
    "wood_lite":  ("银杏黄暖木构件",       "#C6A87F", 0.50, 0.00, 2048),
    "wall_white": ("羊脂温玉暖白微水泥",   "#FBF7EF", 0.80, 0.00, 2048),
    "stone_dark": ("青灰玄武岩铺装",       "#9AA4A8", 0.52, 0.00, 2048),
    "stone_lite": ("汉白玉暖石",           "#F2EFE6", 0.45, 0.00, 1024),
    "water":      ("澄澈影青水体",         "#5FA0B4", 0.04, 0.05, 1024),
    "glass":      ("影青透光玉石屏扇",     "#B7D2CC", 0.12, 0.00, 1024),
    "bronze":     ("宋韵鎏金沉香细部",     "#DDB25C", 0.35, 0.88, 1024),
    "crimson":    ("故宫典雅朱砂大漆",     "#C0453A", 0.42, 0.05, 1024),
    "celadon":    ("宋画青绿彩画·远山",    "#5C9A97", 0.62, 0.00, 1024),
    # 远山专用两档：自发光做「空气透视退晕」，否则背光坡在 EEVEE 里会黑成一片
    "mount_near": ("远景青绿山峦·近层",    "#3E7C79", 0.95, 0.00, 1024),
    "mount_far":  ("远景青绿山峦·远层",    "#86ADAB", 0.95, 0.00, 1024),
    # 八期：泥金脊线 / 塔刹 ——《千里江山图》"青绿设色、泥金染脊"的工笔金线
    "mount_gold": ("远山泥金脊线",          "#C9A227", 0.42, 0.55, 512),
    # 第九期：门匾的黑漆底。wood_dark 是暖栗褐，"黑底金字"会读成棕底；
    # 单独给一种近无反射的黑漆（不生成贴图，纯色即可），5 面匾共用一个 draw call。
    "lacquer":    ("黑漆匾底",              "#0E0B09", 0.22, 0.00, 512),
    "foliage":    ("苍翠罗汉松针叶",       "#264B38", 0.75, 0.00, 1024),
    "cloud":      ("飘逸层云",             "#FFF8E7", 0.92, 0.00, 512),
    "mist":       ("山脚薄雾",             "#D9EDEF", 0.98, 0.00, 512),
    "pond":       ("暖青灰池底微晶石",     "#8A9A96", 0.55, 0.00, 512),
    "silk":       ("朱红月白丝光织锦",     "#C0402F", 0.55, 0.00, 512),
    # 画心／绢本：暖米色旧宣纸，比 wall_white 明显偏黄，室内挂画不再是白纸
    "xuan":       ("宣纸绢本画心",         "#E7DBC0", 0.88, 0.00, 512),
    # 室内地面：暖灰方砖，与室外汉白玉台明区分，避免室内一片纯白
    "brick":      ("室内暖灰方砖",         "#B4A996", 0.72, 0.00, 1024),
    "lightstrip": ("洗墙光带（自发光）",   "#FFE9C8", 0.50, 0.00, 512),
}

# v15 craft materials: portable Principled constants, no misleading stone/bronze aliases.
MAT_META.update({
    "silk_raw": ("素绢生绢", "#EDE6D6", .72, 0., 512),
    "paper_xuan": ("宣纸连史纸", "#F2EDE0", .90, 0., 512),
    "steel": ("精钢", "#C9CFD4", .22, 1., 512),
    "brass": ("黄铜", "#B4894A", .34, 1., 512),
    "amber": ("蜂蜡", "#C6862F", .42, 0., 512),
    "cobalt": ("青花钴料浓", "#274B8E", .55, 0., 512),
    "cobalt_pale": ("青花钴料淡", "#7E9BC8", .62, 0., 512),
    "bamboo": ("竹黄", "#C9B27A", .62, 0., 512),
    "jade": ("白玉", "#E6EBE2", .30, 0., 512),
    "clay_wet": ("湿泥坯", "#8A6B53", .30, 0., 512),
    "bisque": ("素坯白胎", "#EDE8DD", .82, 0., 512),
    "malachite": ("孔雀石石绿", "#2E7D5B", .35, 0., 512),
    "azurite": ("蓝铜矿石青", "#1F3F8C", .35, 0., 512),
    "mineral_ochre": ("赭石颜料", "#A4613D", .74, 0., 256),
    "thread_pale": ("浅色丝线", "#E8B9A8", .55, 0., 256),
    "thread_rose": ("中色丝线", "#C85A5A", .55, 0., 256),
    "thread_deep": ("深色丝线", "#8E2B33", .55, 0., 256),
})


def _ramp_hex(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    return "#" + "".join(f"{round(int(a[i:i+2],16)*(1-t)+int(b[i:i+2],16)*t):02X}"
                          for i in (0, 2, 4))


for _i in range(24):
    _t = _i / 23
    _col = (_ramp_hex("#F0D4B6", "#C85A5A", _t*2) if _t <= .5
            else _ramp_hex("#C85A5A", "#572C50", (_t-.5)*2))
    MAT_META[f"thread_{_i:02d}"] = (f"丝线色阶{_i+1:02d}", _col, .48, 0., 256)
for _i in range(5):
    MAT_META[f"cobalt_{_i}"] = (f"青料浓度{_i+1}",
        _ramp_hex("#AFBED3", "#274B8E", _i/4), .58, 0., 256)

MAT_ORDER = list(MAT_META.keys())


def _hex(h: str):
    h = h.lstrip("#")
    srgb = tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return tuple(lin(c) for c in srgb) + (1.0,)


def _gltf_output_group():
    """创建/获取 glTF Material Output 节点组（导出器识别 Occlusion 的钩子）。"""
    name = "glTF Material Output"
    grp = bpy.data.node_groups.get(name)
    if grp:
        return grp
    grp = bpy.data.node_groups.new(name, "ShaderNodeTree")
    grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketShader")
    gin = grp.nodes.new("NodeGroupInput")
    gout = grp.nodes.new("NodeGroupOutput")
    for i, nd in enumerate((gin, gout)):
        nd.location = (-260 + i * 520, 0)
    return grp


def _load(path):
    if not path or not os.path.exists(path):
        return None
    try:
        return bpy.data.images.load(path, check_existing=True)
    except Exception:
        return None


def _find(tex_dir, key, attr, prefer_png=False):
    """按 .jpg → .png 找贴图。发布版走 jpg（体积小 4~8 倍），源版走 png。"""
    # 贴图别名：远山两档直接复用 celadon 的贴图，避免为背景多生成两套 1024 图
    key = TEX_ALIAS.get(key, key)
    for ext in ((".png", ".jpg") if prefer_png else (".jpg", ".png")):
        p = os.path.join(tex_dir, f"{key}_{attr}{ext}")
        if os.path.exists(p):
            return p
    return None


# 贴图别名表：材质键 → 实际使用的贴图键
# 八期起远山有了自己的「石骨」法线贴图（mount_near_normal / mount_far_normal），
# 不再借用 celadon 的彩画纹（那套横细带铺到 400m 山体上会拉成巨大的斜条纹）。
TEX_ALIAS = {}


# ---------------------------------------------------------------- UV 通道契约
# UV0 = "UVMap"  ：uv_box_project 的按米平铺 UV（basecolor / normal / MR 用它）
# UV1 = "UVMap2" ：uv1_lightmap 生成的非重叠 lightmap UV（AO 必须用它，否则 UV0 重叠
#                  会让同一像素被多个面共用，AO 直接错乱）
UV_TILE = "UVMap"
UV_LIGHT = "UVMap2"


def _uv_node(nt, uv_name, loc=(-900, 0)):
    """取/建指定 UV 通道的 UV Map 节点（同名复用，避免重复建）。"""
    nm = "UVC_" + uv_name
    n = nt.nodes.get(nm)
    if n is None:
        n = nt.nodes.new("ShaderNodeUVMap")
        n.name = nm
        n.uv_map = uv_name
        n.location = loc
    return n


def _wire_orm(nt, bsdf, grp, orm_img):
    """ORM 单图双通道接线。

    同一张图喂两处：
      * T_ORM    取样 UV0 → SeparateColor → G=Roughness, B=Metallic
      * T_ORM_AO 取样 UV1 → SeparateColor → R → glTF Material Output.Occlusion
    两个 Image 节点指向**同一个 bpy image**，所以 GLB 里 image 只存一份，
    而 occlusionTexture 拿到 texCoord=1、metallicRoughnessTexture 拿到 texCoord=0
    —— 这正是 glTF 允许的「同图不同 UV 通道」写法，Three.js 按 texture.channel 生效。
    """
    for nm in ("T_ORM", "T_ORM_AO", "SEP_ORM", "SEP_ORM_AO"):
        old = nt.nodes.get(nm)
        if old:
            nt.nodes.remove(old)
    if orm_img.colorspace_settings.name != "Non-Color":
        orm_img.colorspace_settings.name = "Non-Color"

    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.name = "T_ORM"
    tn.image = orm_img
    tn.location = (-700, -120)
    nt.links.new(_uv_node(nt, UV_TILE, (-920, -120)).outputs["UV"], tn.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    sep.name = "SEP_ORM"
    sep.location = (-420, -120)
    nt.links.new(tn.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])

    tn2 = nt.nodes.new("ShaderNodeTexImage")
    tn2.name = "T_ORM_AO"
    tn2.image = orm_img
    tn2.location = (-700, -360)
    nt.links.new(_uv_node(nt, UV_LIGHT, (-920, -360)).outputs["UV"], tn2.inputs["Vector"])
    sep2 = nt.nodes.new("ShaderNodeSeparateColor")
    sep2.name = "SEP_ORM_AO"
    sep2.location = (-420, -360)
    nt.links.new(tn2.outputs["Color"], sep2.inputs["Color"])

    gnode = nt.nodes.get("GLTF_OCC")
    if gnode is None:
        gnode = nt.nodes.new("ShaderNodeGroup")
        gnode.node_tree = grp
        gnode.name = "GLTF_OCC"
        gnode.location = (-160, -360)
    for l in list(gnode.inputs["Occlusion"].links):
        nt.links.remove(l)
    nt.links.new(sep2.outputs["Red"], gnode.inputs["Occlusion"])


def build_materials(tex_dir: str = TEX_DIR) -> dict:
    """建立全部材质。已有贴图则接线，否则用纯色回退。返回 {key: Material}。"""
    grp = _gltf_output_group()
    out = {}
    for key in MAT_ORDER:
        cn, hexc, rough, metal, size = MAT_META[key]
        mat = bpy.data.materials.get(key) or bpy.data.materials.new(key)
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()

        outp = nt.nodes.new("ShaderNodeOutputMaterial")
        outp.location = (760, 0)
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (420, 0)
        nt.links.new(bsdf.outputs["BSDF"], outp.inputs["Surface"])

        base_img = _load(_find(tex_dir, key, "basecolor"))
        orm_img = _load(_find(tex_dir, key, "orm"))
        nrm_img = _load(_find(tex_dir, key, "normal"))
        if key in ("mount_near", "mount_far", "mist"):
            # 远山不贴 basecolor/orm：青绿靠自发光色阶出"画意"，贴彩画纹会被拉成巨大斜条纹。
            # 但八期起要给远山接一张**石骨法线**（层理 + 皴纹），否则 400m 的山是一张光滑幕布。
            base_img = orm_img = None
            if key == "mist":
                nrm_img = None

        col = _hex(hexc)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.45
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = 1.0

        # ---- BaseColor（走 UV0 平铺 UV）
        if base_img:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.name = "T_BaseColor"
            tn.image = base_img
            tn.location = (-160, 260)
            if base_img.colorspace_settings.name != "sRGB":
                base_img.colorspace_settings.name = "sRGB"
            nt.links.new(_uv_node(nt, UV_TILE, (-380, 260)).outputs["UV"], tn.inputs["Vector"])
            nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
        # ---- ORM（单图双通道：MR 走 UV0，AO 走 UV1）
        if orm_img:
            if orm_img.colorspace_settings.name != "Non-Color":
                orm_img.colorspace_settings.name = "Non-Color"
            _wire_orm(nt, bsdf, grp, orm_img)
        # ---- Normal
        if nrm_img:
            if nrm_img.colorspace_settings.name != "Non-Color":
                nrm_img.colorspace_settings.name = "Non-Color"
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.name = "T_Normal"
            tn.image = nrm_img
            tn.location = (-420, 520)
            nt.links.new(_uv_node(nt, UV_TILE, (-640, 520)).outputs["UV"], tn.inputs["Vector"])
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.location = (-120, 520)
            nm.inputs["Strength"].default_value = 1.0
            nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

        # ---- 特殊材质属性
        if key == "glass":
            # 影青透光玉石屏扇：透光率 45%（Alpha 0.45），不做镜面反射。
            # IOR 压到 1.15，避免斜视角 Fresnel 把整片天空反成白板。
            bsdf.inputs["Alpha"].default_value = 0.45
            if "IOR" in bsdf.inputs:
                bsdf.inputs["IOR"].default_value = 1.15
            mat.blend_method = "BLEND"
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = "NONE"
            mat.use_backface_culling = False
        elif key == "water":
            bsdf.inputs["Roughness"].default_value = 0.04
            bsdf.inputs["Metallic"].default_value = 0.05
        elif key == "cloud":
            # 层云：自发光一点点，让向阳面保持轻盈通透，不靠环境光吃饭；
            # 再给 0.62 半透明，云缘才不会在蓝天上切出一条硬多边形边
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (1.0, 0.973, 0.906, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.55
            bsdf.inputs["Alpha"].default_value = 0.62
            mat.blend_method = "BLEND"
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = "NONE"
            mat.use_backface_culling = False
        elif key in ("mount_near", "mount_far"):
            # 远山：靠自发光做「空气透视」。远层比近层更亮更淡，形成层峦退晕；
            # 同时把高光压掉（Roughness 0.95 / Metallic 0），山体只留轮廓与色阶。
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = col
                bsdf.inputs["Emission Strength"].default_value = (
                    0.90 if key == "mount_near" else 1.35
                )
            # 山体只靠自发光出"画出来的颜色"：基色压到近黑，太阳照上去也不发白。
            # （此前基色=青绿 + 强日光 → 渲出 194,208,210 的"冰川白"，与宋画无关。）
            if "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.02, 0.03, 0.03, 1.0)
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.08
        elif key == "mount_gold":
            # 泥金脊线：金底 + 一点自发光，让 300~450m 外的那道棱线在日光里仍能"亮起来"。
            # 自发光刻意压得很低（0.30），过强就成了霓虹灯条，与宋画的"极微弱金辉"不符。
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = col
                bsdf.inputs["Emission Strength"].default_value = 0.30
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.55
        elif key == "mist":
            # 山脚薄雾：横向贴在山与水交界处的一层雾幔，用半透明 + 自发光把
            # 山体插进水面的"刀切锐角"糊掉。比层云更淡、更低、几乎不吃光。
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.90, 0.95, 0.96, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 0.55
            bsdf.inputs["Alpha"].default_value = 0.16
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.02
            mat.blend_method = "BLEND"
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = "NONE"
            mat.use_backface_culling = False
        elif key == "silk":
            # 丝光织锦垂帘：半透明（0.55），双面可见
            bsdf.inputs["Alpha"].default_value = 0.55
            if "IOR" in bsdf.inputs:
                bsdf.inputs["IOR"].default_value = 1.20
            mat.blend_method = "BLEND"
            if hasattr(mat, "surface_render_method"):
                mat.surface_render_method = "BLENDED"
            if hasattr(mat, "shadow_method"):
                mat.shadow_method = "NONE"
            mat.use_backface_culling = False
        elif key == "crimson":
            if "Coat Weight" in bsdf.inputs:
                bsdf.inputs["Coat Weight"].default_value = 0.20
                bsdf.inputs["Coat Roughness"].default_value = 0.15
        elif key == "lightstrip":
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (1.0, 0.90, 0.76, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 2.4
        elif key == "roof_dai":
            # 琉璃瓦油润层。Coat 0.18/0.14 时沿每条瓦垄拉出白色镜面线，
            # 整片屋面读成"抛光不锈钢"；降到 0.06/0.32 仍是釉面。
            # Specular IOR Level 0.5→0.22 是关键一步：瓦垄是完美圆柱，
            # 默认镜面反射率在低太阳角下让每条脊都成一根白线，压到 0.22
            # 后高光只留在檐口受光面，青黛色才立得住。
            if "Coat Weight" in bsdf.inputs:
                bsdf.inputs["Coat Weight"].default_value = 0.03
                bsdf.inputs["Coat Roughness"].default_value = 0.38
            if "Specular IOR Level" in bsdf.inputs:
                bsdf.inputs["Specular IOR Level"].default_value = 0.14

        # v15: sheen/transmission stay on Principled for portable glTF extensions.
        def _set(name, value):
            if name in bsdf.inputs:
                bsdf.inputs[name].default_value = value
        if key == "silk_raw" or key.startswith("thread_"):
            _set("Sheen Weight", .35)
            _set("Sheen Roughness", .55)
            _set("Anisotropic IOR Level", .45)
            if key == "silk_raw":
                _set("Transmission Weight", .08)
                _set("IOR", 1.35)
        elif key == "amber":
            _set("Transmission Weight", .12)
            _set("Subsurface Weight", .035)
            _set("IOR", 1.44)
        elif key == "clay_wet":
            _set("Coat Weight", .18)
            _set("Coat Roughness", .22)
        elif key == "jade":
            _set("Subsurface Weight", .035)

        mat["key"] = key
        mat["cn"] = cn
        out[key] = mat
    return out


def reload_textures(tex_dir: str = TEX_DIR, prefer_png=False):
    """烘焙/生成贴图后重新接线（在管线末尾调用）。"""
    grp = _gltf_output_group()
    for key in MAT_ORDER:
        mat = bpy.data.materials.get(key)
        if not mat or not mat.use_nodes:
            continue
        nt = mat.node_tree
        bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is None:
            continue
        cn, hexc, rough, metal, size = MAT_META[key]

        def _wire(attr, fname, socket, is_color=True, normal=False):
            old = nt.nodes.get(fname)
            if old:
                nt.nodes.remove(old)
            img = _load(_find(tex_dir, key, attr, prefer_png=prefer_png))
            if not img:
                return None
            if img.colorspace_settings.name != ("sRGB" if is_color and not normal else "Non-Color"):
                img.colorspace_settings.name = "sRGB" if (is_color and not normal) else "Non-Color"
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.name = fname
            tn.image = img
            tn.location = (-420, 300)
            return tn

        tn_base = _wire("basecolor", "T_BaseColor", "Base Color")
        if tn_base:
            nt.links.new(_uv_node(nt, UV_TILE, (-640, 300)).outputs["UV"], tn_base.inputs["Vector"])
            nt.links.new(tn_base.outputs["Color"], bsdf.inputs["Base Color"])
        orm_img = _load(_find(tex_dir, key, "orm", prefer_png=prefer_png))
        if orm_img:
            _wire_orm(nt, bsdf, grp, orm_img)
        tn_nrm = _wire("normal", "T_Normal", "Normal", is_color=False, normal=True)
        if tn_nrm:
            nt.links.new(_uv_node(nt, UV_TILE, (-640, 520)).outputs["UV"], tn_nrm.inputs["Vector"])
            nm = next((n for n in nt.nodes if n.type == "NORMAL_MAP"), None)
            if nm is None:
                nm = nt.nodes.new("ShaderNodeNormalMap")
                nm.location = (-120, 520)
            nt.links.new(tn_nrm.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
