# -*- coding: utf-8 -*-
"""逐件对比：点击前 / 互动中 / 复位后 三张截图在器物附近的像素变化。

用法： D:\wenmai-huazhang\backend\venv\Scripts\python.exe diff14.py
前提：先跑 accept14b.mjs 生成 accept14.json 与 asset-<ID>*.png
"""
import json
import os

from PIL import Image, ImageChops

SCREENS = r"D:\wenmai-huazhang\docs\heritage_gallery\screens"
DATA = r"D:\Codex\wenmai-verify\accept14.json"
OUT = r"D:\Codex\wenmai-verify\diff14.json"


def load(name):
    path = os.path.join(SCREENS, name + ".png")
    if not os.path.exists(path):
        return None
    return Image.open(path).convert("RGB")


def diff_stats(a, b, box, threshold=12):
    if a is None or b is None:
        return None
    crop_a = a.crop(box)
    crop_b = b.crop(box)
    if crop_a.size != crop_b.size:
        return None
    delta = ImageChops.difference(crop_a, crop_b).convert("L")
    pixels = list(delta.getdata())
    changed = sum(1 for value in pixels if value > threshold)
    return {
        "ratio": round(changed / max(1, len(pixels)), 4),
        "px": changed,
        "max": max(pixels) if pixels else 0,
    }


def main():
    with open(DATA, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = []
    for record in payload["results"]:
        asset_id = record["id"].replace("DIY_", "")
        proj = record.get("projected") or {}
        before = load(f"{asset_id}-before")
        active = load(f"asset-{asset_id}")
        reset = load(f"asset-{asset_id}-reset")
        if before is None or active is None:
            rows.append({"id": asset_id, "skipped": True, "reason": "missing screenshot"})
            continue
        width, height = before.size
        if proj.get("inView"):
            cx, cy = int(proj["x"]), int(proj["y"])
            box = (
                max(0, cx - 130),
                max(0, cy - 150),
                min(width, cx + 130),
                min(height, cy + 150),
            )
        else:
            box = (0, 0, width, height)
        rows.append(
            {
                "id": asset_id,
                "name": record.get("name"),
                "placeY": record.get("placed", {}).get("y") if record.get("placed") else None,
                "surface": record.get("placed", {}).get("surface") if record.get("placed") else None,
                "parent": bool(record.get("placed", {}).get("parent")) if record.get("placed") else False,
                "hoverHint": record.get("hover"),
                "stateAfterClick": record.get("afterClick"),
                "stateAfterReset": record.get("afterReset"),
                "cardAfterClick": record.get("card"),
                "cardAfterClose": record.get("cardAfter"),
                "pixelChangedRatio": (diff_stats(before, active, box) or {}).get("ratio"),
                "pixelChangedPx": (diff_stats(before, active, box) or {}).get("px"),
                "maxChannelDelta": (diff_stats(before, active, box) or {}).get("max"),
                "resetVsBeforeRatio": (diff_stats(before, reset, box) or {}).get("ratio")
                if reset is not None
                else None,
                "note": record.get("note"),
            }
        )
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=1)
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()