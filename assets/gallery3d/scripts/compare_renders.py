"""Run the reference measurement pipeline on our own renders and diff it.

  python compare_renders.py
Prints one compact line per render plus a delta table against the measured
reference exteriors. This is the defined measurement method for fidelity: it
never claims more than silhouette / coverage / palette / band statistics.
"""
from __future__ import annotations

import glob
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import measure_v2 as M  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDERS = os.path.join(HERE, "renders")
REF_SUMMARY = os.path.join(HERE, "references", "analysis2", "summary.json")


def stats(path):
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im, dtype=np.float64)
    h, w = arr.shape[:2]
    bg = M.flood_background(arr)
    fg = ~bg
    labels = M.classify(arr)
    prof = M.extent_profile(fg, bands=40)
    sky = labels[fg] == "s"
    pal = M.quant_palette(arr[fg], k=12)
    ys, xs = np.where(fg)
    bbox = {"x0": float(xs.min()) / w, "y0": float(ys.min()) / h,
            "x1": float(xs.max()) / w, "y1": float(ys.max()) / h}
    return {
        "file": os.path.basename(path), "w": w, "h": h,
        "coverage_pct": round(100.0 * fg.mean(), 2),
        "sky_frac": round(float(sky.mean()), 3),
        "bg_frac": round(float(bg.mean()), 3),
        "bbox": {k: round(v, 3) for k, v in bbox.items()},
        "profile": [round(float(d["w"]), 3) for d in prof],
        "palette": appal(pal),
        "fill_by_row": [round(float(fg[i:i + h // 8].mean()), 3) for i in range(0, h, h // 8)],
    }


def appal(pal):
    out = []
    for c in pal:
        if isinstance(c, dict):
            out.append([c.get("hex"), round(float(c.get("pct", 0)), 1)])
        else:
            out.append(list(c))
    return out


def pal_overlap(a, b):
    """Share of the render palette that sits near a reference palette colour."""
    def rgb(h):
        h = h.lstrip("#")
        return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)
    ref = [rgb(h) for h, _ in a]
    score = 0.0
    for h, pct in b:
        c = rgb(h)
        d = min(np.linalg.norm(c - r) for r in ref)
        if d < 46.0:
            score += pct
    return round(score, 1)


def main():
    refs = {}
    if os.path.exists(REF_SUMMARY):
        with open(REF_SUMMARY, encoding="utf-8") as fh:
            for r in json.load(fh):
                refs[r["file"]] = r
    ext = [r for r in refs.values() if r["kind"] == "exterior"]
    print(f"reference exteriors: {len(ext)}")

    rows = []
    for p in sorted(glob.glob(os.path.join(RENDERS, "*.png"))):
        s = stats(p)
        rows.append(s)
        print(f"{s['file']:>16} cov={s['coverage_pct']:5.1f} sky={s['sky_frac']:.3f} "
              f"fill_rows={s['fill_by_row']}")

    print("\n--- delta vs mean reference exterior ---")
    if ext:
        m_cov = np.mean([r["coverage_pct"] for r in ext])
        m_sky = np.mean([r["sky_frac"] for r in ext])
        ref_pal = ext[0]["palette"]
        ref_pal = [[c["hex"], c["pct"]] for c in ref_pal]
        print(f"ref mean coverage={m_cov:.1f} sky={m_sky:.3f}")
        for s in rows[:6]:
            print(f"{s['file']:>16} dCov={s['coverage_pct'] - m_cov:+6.1f} "
                  f"dSky={s['sky_frac'] - m_sky:+.3f} palMatch={pal_overlap(ref_pal, s['palette'])}%")

    out = os.path.join(RENDERS, "render_stats.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()