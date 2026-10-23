"""Image I/O and numpy image primitives for the 纹脉华章 vision modules.

PIL is **not** available inside Blender's Python, so this module provides:

* ``read_png``  — loads a PNG through Blender's image API (fast C path) and
  returns an exact top-down ``uint8`` sRGB array.  Verified byte-identical to a
  pure-stdlib zlib/PNG decode (see ``docs/CONTRACT.md`` note in
  ``measurements.json``): Blender returns ``round(pixel * 255)`` for both the
  ``sRGB`` and ``Non-Color`` colour spaces on byte-buffer images.
* ``write_png`` — a dependency-free PNG writer (``zlib`` + ``struct``) using the
  ``Up`` row filter.  Used for every artifact this package produces so the
  bytes on disk are exactly the sRGB values we computed.
* ``png_header`` — pure-stdlib PNG dimension probe (used by ``check_export``).
* numpy primitives: resize, masks, Sobel, HSV/Lab, a 5x7 bitmap font and a
  contact-sheet builder.

Owned by ``visual-match``.  No third-party imports beyond ``numpy`` and the
standard library (``bpy`` is optional and only used for the fast PNG read).
"""
from __future__ import annotations

import math
import os
import struct
import zlib

import numpy as np

try:  # Blender is present in every real job; tolerate import for unit use.
    import bpy  # type: ignore
    _HAS_BPY = True
except Exception:  # pragma: no cover - only when run outside Blender
    bpy = None  # type: ignore
    _HAS_BPY = False


# ============================================================== PNG plumbing

_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_CT_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def png_header(path: str) -> dict:
    """Read a PNG's IHDR without any third-party library.

    Returns ``{"ok", "width", "height", "bitDepth", "colorType", "channels",
    "interlace", "bytes"}``; on a non-PNG or truncated file returns
    ``{"ok": False, "error": ...}``.
    """
    info = {"ok": False, "path": path, "bytes": 0}
    try:
        info["bytes"] = os.path.getsize(path)
        with open(path, "rb") as fh:
            head = fh.read(33)
    except OSError as exc:
        info["error"] = f"unreadable: {exc}"
        return info
    if len(head) < 33 or head[:8] != _PNG_SIG or head[12:16] != b"IHDR":
        info["error"] = "not a PNG (bad signature or missing IHDR)"
        return info
    w, h, bd, ct, comp, filt, inter = struct.unpack(">IIBBBBB", head[16:29])
    if ct not in _CT_CHANNELS:
        info["error"] = f"unsupported colour type {ct}"
        return info
    info.update(ok=True, width=int(w), height=int(h), bitDepth=int(bd),
                colorType=int(ct), channels=_CT_CHANNELS[ct],
                interlace=int(inter), compression=int(comp), filter=int(filt))
    return info


def _png_chunks(path: str):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != _PNG_SIG:
        raise ValueError("not a PNG")
    pos, out = 8, []
    while pos + 8 <= len(data):
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        typ = data[pos + 4:pos + 8]
        out.append((typ, data[pos + 8:pos + 8 + ln]))
        pos += 12 + ln
        if typ == b"IEND":
            break
    return out


def _unfilter(raw: bytes, w: int, h: int, ch: int, bd: int) -> np.ndarray:
    """Undo PNG row filtering (pure numpy; per-row loops only for Paeth)."""
    if bd != 8:
        raise NotImplementedError(f"only 8-bit PNG is supported (got {bd})")
    stride = w * ch
    buf = np.frombuffer(raw, dtype=np.uint8)
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.int32)
    off = 0
    for y in range(h):
        ft = int(buf[off]); off += 1
        line = buf[off:off + stride].astype(np.int32); off += stride
        if ft == 0:
            cur = line
        elif ft == 1:                      # Sub
            cur = line.copy()
            for i in range(ch, stride):
                cur[i] = (cur[i] + cur[i - ch]) & 255
        elif ft == 2:                      # Up
            cur = (line + prev) & 255
        elif ft == 3:                      # Average
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:                      # Paeth
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 255
        else:
            raise ValueError(f"unknown PNG filter {ft}")
        out[y] = cur.astype(np.uint8)
        prev = cur
    return out.reshape(h, w, ch)


def _read_png_stdlib(path: str) -> np.ndarray:
    """Fallback reader used only when Blender's image API is unavailable."""
    ihdr = png_header(path)
    if not ihdr.get("ok"):
        raise ValueError(f"cannot read PNG {path}: {ihdr.get('error')}")
    idat = b"".join(body for typ, body in _png_chunks(path) if typ == b"IDAT")
    planes = _unfilter(zlib.decompress(idat), ihdr["width"], ihdr["height"],
                       ihdr["channels"], ihdr["bitDepth"])
    if ihdr["colorType"] == 2:
        return np.ascontiguousarray(planes[:, :, :3])
    if ihdr["colorType"] == 6:
        rgb = planes[:, :, :3].astype(np.float32)
        a = planes[:, :, 3:4].astype(np.float32) / 255.0
        return np.clip(rgb * a + 255.0 * (1.0 - a) + 0.5, 0, 255).astype(np.uint8)
    if ihdr["colorType"] == 0:
        return np.repeat(planes, 3, axis=2)
    if ihdr["colorType"] == 4:
        g = planes[:, :, 0:1]
        return np.repeat(g, 3, axis=2)
    raise ValueError(f"unsupported colour type {ihdr['colorType']}")


def read_png(path: str) -> np.ndarray:
    """Return an ``(H, W, 3) uint8`` sRGB array, top row first."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if _HAS_BPY:
        img = None
        try:
            img = bpy.data.images.load(path, check_existing=False)
            img.colorspace_settings.name = "Non-Color"
            w, h = int(img.size[0]), int(img.size[1])
            if w <= 0 or h <= 0:
                raise ValueError("empty image buffer")
            buf = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(buf)
            arr = buf.reshape(h, w, 4)[::-1]           # Blender stores bottom-up
            return np.clip(arr[:, :, :3] * 255.0 + 0.5, 0, 255).astype(np.uint8)
        except Exception:
            pass
        finally:
            if img is not None:
                try:
                    bpy.data.images.remove(img)
                except Exception:
                    pass
    return _read_png_stdlib(path)


def read_png_rgba(path: str) -> np.ndarray:
    """Like :func:`read_png` but keeps a real alpha channel when present."""
    if _HAS_BPY:
        img = None
        try:
            img = bpy.data.images.load(path, check_existing=False)
            img.colorspace_settings.name = "Non-Color"
            w, h = int(img.size[0]), int(img.size[1])
            buf = np.empty(w * h * 4, dtype=np.float32)
            img.pixels.foreach_get(buf)
            arr = buf.reshape(h, w, 4)[::-1]
            return np.clip(arr * 255.0 + 0.5, 0, 255).astype(np.uint8)
        except Exception:
            pass
        finally:
            if img is not None:
                try:
                    bpy.data.images.remove(img)
                except Exception:
                    pass
    rgb = _read_png_stdlib(path)
    a = np.full(rgb.shape[:2] + (1,), 255, dtype=np.uint8)
    return np.concatenate([rgb, a], axis=2)


def write_png(path: str, arr) -> int:
    """Write ``arr`` (uint8 ``(H,W)``/``(H,W,3)``/``(H,W,4)``) as a PNG.

    The ``Up`` filter keeps compression reasonable while remaining a single
    vectorised numpy op per row.  Returns the number of bytes written.
    """
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = np.clip(np.rint(a), 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = a[:, :, None]
    if a.ndim != 3 or a.shape[2] not in (1, 3, 4):
        raise ValueError(f"unsupported array shape {a.shape}")
    h, w, ch = a.shape
    ct = {1: 0, 3: 2, 4: 6}[ch]

    raw = bytearray()
    prev = np.zeros((w, ch), dtype=np.int32)
    for y in range(h):
        row = a[y].astype(np.int32)
        raw.append(2)                                  # Up filter
        raw += ((row - prev) & 255).astype(np.uint8).tobytes()
        prev = row
    comp = zlib.compress(bytes(raw), 6)

    chunks = []
    for typ, body in ((b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ct, 0, 0, 0)),
                      (b"IDAT", comp),
                      (b"IEND", b"")):
        chunks.append(struct.pack(">I", len(body)) + typ + body
                      + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(_PNG_SIG)
        for chunk in chunks:
            fh.write(chunk)
    return os.path.getsize(path)


def file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def artifact(kind: str, path: str, **extra) -> dict:
    """Contract §2 artifact entry (absolute path + real byte count)."""
    item = {"kind": kind, "path": os.path.abspath(path), "bytes": file_size(path)}
    item.update(extra)
    return item


# ============================================================ array primitives

def as_float(arr) -> np.ndarray:
    return np.asarray(arr, dtype=np.float32)


def resize_bilinear(arr: np.ndarray, out_w: int, out_h: int) -> np.ndarray:
    """Corner-aligned bilinear resize; dtype preserving."""
    out_w, out_h = int(max(1, out_w)), int(max(1, out_h))
    src = np.asarray(arr)
    h, w = src.shape[:2]
    if (w, h) == (out_w, out_h):
        return src.copy()
    xs = np.linspace(0.0, w - 1.0, out_w)
    ys = np.linspace(0.0, h - 1.0, out_h)
    x0 = np.floor(xs).astype(np.int64); x1 = np.minimum(x0 + 1, w - 1)
    y0 = np.floor(ys).astype(np.int64); y1 = np.minimum(y0 + 1, h - 1)
    wx = (xs - x0)[None, :, None].astype(np.float32)
    wy = (ys - y0)[:, None, None].astype(np.float32)
    f = src.astype(np.float32)
    top = f[y0][:, x0] * (1.0 - wx) + f[y0][:, x1] * wx
    bot = f[y1][:, x0] * (1.0 - wx) + f[y1][:, x1] * wx
    out = top * (1.0 - wy) + bot * wy
    if np.issubdtype(src.dtype, np.integer):
        return np.clip(out + 0.5, 0, 255).astype(src.dtype)
    return out


def resample_into(src: np.ndarray, out_w: int, out_h: int, sx: float, sy: float,
                  tx: float, ty: float, fill: int = 255) -> np.ndarray:
    """Warp ``src`` so ``dst(x, y) = src((x - tx) / sx, (y - ty) / sy)``.

    Used by the comparison aligner to map a render's foreground onto the
    reference canvas.  Out-of-range samples become ``fill``.
    """
    src = np.asarray(src)
    h, w = src.shape[:2]
    ch = 1 if src.ndim == 2 else src.shape[2]
    xs = (np.arange(out_w, dtype=np.float32) - tx) / max(sx, 1e-9)
    ys = (np.arange(out_h, dtype=np.float32) - ty) / max(sy, 1e-9)
    valid_x = (xs >= 0) & (xs <= w - 1)
    valid_y = (ys >= 0) & (ys <= h - 1)
    xc = np.clip(xs, 0, w - 1); yc = np.clip(ys, 0, h - 1)
    x0 = np.floor(xc).astype(np.int64); x1 = np.minimum(x0 + 1, w - 1)
    y0 = np.floor(yc).astype(np.int64); y1 = np.minimum(y0 + 1, h - 1)
    wx = (xc - x0)[None, :, None].astype(np.float32)
    wy = (yc - y0)[:, None, None].astype(np.float32)
    f = src.astype(np.float32) if src.ndim == 3 else src.astype(np.float32)[:, :, None]
    top = f[y0][:, x0] * (1 - wx) + f[y0][:, x1] * wx
    bot = f[y1][:, x0] * (1 - wx) + f[y1][:, x1] * wx
    out = top * (1 - wy) + bot * wy
    ok = (valid_y[:, None] & valid_x[None, :])
    if not ok.all():
        out[~ok] = float(fill)
    if src.ndim == 2:
        out = out[:, :, 0]
    if np.issubdtype(src.dtype, np.integer):
        return np.clip(out + 0.5, 0, 255).astype(src.dtype)
    return out


def to_gray(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 3:
        a = a[:, :, :3]
        return a @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    return a


def rgb_to_hsv(arr: np.ndarray):
    a = np.asarray(arr, dtype=np.float32)
    r, g, b = a[..., 0] / 255.0, a[..., 1] / 255.0, a[..., 2] / 255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    d = np.maximum(mx - mn, 1e-6)
    h = np.zeros_like(mx)
    m = (mx == r)
    h[m] = (60.0 * ((g - b) / d) % 360.0)[m]
    m = (mx == g) & (mx != r)
    h[m] = (60.0 * ((b - r) / d) + 120.0)[m]
    m = (mx == b) & (mx != r) & (mx != g)
    h[m] = (60.0 * ((r - g) / d) + 240.0)[m]
    s = np.where(mx <= 1e-6, 0.0, d / np.maximum(mx, 1e-6))
    return h, s, mx


_M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]], dtype=np.float64)
_WHITE_D65 = np.array([0.95047, 1.00000, 1.08883], dtype=np.float64)


def rgb_to_lab(arr: np.ndarray) -> np.ndarray:
    """sRGB (uint8/float 0..255) -> CIE L*a*b* (D65), numpy only."""
    a = np.asarray(arr, dtype=np.float64) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    xyz = lin @ _M_RGB2XYZ.T
    t = xyz / _WHITE_D65
    d = 6.0 / 29.0
    f = np.where(t > d ** 3, np.cbrt(t), t / (3.0 * d * d) + 4.0 / 29.0)
    return np.stack([116.0 * f[..., 1] - 16.0,
                     500.0 * (f[..., 0] - f[..., 1]),
                     200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e76(lab_a: np.ndarray, lab_b: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((lab_a - lab_b) ** 2, axis=-1))


def lab_mean(arr: np.ndarray, mask: np.ndarray) -> list:
    lab = rgb_to_lab(arr)
    m = np.asarray(mask, dtype=bool)
    if not m.any():
        return [0.0, 0.0, 0.0]
    return [round(float(v), 3) for v in lab[m].mean(axis=0)]


_SOBEL_X = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
_SOBEL_Y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)


def _convolve3(gray: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    g = np.asarray(gray, dtype=np.float32)
    p = np.pad(g, 1, mode="edge")
    out = np.zeros_like(g)
    for dy in range(3):
        for dx in range(3):
            k = float(kernel[dy, dx])
            if k:
                out += k * p[dy:dy + g.shape[0], dx:dx + g.shape[1]]
    return out


def sobel(gray: np.ndarray):
    """Return ``(magnitude, angle_deg_0_180)`` for a 2-D luminance array."""
    gx = _convolve3(gray, _SOBEL_X)
    gy = _convolve3(gray, _SOBEL_Y)
    mag = np.sqrt(gx * gx + gy * gy)
    ang = np.degrees(np.arctan2(gy, gx)) % 180.0
    return mag, ang


def laplacian_energy(gray: np.ndarray) -> float:
    """High-pass energy: mean |Laplacian| normalised by (mean luminance + eps)."""
    g = np.asarray(gray, dtype=np.float32)
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    lap = np.abs(_convolve3(g, k))
    return float(lap.mean() / (float(g.mean()) + 1e-6))


def edge_density(gray: np.ndarray, mask: np.ndarray | None = None,
                 thresh: float = 24.0) -> float:
    """Fraction of (masked) pixels with Sobel magnitude above ``thresh``."""
    mag, _ = sobel(gray)
    sel = mag > thresh
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        if not m.any():
            return 0.0
        return float(sel[m].mean())
    return float(sel.mean())


def palette_hist(arr: np.ndarray, mask: np.ndarray | None = None, k: int = 12) -> list:
    """Deterministic 16-level histogram palette peaks in sRGB (no RNG)."""
    a = np.asarray(arr)
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        if not m.any():
            return []
        px = a[m]
    else:
        px = a.reshape(-1, a.shape[2]) if a.ndim == 3 else a.reshape(-1, 1)
    if px.size == 0:
        return []
    q = np.clip((px[:, :3].astype(np.int32) // 16) * 16 + 8, 0, 255)
    key = q[:, 0] * 65536 + q[:, 1] * 256 + q[:, 2]
    uniq, counts = np.unique(key, return_counts=True)
    order = np.argsort(-counts)[:k]
    total = float(counts.sum())
    out = []
    for i in order:
        kv = int(uniq[i])
        r, g, b = (kv >> 16) & 255, (kv >> 8) & 255, kv & 255
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b],
                    "pct": round(100.0 * float(counts[i]) / total, 2)})
    return out


def kmeans_palette(arr: np.ndarray, mask: np.ndarray | None = None, k: int = 8,
                   seed: int = 20261022, iters: int = 24, sample: int = 40000) -> list:
    """k-means over sRGB foreground pixels with a fixed RNG seed (deterministic).

    Uses k-means++ seeding from ``np.random.default_rng(seed)`` so repeated runs
    on identical input produce identical palettes.
    """
    a = np.asarray(arr)
    if mask is not None:
        m = np.asarray(mask, dtype=bool)
        if not m.any():
            return []
        px = a[m][:, :3].astype(np.float32)
    else:
        px = a.reshape(-1, a.shape[2])[:, :3].astype(np.float32)
    if px.shape[0] == 0:
        return []
    rng = np.random.default_rng(seed)
    if px.shape[0] > sample:
        idx = rng.choice(px.shape[0], size=sample, replace=False)
        px = px[idx]
    k = int(max(1, min(k, px.shape[0])))
    # k-means++ init
    centres = [px[rng.integers(px.shape[0])]]
    for _ in range(1, k):
        d2 = np.min(np.stack([np.sum((px - c) ** 2, axis=1) for c in centres]), axis=0)
        tot = float(d2.sum())
        if tot <= 0:
            centres.append(px[rng.integers(px.shape[0])])
        else:
            centres.append(px[int(np.searchsorted(np.cumsum(d2 / tot), rng.random()))])
    C = np.stack(centres).astype(np.float32)
    labels = None
    for _ in range(iters):
        d = np.stack([np.sum((px - c) ** 2, axis=1) for c in C])
        labels = np.argmin(d, axis=0)
        for i in range(k):
            sel = labels == i
            if sel.any():
                C[i] = px[sel].mean(axis=0)
    counts = np.bincount(labels, minlength=k).astype(np.float64)
    total = counts.sum()
    order = np.argsort(-counts)
    out = []
    for i in order:
        if counts[i] <= 0:
            continue
        r, g, b = (int(round(float(v))) for v in C[i])
        out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "rgb": [r, g, b],
                    "pct": round(100.0 * float(counts[i]) / total, 2)})
    return out


# ================================================================ silhouettes

def border_background(arr: np.ndarray, band: int = 6) -> np.ndarray:
    """Per-row background colour from the left/right image borders."""
    a = np.asarray(arr, dtype=np.float32)
    h, w = a.shape[:2]
    band = int(max(1, min(band, w // 4)))
    b = np.concatenate([a[:, :band], a[:, w - band:]], axis=1)
    return np.median(b, axis=1)


def foreground_mask(arr: np.ndarray, tol: float = 20.0, band: int = 6,
                    mode: str = "auto", step: int = 4):
    """Split foreground (building) from background (sky / clouds / backdrop).

    The ten references mix graded skies, white clouds, a white studio backdrop
    and flat interior ceilings, so a single-colour flood fill is not enough.
    Three candidate background predicates are combined:

    ``row``     per-row border median within ``tol``   (graded sky, ground plane)
    ``sky``     HSV blue/pale rule                     (blue sky)
    ``bright``  ``v > 0.82 and s < 0.22``              (clouds, white backdrop)

    Only candidate pixels **connected to the image border** count as
    background, which keeps the building's own pale plaster walls (never
    border-connected through the dark roof line) as foreground.

    ``mode='auto'`` records which border statistic was used; ``mode`` may also
    be forced to ``'row'`` or ``'global'``.  Returns ``(mask, info)``.
    """
    a = np.asarray(arr, dtype=np.float32)
    h, w = a.shape[:2]
    bg_row = border_background(a, band)
    if mode == "auto":
        spread = float(np.percentile(bg_row, 90) - np.percentile(bg_row, 10))
        mode = "row" if spread >= 6.0 else "global"
    if mode == "global":
        border = np.concatenate([a[:, :band], a[:, w - band:]], axis=1).reshape(-1, 3)
        bg = np.median(border, axis=0)[None, None, :]
    else:
        bg = bg_row[:, None, :]

    cand = np.abs(a - bg).max(axis=2) <= tol
    sky = sky_mask(a)
    hsv_v = a.max(axis=2) / 255.0
    hsv_s = np.where(hsv_v <= 1e-6, 0.0,
                     (a.max(axis=2) - a.min(axis=2)) / np.maximum(a.max(axis=2), 1e-6))
    bright = (hsv_v > 0.82) & (hsv_s < 0.22)
    cand = cand | sky | bright

    small = _downsample_bool(cand, step)
    background = _flood_cells(small, _border_ring(small.shape))
    mask = ~_upsample_bool(background, (h, w), step)

    info = {"mode": mode, "tol": float(tol), "step": int(step),
            "borderSpread": round(float(np.percentile(bg_row, 90)
                                        - np.percentile(bg_row, 10)), 3),
            "skyCandidateFraction": round(float(sky.mean()), 4),
            "brightCandidateFraction": round(float(bright.mean()), 4),
            "borderBackgroundFraction": round(float(background.mean()), 4),
            "rawFraction": round(float(mask.mean()), 4)}
    return mask, info


def _downsample_bool(mask: np.ndarray, step: int) -> np.ndarray:
    h, w = mask.shape
    hs, ws = max(1, h // step), max(1, w // step)
    m = mask[:hs * step, :ws * step].reshape(hs, step, ws, step)
    return m.mean(axis=(1, 3)) >= 0.5


def _upsample_bool(small: np.ndarray, shape, step: int) -> np.ndarray:
    up = np.repeat(np.repeat(small, step, axis=0), step, axis=1)
    h, w = shape
    out = np.zeros((h, w), dtype=bool)
    hh, ww = min(h, up.shape[0]), min(w, up.shape[1])
    out[:hh, :ww] = up[:hh, :ww]
    if hh < h:
        out[hh:, :] = out[hh - 1:hh, :]
    if ww < w:
        out[:, ww:] = out[:, ww - 1:ww]
    return out


def _flood_cells(traversable: np.ndarray, seeds) -> np.ndarray:
    """4-connected flood fill from explicit ``seeds`` within ``traversable``.

    Runs breadth-first over the (small) grid; every visited cell is returned.
    """
    hs, ws = traversable.shape
    out = np.zeros_like(traversable)
    frontier = []
    for y, x in seeds:
        y, x = int(y), int(x)
        if 0 <= y < hs and 0 <= x < ws and traversable[y, x] and not out[y, x]:
            out[y, x] = True
            frontier.append((y, x))
    while frontier:
        nxt = []
        for y, x in frontier:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if (0 <= ny < hs and 0 <= nx < ws and traversable[ny, nx]
                        and not out[ny, nx]):
                    out[ny, nx] = True
                    nxt.append((ny, nx))
        frontier = nxt
    return out


def _border_ring(shape) -> list:
    hs, ws = shape
    ring = [(0, x) for x in range(ws)] + [(hs - 1, x) for x in range(ws)]
    ring += [(y, 0) for y in range(hs)] + [(y, ws - 1) for y in range(hs)]
    return ring


def clean_mask(mask: np.ndarray, step: int = 4, keep_largest: bool = True,
               fill_holes: bool = True, min_fraction: float = 0.002):
    """Fill interior holes and keep the dominant connected component."""
    m = np.asarray(mask, dtype=bool)
    h, w = m.shape
    info = {"step": step, "largestKept": False, "holesFilled": False,
            "components": 0, "largestFraction": round(float(m.mean()), 4)}
    if m.size == 0:
        return m, info
    small = _downsample_bool(m, step)
    if fill_holes:
        # Background = non-foreground cells reachable from the image border.
        outside = _flood_cells(~small, _border_ring(small.shape))
        holes = (~small) & (~outside)
        info["holesFilled"] = bool(holes.any())
        small = small | holes
    if keep_largest:
        comps = []
        remaining = small.copy()
        for _ in range(64):
            seeds = np.argwhere(remaining)
            if seeds.size == 0:
                break
            y0, x0 = int(seeds[0][0]), int(seeds[0][1])
            comp = _flood_cells(remaining, [(y0, x0)])
            if not comp.any():
                remaining[y0, x0] = False
                continue
            comps.append(comp)
            remaining &= ~comp
        info["components"] = len(comps)
        if comps:
            best = max(comps, key=lambda c: int(c.sum()))
            small = best
            info["largestFraction"] = round(float(small.mean()), 4)
            info["largestKept"] = True
    out = _upsample_bool(small, (h, w), step) & m
    return out, info


def bbox_of(mask: np.ndarray) -> dict | None:
    m = np.asarray(mask, dtype=bool)
    if not m.any():
        return None
    rows = np.nonzero(m.any(axis=1))[0]
    cols = np.nonzero(m.any(axis=0))[0]
    h, w = m.shape
    x0, x1 = int(cols.min()), int(cols.max())
    y0, y1 = int(rows.min()), int(rows.max())
    return {"x": x0, "y": y0, "w": x1 - x0 + 1, "h": y1 - y0 + 1,
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "norm": {"x0": round(x0 / w, 4), "y0": round(y0 / h, 4),
                     "x1": round(x1 / w, 4), "y1": round(y1 / h, 4),
                     "w": round((x1 - x0 + 1) / w, 4),
                     "h": round((y1 - y0 + 1) / h, 4)}}


def band_slices(height: int, boundaries) -> list:
    """Turn normalised boundaries into integer ``(y0, y1)`` row slices."""
    cuts = [0.0] + [float(b) for b in boundaries] + [1.0]
    cuts = sorted(set(max(0.0, min(1.0, c)) for c in cuts))
    out = []
    for i in range(len(cuts) - 1):
        y0 = int(round(cuts[i] * height))
        y1 = int(round(cuts[i + 1] * height))
        out.append((y0, max(y0 + 1, y1)))
    return out


def symmetry_score(mask: np.ndarray, box: dict | None = None) -> float:
    """IoU between the silhouette and its mirror about the box centre column."""
    m = np.asarray(mask, dtype=bool)
    if box is None:
        box = bbox_of(m)
    if box is None:
        return 0.0
    x0, x1 = box["x"], box["x1"]
    sub = m[:, x0:x1 + 1]
    return float((sub & sub[:, ::-1]).sum() / max(1, (sub | sub[:, ::-1]).sum()))


def warm_cool(arr: np.ndarray, mask: np.ndarray | None = None) -> dict:
    """Warm/cool balance of the foreground.

    ``ratio`` is reported only when both populations are materially present
    (>= 0.5 % each); otherwise it is ``null`` rather than a meaningless large
    number, and the caller should read the two fractions instead.
    """
    a = np.asarray(arr, dtype=np.float32)
    sel = np.asarray(mask, dtype=bool) if mask is not None else np.ones(a.shape[:2], bool)
    if not sel.any():
        return {"warmFraction": 0.0, "coolFraction": 0.0, "ratio": None,
                "meanWarmth": 0.0, "warmMinusCool": 0.0}
    px = a[sel][:, :3]
    warm = (px[:, 1] > px[:, 2]) & (px[:, 0] > px[:, 2]) & (px[:, 0] >= px[:, 1])
    cool = px[:, 2] > px[:, 0]
    warmth = float((px[:, 0] - px[:, 2]).mean())
    wf, cf = float(warm.mean()), float(cool.mean())
    ratio = round(wf / cf, 4) if (cf >= 0.005 and wf >= 0.005) else None
    return {"warmFraction": round(wf, 4), "coolFraction": round(cf, 4),
            "ratio": ratio, "meanWarmth": round(warmth, 3),
            "warmMinusCool": round(wf - cf, 4)}


def sky_mask(arr: np.ndarray) -> np.ndarray:
    """Blue/pale sky detector (HSV rule from the proven ``measure_v2`` pass)."""
    h, s, v = rgb_to_hsv(arr)
    blue = (h >= 190.0) & (h <= 250.0) & (s > 0.18) & (v > 0.55)
    pale = (v > 0.86) & (s < 0.35) & (h >= 190.0) & (h <= 250.0)
    return blue | pale


# ====================================================================== font

_FONT_B32 = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
_FONT: dict = {}


def _init_font() -> None:
    rows = {
        "0": "EHJLPHE", "1": "4C4444E", "2": "EH1248V", "3": "V2421HE",
        "4": "26AIV22", "5": "VGU11HE", "6": "68GUHHE", "7": "V124888",
        "8": "EHHEHHE", "9": "EHHF12C",
        "A": "EHHVHHH", "B": "UHHUHHU", "C": "EHGGGHE", "D": "SIHHHIS",
        "E": "VGGUGGV", "F": "VGGUGGG", "G": "EHGNHHF", "H": "HHHVHHH",
        "I": "E44444E", "J": "72222IC", "K": "HIKOKIH", "L": "GGGGGGV",
        "M": "HRLLHHH", "N": "HHPLJHH", "O": "EHHHHHE", "P": "UHHUGGG",
        "Q": "EHHHLID", "R": "UHHUKIH", "S": "FGGE11U", "T": "V444444",
        "U": "HHHHHHE", "V": "HHHHHA4", "W": "HHHLLRH", "X": "HHA4AHH",
        "Y": "HHA4444", "Z": "V1248GV",
        "-": "000V000", "_": "000000V", ".": "00000CC", ":": "0CC0CC0",
        " ": "0000000", "+": "004V400", "/": "001248G", "%": "H1248GH",
    }
    for ch, code in rows.items():
        bits = np.zeros((7, 5), dtype=bool)
        for r, c in enumerate(code):
            v = _FONT_B32.index(c)
            for col in range(5):
                bits[r, col] = bool((v >> (4 - col)) & 1)
        _FONT[ch] = bits


_init_font()

GLYPH_W, GLYPH_H, GLYPH_GAP = 5, 7, 1


def text_width(text: str, scale: int = 2) -> int:
    return max(0, (len(text) * (GLYPH_W + GLYPH_GAP) - GLYPH_GAP)) * scale


def draw_text(arr: np.ndarray, x: int, y: int, text: str, color=(255, 255, 255),
              scale: int = 2, shadow=(0, 0, 0)) -> None:
    """Blit a 5x7 bitmap string onto an ``(H, W, 3)`` uint8 array in place."""
    h, w = arr.shape[:2]
    cx = int(x)
    for ch in str(text).upper():
        bits = _FONT.get(ch)
        if bits is None:
            cx += (GLYPH_W + GLYPH_GAP) * scale
            continue
        for r in range(GLYPH_H):
            for c in range(GLYPH_W):
                if not bits[r, c]:
                    continue
                px = cx + c * scale
                py = y + r * scale
                if 0 <= py < h and 0 <= px < w:
                    arr[py:min(h, py + scale), px:min(w, px + scale)] = shadow
                    py2, px2 = py - scale, px - scale
                    if 0 <= py2 < h and 0 <= px2 < w:
                        arr[py2, px2:min(w, px2 + scale)] = shadow
        cx += (GLYPH_W + GLYPH_GAP) * scale
    # second pass with the real colour so the shadow stays a 1px outline
    cx = int(x)
    for ch in str(text).upper():
        bits = _FONT.get(ch)
        if bits is None:
            cx += (GLYPH_W + GLYPH_GAP) * scale
            continue
        for r in range(GLYPH_H):
            for c in range(GLYPH_W):
                if bits[r, c]:
                    px = cx + c * scale
                    py = y + r * scale
                    if 0 <= py < h and 0 <= px < w:
                        arr[py:min(h, py + scale), px:min(w, px + scale)] = color
        cx += (GLYPH_W + GLYPH_GAP) * scale


def draw_rect(arr: np.ndarray, x0: int, y0: int, x1: int, y1: int,
              color=(255, 64, 64), thickness: int = 2) -> None:
    h, w = arr.shape[:2]
    x0, x1 = int(max(0, min(x0, x1))), int(min(w - 1, max(x0, x1)))
    y0, y1 = int(max(0, min(y0, y1))), int(min(h - 1, max(y0, y1)))
    t = max(1, int(thickness))
    arr[y0:min(h, y0 + t), x0:x1 + 1] = color
    arr[max(0, y1 - t + 1):y1 + 1, x0:x1 + 1] = color
    arr[y0:y1 + 1, x0:min(w, x0 + t)] = color
    arr[y0:y1 + 1, max(0, x1 - t + 1):x1 + 1] = color


def draw_cross(arr: np.ndarray, x: int, y: int, color=(255, 220, 0), size: int = 7) -> None:
    h, w = arr.shape[:2]
    x, y = int(x), int(y)
    for d in range(-size, size + 1):
        if 0 <= y < h and 0 <= x + d < w:
            arr[y, x + d] = color
        if 0 <= y + d < h and 0 <= x < w:
            arr[y + d, x] = color


def contact_sheet(cells: list, cell_w: int = 360, cell_h: int = 270,
                  cols: int = 5, label_h: int = 30, bg=(24, 24, 28),
                  title: str | None = None, scale: int = 2,
                  pad: int = 8, draw_boxes: bool = True) -> np.ndarray:
    """Compose labelled thumbnails into one PNG-ready array.

    ``cells`` is a list of ``{"label", "image", "box"? , "sublabel"?}`` dicts.
    Intended as the human-readable companion to ``measurements.json``.
    """
    n = max(1, len(cells))
    rows = int(math.ceil(n / float(cols)))
    title_h = 0
    if title:
        title_h = GLYPH_H * 3 + pad * 2
    W = cols * cell_w + (cols + 1) * pad
    H = title_h + rows * (cell_h + label_h) + (rows + 1) * pad
    sheet = np.zeros((H, W, 3), dtype=np.uint8)
    sheet[:, :] = bg
    if title:
        draw_text(sheet, pad, pad + 2, title, color=(255, 236, 200), scale=3)
    for i, cell in enumerate(cells):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = title_h + pad + r * (cell_h + label_h + pad)
        img = cell.get("image")
        tile = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
        tile[:, :] = (12, 12, 16)
        if img is not None:
            a = np.asarray(img)
            ih, iw = a.shape[:2]
            s = min(cell_w / float(iw), cell_h / float(ih))
            tw, th = max(1, int(iw * s)), max(1, int(ih * s))
            small = resize_bilinear(a, tw, th)
            ox, oy = (cell_w - tw) // 2, (cell_h - th) // 2
            tile[oy:oy + th, ox:ox + tw] = small
            box = cell.get("box")
            if draw_boxes and box:
                bx0 = ox + int(box["x"] * s)
                by0 = oy + int(box["y"] * s)
                bx1 = ox + int((box["x"] + box["w"] - 1) * s)
                by1 = oy + int((box["y"] + box["h"] - 1) * s)
                draw_rect(tile, bx0, by0, bx1, by1, color=(80, 230, 120), thickness=1)
        sheet[y:y + cell_h, x:x + cell_w] = tile
        label = str(cell.get("label", f"{i + 1:02d}"))
        draw_text(sheet, x + 2, y + cell_h + 4, label[:26],
                  color=(240, 240, 240), scale=scale)
        sub = cell.get("sublabel")
        if sub:
            draw_text(sheet, x + 2 + text_width(label[:18], scale) + 8, y + cell_h + 4,
                      str(sub)[:22], color=(150, 200, 255), scale=scale)
    return sheet


def strip(cells: list, cell_w: int = 260, cell_h: int = 195, label_h: int = 26,
          bg=(20, 20, 24), pad: int = 6) -> np.ndarray:
    """Single-row variant of :func:`contact_sheet`."""
    sheet = contact_sheet(cells, cell_w=cell_w, cell_h=cell_h, cols=max(1, len(cells)),
                          label_h=label_h, bg=bg, pad=pad)
    return sheet


def blend_overlay(base: np.ndarray, layer: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """50 % (or ``alpha``) composite of two uint8 RGB arrays."""
    a = np.asarray(base, dtype=np.float32)
    b = np.asarray(layer, dtype=np.float32)
    if a.shape != b.shape:
        b = resize_bilinear(layer, a.shape[1], a.shape[0]).astype(np.float32)
    return np.clip(a * (1.0 - alpha) + b * alpha + 0.5, 0, 255).astype(np.uint8)


def mask_outline(mask: np.ndarray, thickness: int = 2) -> np.ndarray:
    """Boundary pixels of a boolean mask (dilate-minus-mask)."""
    m = np.asarray(mask, dtype=bool)
    d = m.copy()
    for _ in range(max(1, thickness)):
        e = d.copy()
        e[1:, :] |= d[:-1, :]
        e[:-1, :] |= d[1:, :]
        e[:, 1:] |= d[:, :-1]
        e[:, :-1] |= d[:, 1:]
        d = e
    return d & ~m


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, dtype=bool)
    y = np.asarray(b, dtype=bool)
    if x.shape != y.shape:
        return 0.0
    union = int((x | y).sum())
    return float(int((x & y).sum()) / union) if union else 0.0


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def relpath(path: str, root: str | None) -> str | None:
    """Project-relative rendering of an absolute path (for readability)."""
    if not path or not root:
        return None
    try:
        return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace("\\", "/")
    except ValueError:
        return None


def resolve_path(path: str, ctx: dict | None = None) -> str:
    """Absolute-ise ``path``, resolving relatives against ``projectRoot``.

    Never escapes the authorized project root: an absolute path outside it is
    returned unchanged so the caller can decide, but a relative path is always
    anchored on ``context.projectRoot`` (falling back to the CWD).
    """
    if not path:
        return path
    p = os.path.expanduser(str(path))
    if os.path.isabs(p):
        return os.path.normpath(p)
    root = (ctx or {}).get("projectRoot") or os.getcwd()
    return os.path.normpath(os.path.join(root, p))


def sha1_of(path: str, chunk: int = 1 << 20) -> str:
    import hashlib
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()
