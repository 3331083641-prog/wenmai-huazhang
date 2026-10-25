"""把一张新生成的图，变成一件「可互动」的真实案例。

一次调用做完全部步骤：
  1. 落盘成标准案例目录 docs/examples/<slug>/（generated.png + metadata.json）
  2. Qwen3-VL 读取实际成图，产生专属观察、热点、三折章节及微动类别
  3. 为同一图片生成深度与热点镜头配置（自动定位标 approximate）
  4. 写出 experience.json（前端自动加载，无需改代码）
  5. 调 build_painting_world.py 生成画境资产（深度网格 / 遮罩 / 抠像 / world.json）
  6. 回写 metadata.json 的 experienceId，并写一份 ingest-report.json

设计边界（必须诚实写在报告与 UI 里）：
  * 热点坐标是**自动估计**的，不是逐点裁切复核过的；因此 locationStatus=approximate、
    reviewStatus=pending，前端会把它们显示为「待复核」。
  * 视觉模型按本图生成观察和审美解读；风格知识仅用于文化背景，不套用通用章节。
  * 深度是单图估计，只能给前后关系，不是三维重建。

用法：
  python scripts/interactive/ingest_case.py \
      --image D:\\out\\new.png --slug zx-20261021-a --style-id zhuxianzhen \
      --title "瑞猫迎春·新作" [--no-vlm] [--skip-world] [--force]

  # 已有案例重新生成互动内容
  python scripts/interactive/ingest_case.py --refresh zhuxianzhen-20261021-153012-ab12
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = PROJECT_ROOT / "docs" / "examples"
BUILDER = PROJECT_ROOT / "scripts" / "interactive" / "build_painting_world.py"
PUBLIC_WORLD = PROJECT_ROOT / "frontend" / "public" / "interactive"
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
from dotenv import load_dotenv
load_dotenv(Path(os.getenv("WENMAI_ENV_FILE") or PROJECT_ROOT / "backend" / ".env"), override=False, encoding="utf-8-sig")
from services.interaction_plan import InteractionPlanService, assemble_experience

# --------------------------------------------------------------------------- #
# 风格知识包：新图沿用同风格的来源编号与背景资料，不编造文化事实
# --------------------------------------------------------------------------- #
STYLES: dict[str, dict] = {
    "zhuxianzhen": {
        "name": "朱仙镇木版年画",
        "accent": "#9E241B", "accentSoft": "#E8C9A0", "paper": "#F6EFE3",
        "ink": "#3F2B1F", "gold": "#B98B4E",
        "sources": ["SRC-ZXZ-NIANHUA-001", "SRC-ZXZ-CRAFT-002"],
        "kicker": "线刻转译",
        "explain": "朱仙镇木版年画以线版立形、多版套色，造型饱满、色彩浓烈，2006 年列入第一批国家级非物质文化遗产名录。",
    },
    "bianxiu": {
        "name": "汴绣",
        "accent": "#7B4B8A", "accentSoft": "#E7D3EA", "paper": "#F7F2F4",
        "ink": "#3A2A33", "gold": "#B08A5E",
        "sources": ["SRC-BX-KAIFENG-001"],
        "kicker": "针法特征",
        "explain": "汴绣以针代笔、以线晕色，讲究针脚走向随形体转折；2008 年列入国家级非物质文化遗产名录。",
    },
    "songhua": {
        "name": "宋画青绿山水",
        "accent": "#2F6B5E", "accentSoft": "#CBDCC8", "paper": "#F4F1E6",
        "ink": "#2A3630", "gold": "#A8894F",
        "sources": ["SRC-SH-QINGLU-001"],
        "kicker": "设色层次",
        "explain": "青绿山水以石青、石绿为主色，先墨骨后重彩，山体层层罩染，是宋画里最具装饰性的一路。",
    },
    "qinghua": {
        "name": "青花瓷纹样",
        "accent": "#22508F", "accentSoft": "#CBD9EC", "paper": "#F3F5F8",
        "ink": "#243040", "gold": "#9C8556",
        "sources": ["SRC-QH-JINGDEZHEN-001"],
        "kicker": "青料特征",
        "explain": "青花属釉下彩，以钴料在坯上绘纹、罩釉高温烧成；青花瓷是瓷器品种，本项目不将其表述为非物质文化遗产项目。",
    },
    "jianzhi": {
        "name": "中国剪纸",
        "accent": "#B03A2E", "accentSoft": "#F0CFC6", "paper": "#FBF3EF",
        "ink": "#3A2622", "gold": "#B98B4E",
        "sources": ["SRC-JZ-PAPER-001"],
        "kicker": "镂空语言",
        "explain": "剪纸以镂空成形、讲究纸筋相连；2006 年列入第一批国家级非物质文化遗产名录（Ⅶ-16），2009 年入选联合国教科文组织人类非遗代表作名录。",
    },
}


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", text.strip().lower()).strip("-")
    return cleaned or f"case-{int(time.time())}"


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# 深度（复用画境构建器的实现，保证两边口径一致）
# --------------------------------------------------------------------------- #
from depth_estimation import estimate_image_depth
DEPTH_SOURCE = ''
DEPTH_PROVENANCE = {}


def estimate_depth(image_path: Path, slug: str, gamma: float = 0.72, plan=None):
    """本图本地深度推理；仅显式 geometry 配置允许规则近似。"""
    global DEPTH_SOURCE, DEPTH_PROVENANCE
    raw, DEPTH_PROVENANCE = estimate_image_depth(image_path,plan)
    DEPTH_SOURCE = DEPTH_PROVENANCE['source']
    cache = PROJECT_ROOT / "scripts" / "interactive" / "_probe" / f"{slug}-depth.npy"
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, raw)
    return _smooth_depth(_normalise_depth(raw, gamma), 3.0)


def _normalise_depth(raw: np.ndarray, gamma: float) -> np.ndarray:
    lo, hi = np.percentile(raw, [2, 98])
    n = np.clip((raw - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    return np.power(n, gamma)


def _smooth_depth(depth: np.ndarray, radius: float = 3.0) -> np.ndarray:
    if radius <= 0:
        return depth
    img = Image.fromarray((np.clip(depth, 0.0, 1.0) * 255).astype(np.uint8))
    blur = img.filter(ImageFilter.GaussianBlur(radius))
    return np.asarray(blur, dtype=np.float32) / 255.0


def ingest(args) -> int:
    started = time.time()
    t0 = time.time()

    if args.refresh:
        folder = EXAMPLES_DIR / args.refresh
        if not folder.is_dir():
            log(f"✖ 找不到案例目录 {folder}")
            return 2
        slug = folder.name
        meta_path = folder / "metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path.exists() else {}
        style_id = str(args.style_id or meta.get("styleId") or "zhuxianzhen")
        title = str(args.title or meta.get("artworkTitle") or slug)
        image_path = folder / "generated.png"
        if not image_path.is_file():
            log(f"✖ {folder} 里没有 generated.png")
            return 2
    else:
        if not args.image:
            log("✖ 需要 --image 或 --refresh")
            return 2
        src = Path(args.image).expanduser().resolve()
        if not src.is_file():
            log(f"✖ 图片不存在：{src}")
            return 2
        style_id = str(args.style_id or "")
        if style_id not in STYLES:
            log(f"✖ --style-id 必须是 {', '.join(STYLES)} 之一")
            return 2
        slug = slugify(args.slug or src.stem)
        folder = EXAMPLES_DIR / slug
        if folder.exists() and not args.force:
            log(f"✖ 案例已存在：{folder}（加 --force 覆盖）")
            return 2
        folder.mkdir(parents=True, exist_ok=True)
        image_path = folder / "generated.png"
        with Image.open(src) as im:
            im.convert("RGB").save(image_path, format="PNG", optimize=True)
        title = str(args.title or slug)
        meta = {}
        log(f"1/6 落盘 {image_path.relative_to(PROJECT_ROOT)}  {image_path.stat().st_size / 1024:.0f} KB")

    with Image.open(image_path) as im:
        image = im.convert("RGB")
    W, H = image.size
    arr = np.asarray(image)
    log(f"    尺寸 {W}x{H}  风格 {style_id} / {STYLES[style_id]['name']}")

    # First parse THIS image. No generic style chapters or style-specific animal vocabulary.
    if args.no_vlm:
        raise RuntimeError("自动互动必须先完成 Qwen3-VL 成图解析，不能以无视觉模板冒充成功。")
    artifact = InteractionPlanService().analyze(image_path, STYLES[style_id], folder / "interaction-analysis.json")
    draft = assemble_experience(slug, style_id, STYLES[style_id], image.size, artifact)
    title = draft["title"]
    vlm_used = True
    log(f"2/6 Qwen3-VL 本图解析完成 sha256={artifact['inputImageSha256'][:12]}")

    depth = estimate_depth(image_path, slug, args.gamma, artifact['analysis'])
    log(f"3/6 深度完成（{DEPTH_SOURCE}）")
    if DEPTH_SOURCE == "image_geometry_v1":
        # 降级必须对用户可见：仍然能打开画境，但明确说明只有近似深度。
        draft["animation"]["world"]["depthNote"] = (
            "单图像素规则生成的近似深度，仅支持有限视差；"
            "不是三维重建，不调用其他深度或分割模型。"
        )
    exp_path = folder / "experience.json"
    exp_tmp = exp_path.with_suffix(".json.tmp")
    exp_tmp.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    exp_tmp.replace(exp_path)
    log(f"4/6 experience.json  {exp_path.stat().st_size / 1024:.1f} KB  "
        f"{len(draft['hotspots'])} 热点 / {len(draft['chapters'])} 折")

    # 5) 画境资产
    world_ok = False
    if not args.skip_world:
        # Pick a foreground detail from THIS depth map and model-grounded hotspots.
        def near_score(spot):
            x=min(depth.shape[1]-1,max(0,round(spot['x']*(depth.shape[1]-1))))
            y=min(depth.shape[0]-1,max(0,round(spot['y']*(depth.shape[0]-1))))
            return float(depth[max(0,y-8):y+9,max(0,x-8):x+9].mean())
        near_spot=max(artifact['analysis']['hotspots'],key=near_score)
        cfg = {
            "slug": slug,
            "title": title,
            "styleName": STYLES[style_id]["name"],
            "source": str(image_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sourceSha256": artifact["inputImageSha256"],
            "semanticMotion": artifact["analysis"]["motion_regions"],
            "depthSource": DEPTH_SOURCE,
            "sceneKind": artifact['analysis']['scene_kind'],
            "subjectSeed": {key:artifact['analysis']['hotspots'][0][key] for key in ('x','y')},
            "subjectLabel": artifact['analysis']['observed_subjects'][0],
            "depthAnchors": [{key: spot[key] for key in ('x','y','depth')} for spot in artifact['analysis']['hotspots']],
            "depthProvenance": DEPTH_PROVENANCE,
            "hotspots": [{"id": h["id"], "label": h["title"],
                          "x": h["geometry"]["cx"], "y": h["geometry"]["cy"],
                          "w": 0, "h": 0, "r": h["geometry"]["r"]} for h in draft["hotspots"]],
            "cutouts": [{"id":"subject","label":near_spot['title'],"depth_min":.58,
                "seed":{"x":near_spot['x'],"y":near_spot['y']},"half":{"w":.2,"h":.2}}],
        }
        cfg_path = PROJECT_ROOT / "scripts" / "interactive" / "_probe" / f"{slug}-config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [sys.executable, "-X", "utf8", str(BUILDER), "--config", str(cfg_path)]
        log("5/6 生成画境资产 …")
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, encoding="utf-8")
        tail = (proc.stdout or "").strip().splitlines()
        for line in tail[-6:]:
            log("    " + line)
        if proc.returncode != 0:
            log("    ✖ 画境构建失败：\n" + (proc.stderr or "")[-800:])
        else:
            world_ok = (PUBLIC_WORLD / slug / "world" / "world.json").is_file()

    # 6) 回写 metadata
    meta.update({
        "caseId": slug,
        "caseOrigin": "runtime",
        "experienceId": slug,
        "styleId": style_id,
        "styleName": STYLES[style_id]["name"],
        "artworkTitle": title,
        "generatedAt": meta.get("generatedAt") or datetime.now().astimezone().isoformat(),
        "generatedSha256": sha256(image_path),
        "generatedBytes": image_path.stat().st_size,
        "artworkSize": {"width": W, "height": H},
        "interactive": {
            "status": "ready" if world_ok else "partial",
            "experience": "experience.json",
            "world": f"frontend/public/interactive/{slug}/world/world.json" if world_ok else "",
            "hotspots": len(draft["hotspots"]),
            "hotspotMethod": "qwen3-vl-image-plan",
            "contentSource": "qwen3_vl_image",
            "analysisImageSha256": artifact["inputImageSha256"],
            "interactionPlanVersion": artifact["schemaVersion"],
            "depthSource": DEPTH_SOURCE,
            "builtAt": datetime.now().astimezone().isoformat(),
        },
    })
    (folder / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    world_dir = PUBLIC_WORLD / slug / "world"
    files = sorted(p.name for p in world_dir.glob("*")) if world_dir.is_dir() else []
    report = {
        "slug": slug,
        "styleId": style_id,
        "title": title,
        "image": {"width": W, "height": H, "bytes": image_path.stat().st_size},
        "depth": {
            "source": DEPTH_SOURCE,
            "provenance": DEPTH_PROVENANCE,
            "nearShare": round(float((depth > 0.8).mean()), 4),
            "farShare": round(float((depth < 0.35).mean()), 4),
            "percentiles": [round(float(v), 4) for v in np.percentile(depth, [2, 10, 50, 90, 98])],
            "gamma": args.gamma,
        },
        "hotspots": [{"id": h["id"], "title": h["title"], "x": h["geometry"]["cx"],
                      "y": h["geometry"]["cy"], "status": h["locationStatus"]} for h in draft["hotspots"]],
        "chapters": [{"id": c["id"], "scale": c["frame"]["scale"]} for c in draft["chapters"]],
        "world": {"built": world_ok, "files": files,
                  "bytes": sum((world_dir / f).stat().st_size for f in files) if files else 0},
        "vlm": {"used": True, "model": artifact["model"],
                "inputImageSha256": artifact["inputImageSha256"], "contentSource": "qwen3_vl_image"},
        "warnings": ([w for w in [
            "热点为模型自动定位，可直接体验，不冒充人工逐点复核。",
            "热点与章节来自本图 Qwen3-VL 解析；自动观察和审美解读仍可能有偏差。",
            "画境仅用图像像素规则生成近似深度，不调用其他模型，只提供有限视差。" if DEPTH_SOURCE == "image_geometry_v1" else "",
        ] if w]),
        "elapsedSec": round(time.time() - started, 1),
    }
    (folder / "ingest-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Metadata and local assets must exist before the disposable browser reads this case.
    # A cloud reviewer failure cannot delete a successful generated work or local interactions.
    if world_ok:
        from world_quality import review_world,write_json
        try:
            quality=review_world(slug,style_id)
        except Exception as exc:
            quality={'status':'unverified','rounds':0,'improved':False,'errorType':type(exc).__name__,
                'note':'画境保留；云端视觉复审未完成，不计作质量通过。'}
            write_json(folder/'quality-review.json',quality)
            current_meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8-sig'))
            current_meta['qualityReview']=quality
            write_json(folder/'metadata.json',current_meta)
        report['qualityReview']={key:value for key,value in quality.items() if key not in ('history',)}
        write_json(folder/'ingest-report.json',report)
        log('    DeepSeek视觉复审：'+str(quality['status'])+'；轮数 '+str(quality.get('rounds',0)))

    log(f"6/6 完成  {slug}  用时 {report['elapsedSec']}s")
    log(f"    三入口：/experience/{slug} · /story/{slug} · /wander/{slug}")
    for warn in report["warnings"]:
        log("    ! " + warn)
    if not world_ok and not args.skip_world:
        log("    ✖ 画境资产未生成，画境漫游入口不会出现（本次按失败返回）")
        return 4
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="把新生成的图变成带三重互动的真实案例")
    ap.add_argument("--image", help="新生成的图片路径")
    ap.add_argument("--slug", help="案例目录名（默认取文件名）")
    ap.add_argument("--title", help="作品标题")
    ap.add_argument("--style-id", choices=sorted(STYLES), help="风格（决定文案口径与来源编号）")
    ap.add_argument("--hotspots", type=int, default=5, help="自动热点数量（4–6）")
    ap.add_argument("--gamma", type=float, default=0.72)
    ap.add_argument("--no-vlm", action="store_true", help="兼容旧参数；本图互动要求视觉解析，指定此项会明确拒绝构建")
    ap.add_argument("--skip-world", action="store_true", help="只生成 experience.json，不建画境资产")
    ap.add_argument("--refresh", help="对已有案例目录重新生成互动内容")
    ap.add_argument("--force", action="store_true", help="覆盖已有案例目录")
    args = ap.parse_args()
    args.hotspots = int(np.clip(args.hotspots, 4, 6))
    return ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
