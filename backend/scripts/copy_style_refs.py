from __future__ import annotations

import shutil
from pathlib import Path


STYLE_REF_FILES = [
    "zhuxianzhen.png",
    "bianxiu.png",
    "songhua.png",
    "qinghua.png",
    "jianzhi.png",
]

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_PUBLIC_DIR = PROJECT_ROOT / "frontend" / "public"
STYLE_REFS_DIR = BACKEND_DIR / "style_refs"


def main() -> int:
    print("复制非遗风格参考图")
    print(f"来源目录: {FRONTEND_PUBLIC_DIR}")
    print(f"目标目录: {STYLE_REFS_DIR}")

    STYLE_REFS_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    copied = 0

    for filename in STYLE_REF_FILES:
        source = FRONTEND_PUBLIC_DIR / filename
        target = STYLE_REFS_DIR / filename

        if not source.exists():
            missing.append(filename)
            print(f"[缺失] {filename}: frontend/public 中未找到")
            continue

        action = "覆盖" if target.exists() else "复制"
        shutil.copy2(source, target)
        copied += 1
        print(f"[{action}] {filename} -> {target}")

    print(f"完成: 已处理 {copied}/{len(STYLE_REF_FILES)} 张参考图")
    if missing:
        print("缺失文件:")
        for filename in missing:
            print(f"- {filename}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
