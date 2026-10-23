"""``match_camera`` / ``validate_multiview`` — real pinhole camera solving.

``match_camera`` recovers a Blender camera from >=6 2D<->3D correspondences:

1. Hartley normalisation of both point sets;
2. normalised DLT (SVD null space) -> 3x4 projection matrix;
3. RQ decomposition of the left 3x3 -> intrinsics + rotation, camera centre
   from the null vector;
4. Levenberg-Marquardt refinement **directly in Blender's own parameterisation**
   (position, look-at target, lens, roll, shift_x, shift_y) using a projection
   that mirrors Blender's ``world_to_camera_view``, so the returned camera is
   the optimum of the model ``wm_capture`` can actually build;
5. structured rejection of degenerate input (too few / duplicate / collinear
   points, points behind the camera, non-finite DLT).

``validate_multiview`` projects component boxes through the solved cameras and
compares them with the measured reference bands, reporting per-view RMS and
component offsets plus contradictions.

Owned by ``visual-match``.  numpy + standard library only.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

import wm_common as C
import wm_image as WI

SENSOR_WIDTH_MM = 36.0

# Contract §1 geometry, used as the documented fallback component catalogue.
CONTRACT = {
    "plinthTopZ": 0.0, "plinthBottomZ": -0.65, "bracketBottomZ": -0.95,
    "floor1Z": 0.25, "floor2Z": 3.60, "topZ": 6.55,
    "eaveZ": 6.15, "ridgeZ": 11.30,
    "footprintX": 8.4, "footprintY": 7.5, "hallY": 0.55,
    "overhang": 1.55, "baseSize": 16.0,
}


class CameraError(Exception):
    """Structured, catchable failure (carries a machine-readable code)."""

    def __init__(self, code: str, message: str, **detail):
        super().__init__(message)
        self.code = code
        self.message = message
        self.detail = detail

    def as_result(self) -> dict:
        return {"ok": False,
                "error": {"code": self.code, "message": self.message,
                          "detail": self.detail}}


# ============================================================ camera geometry

def _basis(position, target, roll: float):
    """World->camera rotation mirroring ``to_track_quat('-Z', 'Y')`` + roll.

    Blender's camera looks down its local -Z with local +Y up.  ``roll``
    rotates the camera about its own view axis.
    """
    pos = np.asarray(position, dtype=np.float64)
    tgt = np.asarray(target, dtype=np.float64)
    d = tgt - pos
    nd = float(np.linalg.norm(d))
    if nd < 1e-12:
        raise CameraError("DEGENERATE_VIEW", "target coincides with position")
    d = d / nd
    z = -d                                        # local +Z points backwards
    up_ref = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(up_ref, z))) > 0.999999:   # straight up/down view
        up_ref = np.array([0.0, 1.0, 0.0])
    x = np.cross(up_ref, z)
    nx = float(np.linalg.norm(x))
    if nx < 1e-12:
        x = np.cross(np.array([1.0, 0.0, 0.0]), z)
        nx = float(np.linalg.norm(x))
    x = x / nx
    y = np.cross(z, x)
    R = np.stack([x, y, z], axis=1)               # columns = camera axes
    if roll:
        c, s = math.cos(roll), math.sin(roll)
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        R = R @ Rz
    return R


def project_points(cam: dict, points) -> np.ndarray:
    """Project world points to pixels, mirroring Blender's AUTO sensor fit.

    Returns an ``(N, 3)`` array of ``(u_px, v_px, depth)`` with ``v`` measured
    from the **top** of the image (so it can be compared with image rows) and
    ``depth`` being the positive distance along the view axis.
    """
    P = np.atleast_2d(np.asarray(points, dtype=np.float64))
    w = float(cam.get("width") or 1200)
    h = float(cam.get("height") or 900)
    f = float(cam["lens"])
    sensor = float(cam.get("sensor", SENSOR_WIDTH_MM))
    R = _basis(cam["position"], cam["target"], float(cam.get("roll", 0.0)))
    pos = np.asarray(cam["position"], dtype=np.float64)
    rel = (P - pos) @ R                          # R^T (P - pos)
    depth = -rel[:, 2]
    scale = max(w, h) * f / sensor
    shift_px = max(w, h)
    with np.errstate(divide="ignore", invalid="ignore"):
        x = rel[:, 0] / depth
        y = rel[:, 1] / depth
    u = 0.5 * w + x * scale + float(cam.get("shiftX", 0.0)) * shift_px
    v = 0.5 * h - y * scale - float(cam.get("shiftY", 0.0)) * shift_px
    return np.stack([u, v, depth], axis=1)


def pixel_scale(cam: dict) -> float:
    """Pixels per unit tangent at the principal point."""
    return max(float(cam.get("width") or 1200), float(cam.get("height") or 900)) * \
        float(cam["lens"]) / float(cam.get("sensor", SENSOR_WIDTH_MM))


def fov_from_lens(lens: float, sensor: float = SENSOR_WIDTH_MM) -> float:
    return math.degrees(2.0 * math.atan(sensor / (2.0 * max(1e-9, lens))))


# ------------------------------------------------------------- degeneracy

def _singular_ratio(points: np.ndarray) -> float:
    """sigma2/sigma1 of the centred point set (0 => collinear / coincident)."""
    X = np.asarray(points, dtype=np.float64)
    if X.shape[0] < 2:
        return 0.0
    Xc = X - X.mean(axis=0, keepdims=True)
    s = np.linalg.svd(Xc, compute_uv=False)
    if s.size == 0 or s[0] <= 1e-12:
        return 0.0
    return float(s[1] / s[0]) if s.size > 1 else 0.0


def validate_correspondences(points3d: np.ndarray, pixels: np.ndarray,
                             min_points: int = 6, eps: float = 1e-9) -> dict:
    """Raise :class:`CameraError` for input the solve cannot handle."""
    n = int(points3d.shape[0])
    if n < min_points:
        raise CameraError("INSUFFICIENT_CORRESPONDENCES",
                          f"{n} correspondences given, at least {min_points} are "
                          "required for a pinhole solve",
                          given=n, required=min_points)
    if not np.isfinite(points3d).all() or not np.isfinite(pixels).all():
        raise CameraError("NON_FINITE_INPUT",
                          "correspondences contain NaN/Inf values")
    for i in range(n):
        for j in range(i + 1, n):
            if np.linalg.norm(pixels[i] - pixels[j]) < eps:
                raise CameraError("DUPLICATE_PIXELS",
                                  f"correspondences {i} and {j} share the same "
                                  "pixel; identical image points carry no "
                                  "independent constraint",
                                  indices=[i, j], pixel=list(pixels[i]))
            if np.linalg.norm(points3d[i] - points3d[j]) < eps:
                raise CameraError("DUPLICATE_POINTS_3D",
                                  f"correspondences {i} and {j} share the same "
                                  "3D point", indices=[i, j], point=list(points3d[i]))
    r3 = _singular_ratio(points3d)
    if r3 < 1e-7:
        raise CameraError("COLLINEAR_POINTS_3D",
                          "the 3D points are collinear (or coincident); the DLT "
                          "null space is not unique",
                          singularRatio=r3)
    r2 = _singular_ratio(pixels)
    if r2 < 1e-9:
        raise CameraError("COLLINEAR_PIXELS",
                          "the image points are collinear; the DLT null space is "
                          "not unique", singularRatio=r2)
    return {"points": n, "singularRatio3D": round(r3, 8),
            "singularRatio2D": round(r2, 12)}


# ------------------------------------------------------------------ DLT

def _normalise2d(pts: np.ndarray):
    c = pts.mean(axis=0)
    d = pts - c
    mean_dist = float(np.sqrt((d ** 2).sum(axis=1)).mean())
    s = math.sqrt(2.0) / mean_dist if mean_dist > 1e-12 else 1.0
    T = np.array([[s, 0.0, -s * c[0]], [0.0, s, -s * c[1]], [0.0, 0.0, 1.0]])
    return T


def _normalise3d(pts: np.ndarray):
    c = pts.mean(axis=0)
    d = pts - c
    mean_dist = float(np.sqrt((d ** 2).sum(axis=1)).mean())
    s = math.sqrt(3.0) / mean_dist if mean_dist > 1e-12 else 1.0
    T = np.eye(4)
    T[0, 0] = T[1, 1] = T[2, 2] = s
    T[:3, 3] = -s * c
    return T


def dlt(points3d: np.ndarray, pixels: np.ndarray) -> dict:
    """Normalised DLT.  Returns the 3x4 matrix plus the normalisers used."""
    n = points3d.shape[0]
    T2 = _normalise2d(pixels)
    T3 = _normalise3d(points3d)
    ph = np.hstack([pixels, np.ones((n, 1))]) @ T2.T
    Xh = np.hstack([points3d, np.ones((n, 1))]) @ T3.T
    A = np.zeros((2 * n, 12), dtype=np.float64)
    for i in range(n):
        X, Y, Z = Xh[i, 0], Xh[i, 1], Xh[i, 2]
        u, v, _ = ph[i]
        A[2 * i] = [X, Y, Z, 1, 0, 0, 0, 0, -u * X, -u * Y, -u * Z, -u]
        A[2 * i + 1] = [0, 0, 0, 0, X, Y, Z, 1, -v * X, -v * Y, -v * Z, -v]
    _, s, Vt = np.linalg.svd(A)
    Pn = Vt[-1].reshape(3, 4)
    P = np.linalg.inv(T2) @ Pn @ T3
    if not np.isfinite(P).all() or abs(P[2, 3]) < 1e-14 and np.linalg.norm(P[2, :3]) < 1e-14:
        raise CameraError("DLT_FAILED", "the DLT produced a degenerate projection")
    return {"P": P, "singularValues": [float(x) for x in s[:12]],
            "smallestSingular": float(s[-1]), "secondSmallest": float(s[-2])}


def decompose_dlt(P: np.ndarray) -> dict:
    """RQ decomposition of ``P[:, :3]`` -> K, R and the camera centre."""
    M = np.asarray(P, dtype=np.float64)[:, :3]
    if abs(np.linalg.det(M)) < 1e-14:
        raise CameraError("DLT_DEGENERATE_INTRINSICS",
                          "the DLT's left 3x3 is singular; intrinsics cannot be "
                          "recovered", determinant=float(np.linalg.det(M)))
    # RQ: reverse-flip -> QR -> reverse-flip back.
    Q, R = np.linalg.qr(np.flipud(M).T)
    R = np.flipud(R.T)
    Q = Q.T
    R = np.fliplr(R)
    Q = np.flipud(Q)
    # Blender/OpenCV want K[2,2] = 1 with positive diagonal.
    for i in range(3):
        if abs(R[i, i]) > 1e-15 and R[i, i] < 0:
            R[:, i] *= -1
            Q[i, :] *= -1
    if R[2, 2] != 0:
        R = R / R[2, 2]
    Cc = -np.linalg.inv(M) @ np.asarray(P, dtype=np.float64)[:, 3]
    return {"K": R, "R": Q, "center": Cc,
            "fx": float(R[0, 0]), "fy": float(R[1, 1]),
            "cx": float(R[0, 2]), "cy": float(R[1, 2])}


# ------------------------------------------------------- Levenberg-Marquardt

PARAM_NAMES = ("px", "py", "pz", "yaw", "pitch", "lens", "roll", "shiftX", "shiftY")
PARAM_SCALE = np.array([1.0, 1.0, 1.0, 0.1, 0.1, 1.0, 1.0, 0.01, 0.01])


def view_direction(position, target) -> tuple:
    """(yaw, pitch) of the view direction, in the same convention as _basis."""
    d = np.asarray(target, dtype=np.float64) - np.asarray(position, dtype=np.float64)
    n = float(np.linalg.norm(d))
    if n < 1e-12:
        return 0.0, 0.0
    d = d / n
    return math.atan2(d[1], d[0]), math.asin(max(-1.0, min(1.0, d[2])))


def theta_to_cam(theta: np.ndarray, base: dict, P3: np.ndarray) -> dict:
    """Build a camera from the gauge-free 9-vector.

    The look-at target has one unobservable degree of freedom (only its
    direction affects the projection), so it is *not* optimised.  Instead the
    direction is parameterised by (yaw, pitch) and the target is always placed
    at the median distance from the camera to the fitted 3D points, which keeps
    the reported ``target`` meaningful and the system well conditioned.
    """
    pos = np.asarray(theta[0:3], dtype=np.float64)
    yaw, pitch = float(theta[3]), float(theta[4])
    d_ref = float(np.median(np.linalg.norm(np.asarray(P3) - pos, axis=1))) \
        if len(P3) else 10.0
    d_ref = max(1.0, d_ref)
    d = np.array([math.cos(pitch) * math.cos(yaw),
                  math.cos(pitch) * math.sin(yaw),
                  math.sin(pitch)])
    cam = dict(base)
    cam["position"] = [float(v) for v in pos]
    cam["target"] = [float(v) for v in (pos + d * d_ref)]
    cam["lens"] = float(theta[5])
    cam["roll"] = float(theta[6])
    cam["shiftX"] = float(theta[7])
    cam["shiftY"] = float(theta[8])
    cam["targetDistanceM"] = round(d_ref, 6)
    return cam


def cam_to_theta(cam: dict, P3: np.ndarray) -> np.ndarray:
    yaw, pitch = view_direction(cam["position"], cam["target"])
    return np.array([*cam["position"], yaw, pitch, cam["lens"],
                     cam.get("roll", 0.0), cam.get("shiftX", 0.0),
                     cam.get("shiftY", 0.0)], dtype=np.float64)


def _residuals(theta: np.ndarray, cam: dict, P3: np.ndarray,
               uv: np.ndarray) -> np.ndarray:
    c = theta_to_cam(theta, cam, P3)
    try:
        proj = project_points(c, P3)
    except CameraError:
        return np.full(uv.size, 1e6, dtype=np.float64)
    return (proj[:, :2] - uv).reshape(-1)


def levenberg_marquardt(cam: dict, P3: np.ndarray, uv: np.ndarray,
                        iters: int = 120, lam0: float = 1e-3,
                        tol: float = 1e-10):
    """Damped Gauss-Newton in Blender's camera parameter space (scaled units)."""
    theta = cam_to_theta(cam, P3)
    scale = PARAM_SCALE.copy()

    def cost(t):
        r = _residuals(t, cam, P3, uv)
        return float(r @ r)

    def jacobian(t, r0):
        J = np.zeros((r0.size, theta.size))
        for k in range(theta.size):
            step = max(1e-6, abs(t[k]) * 1e-6) * scale[k] / scale[k]
            tp = t.copy(); tp[k] += step
            tm = t.copy(); tm[k] -= step
            J[:, k] = (_residuals(tp, cam, P3, uv) - _residuals(tm, cam, P3, uv)) / (2 * step)
        return J

    c0 = cost(theta)
    lam = lam0
    trace = [{"iteration": 0, "cost": c0, "lambda": lam}]
    for it in range(1, iters + 1):
        r = _residuals(theta, cam, P3, uv)
        J = jacobian(theta, r)
        A = J.T @ J
        g = J.T @ r
        improved = False
        for _ in range(12):
            H = A + lam * np.diag(np.maximum(np.diag(A), 1e-9))
            try:
                dx = -np.linalg.solve(H, g)
            except np.linalg.LinAlgError:
                lam *= 10.0
                continue
            cand = theta + dx
            if cand[5] <= 1e-3:                  # keep a physical focal length
                lam *= 10.0
                continue
            cc = cost(cand)
            if np.isfinite(cc) and cc < c0:
                prev = c0
                theta, c0 = cand, cc
                lam = max(lam * 0.3, 1e-12)
                improved = True
                trace.append({"iteration": it, "cost": c0, "lambda": lam})
                if abs(prev - cc) <= tol * max(1.0, prev):
                    return theta, c0, trace
                break
            lam *= 10.0
        if not improved:
            break
    return theta, c0, trace


# ------------------------------------------------------------------- solve

def _camera_dict_from_theta(theta, base: dict, P3: np.ndarray,
                            width, height, sensor=SENSOR_WIDTH_MM) -> dict:
    cam = theta_to_cam(theta, base, P3)
    cam.update({
        "lens": round(float(cam["lens"]), 6),
        "sensor": float(sensor),
        "fov": round(fov_from_lens(float(cam["lens"]), sensor), 4),
        "roll": round(float(cam["roll"]), 8),
        "shiftX": round(float(cam["shiftX"]), 8),
        "shiftY": round(float(cam["shiftY"]), 8),
        "position": [round(float(v), 8) for v in cam["position"]],
        "target": [round(float(v), 8) for v in cam["target"]],
        "width": int(width), "height": int(height),
    })
    return cam


def _init_from_dlt(dec: dict, width: float, height: float, sensor: float,
                   pixels: np.ndarray) -> dict:
    """Turn the DLT intrinsics/extrinsics into a starting Blender camera."""
    fx, fy = abs(dec["fx"]), abs(dec["fy"])
    if not (np.isfinite(fx) and fx > 1e-9):
        raise CameraError("DLT_DEGENERATE_INTRINSICS",
                          "the DLT recovered a non-positive focal length",
                          fx=float(fx), fy=float(fy))
    fpx = 0.5 * (fx + fy)
    lens = fpx * sensor / max(width, height)
    lens = float(min(max(lens, 1.0), 500.0))
    shift_x = (dec["cx"] - 0.5 * width) / max(width, height)
    shift_y = (0.5 * height - dec["cy"]) / max(width, height)
    center = np.asarray(dec["center"], dtype=np.float64)
    Rd = np.asarray(dec["R"], dtype=np.float64)
    # OpenCV-style R maps world -> camera (x right, y down, z forward).  The
    # view direction in world space is R^T @ [0,0,1].
    fwd = Rd.T @ np.array([0.0, 0.0, 1.0])
    if float(np.linalg.norm(fwd)) < 1e-9:
        raise CameraError("DLT_DEGENERATE_EXTRINSICS",
                          "the DLT rotation has no forward axis")
    fwd = fwd / float(np.linalg.norm(fwd))
    dist = float(np.linalg.norm(pixels.mean(axis=0)))  # rough, only a seed
    dist = max(dist, 5.0)
    target = center + fwd * dist
    return {"position": [float(v) for v in center],
            "target": [float(v) for v in target],
            "lens": lens, "sensor": sensor, "roll": 0.0,
            "shiftX": float(np.clip(shift_x, -0.5, 0.5)),
            "shiftY": float(np.clip(shift_y, -0.5, 0.5)),
            "width": width, "height": height}


def solve_camera(points3d, pixels, width: float, height: float,
                 sensor: float = SENSOR_WIDTH_MM, init: dict | None = None,
                 refine_iters: int = 120) -> dict:
    """Full pipeline: validate -> DLT -> decompose -> LM refine."""
    P3 = np.asarray(points3d, dtype=np.float64).reshape(-1, 3)
    uv = np.asarray(pixels, dtype=np.float64).reshape(-1, 2)
    guard = validate_correspondences(P3, uv)

    d = dlt(P3, uv)
    dec = decompose_dlt(d["P"])

    if init:
        # Caller-provided seed (yaw/pitch/distance/lens) wins over the DLT seed.
        cam0 = _seed_from_init(init, dec, width, height, sensor, P3)
    else:
        cam0 = _init_from_dlt(dec, width, height, sensor, uv)

    proj0 = project_points(cam0, P3)
    rms0 = float(np.sqrt(np.mean(np.sum((proj0[:, :2] - uv) ** 2, axis=1))))

    theta, cost, trace = levenberg_marquardt(cam0, P3, uv, iters=refine_iters)
    cam = _camera_dict_from_theta(theta, cam0, P3, width, height, sensor)

    proj = project_points(cam, P3)
    res = proj[:, :2] - uv
    per = np.sqrt(np.sum(res ** 2, axis=1))
    rms = float(np.sqrt(np.mean(per ** 2)))

    behind = int(np.count_nonzero(proj[:, 2] <= 0.0))
    if behind:
        raise CameraError("POINTS_BEHIND_CAMERA",
                          f"{behind} of {len(per)} points project behind the "
                          "camera plane; the solution is not admissible",
                          behind=behind, rmsPx=rms)

    # Cross-check the LM optimum really is a local minimum of the Blender model.
    if rms > rms0 + 1e-6:
        C.log("match_camera: LM did not improve on the DLT seed "
              "(rms %.4f vs %.4f)" % (rms, rms0))

    view = _basis(cam["position"], cam["target"], cam["roll"])
    cam["matrixWorld"] = [float(v) for v in
                          np.stack([*view.T, np.asarray(cam["position"])],
                                   axis=1).reshape(-1)]
    return {
        "camera": cam,
        "dlt": {"smallestSingular": d["smallestSingular"],
                "secondSmallest": d["secondSmallest"],
                "fx": dec["fx"], "fy": dec["fy"],
                "cx": dec["cx"], "cy": dec["cy"]},
        "guard": guard,
        "reprojectionError": {"rmsPx": round(rms, 6), "maxPx": round(float(per.max()), 6),
                              "meanPx": round(float(per.mean()), 6),
                              "initialRmsPx": round(rms0, 6)},
        "perPoint": [{"index": i,
                      "pixel": [round(float(uv[i, 0]), 3), round(float(uv[i, 1]), 3)],
                      "projected": [round(float(proj[i, 0]), 3),
                                    round(float(proj[i, 1]), 3)],
                      "residualPx": round(float(per[i]), 6),
                      "depth": round(float(proj[i, 2]), 6)}
                     for i in range(len(per))],
        "lmTrace": trace[-6:],
        "theta": [float(v) for v in theta],
    }


def _seed_from_init(init: dict, dec: dict, width, height, sensor, P3) -> dict:
    """Build a seed from ``init`` (distance/lens/yaw/pitch) around the 3D cloud."""
    c = np.asarray(dec["center"], dtype=np.float64)
    if not np.isfinite(c).all():
        c = P3.mean(axis=0)
    yaw = math.radians(float(init.get("yaw", 35.0)))
    pitch = math.radians(float(init.get("pitch", 20.0)))
    dist = float(init.get("distance", max(10.0, float(np.ptp(P3, axis=0).max()) * 2.5)))
    aim = P3.mean(axis=0)
    pos = aim + dist * np.array([math.sin(yaw) * math.cos(pitch),
                                 math.cos(yaw) * math.cos(pitch),
                                 math.sin(pitch)])
    return {"position": [float(v) for v in pos], "target": [float(v) for v in aim],
            "lens": float(init.get("lens", 42.0)), "sensor": sensor,
            "roll": float(init.get("roll", 0.0)),
            "shiftX": 0.0, "shiftY": 0.0, "width": width, "height": height}


# ============================================================== task: match

def match_camera(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    checks, warnings = [], []

    raw = params.get("correspondences") or []
    if not isinstance(raw, list):
        return C.fail("correspondences must be a list")
    points3d, pixels, labels = [], [], []
    for i, item in enumerate(raw):
        try:
            points3d.append([float(v) for v in item["point3d"]])
            pixels.append([float(v) for v in item["pixel"]])
            labels.append(item.get("label") or f"p{i}")
        except (KeyError, TypeError, ValueError) as exc:
            return C.fail(f"correspondence {i} is malformed ({exc}); expected "
                          '{"point3d":[x,y,z],"pixel":[u,v]}')
    P3 = np.asarray(points3d, dtype=np.float64).reshape(-1, 3)
    uv = np.asarray(pixels, dtype=np.float64).reshape(-1, 2)

    image = params.get("image")
    size = params.get("imageSize")
    if size:
        width, height = float(size[0]), float(size[1])
    elif image:
        img_path = WI.resolve_path(image, ctx)
        hdr = WI.png_header(img_path)
        if hdr.get("ok"):
            width, height = float(hdr["width"]), float(hdr["height"])
        else:
            return C.fail(f"cannot determine image size: neither imageSize was "
                          f"given nor is {img_path} a readable PNG")
    else:
        return C.fail("image or imageSize is required")

    if image:
        img_path = WI.resolve_path(image, ctx)
        if not os.path.isfile(img_path):
            warnings.append(f"image file not found ({img_path}); solved from "
                            "imageSize alone")
            image = None

    sensor = float(params.get("sensor", SENSOR_WIDTH_MM))
    try:
        solved = solve_camera(P3, uv, width, height, sensor,
                             init=params.get("init"),
                             refine_iters=int(params.get("refineIters", 120)))
    except CameraError as exc:
        C.check(checks, "correspondences_valid", "fail", exc.message,
                code=exc.code, extraDetail=exc.detail)
        return {"ok": False, "error": {"code": exc.code, "message": exc.message,
                                       "detail": exc.detail},
                "checks": checks, "warnings": warnings,
                "notes": "degenerate input rejected before any camera was returned"}

    cam = solved["camera"]
    err = solved["reprojectionError"]

    out_dir = WI.resolve_path(params.get("outDir") or ctx.get("reportsDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "reports"), ctx)
    WI.ensure_dir(out_dir)
    stem = os.path.splitext(os.path.basename(image))[0] if image else "synthetic"
    cpath = params.get("outPath") or os.path.join(out_dir, "specs",
                                                 f"camera_{stem}.json")
    cpath = WI.resolve_path(cpath, ctx)
    WI.ensure_dir(os.path.dirname(cpath))
    payload = {"schema": 1, "generatedBy": "wm_camera.match_camera",
               "image": image, "imageSize": [width, height],
               "camera": cam, "reprojectionError": err,
               "perPoint": solved["perPoint"],
               "correspondenceLabels": labels,
               "dlt": solved["dlt"], "guard": solved["guard"],
               "integrityNote": (
                   "This camera describes the equations used to fit it. It has "
                   "not been verified against the reference beyond the listed "
                   "per-point residuals.")}
    with open(cpath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    C.check(checks, "correspondences_valid", "pass",
            f"{solved['guard']['points']} correspondences; 3D collinearity ratio "
            f"{solved['guard']['singularRatio3D']}", **solved["guard"])
    C.check(checks, "dlt_solved", "pass",
            f"normalised DLT, smallest singular value "
            f"{solved['dlt']['smallestSingular']:.6g}")
    C.check(checks, "refined", "pass",
            f"LM in Blender parameters: {err['initialRmsPx']} px -> {err['rmsPx']} px")
    status = "pass" if err["rmsPx"] <= float(params.get("maxRmsPx", 4.0)) else "warn"
    C.check(checks, "reprojection_within_tolerance", status,
            f"RMS {err['rmsPx']} px, max {err['maxPx']} px "
            f"(tolerance {params.get('maxRmsPx', 4.0)} px)")
    C.check(checks, "camera_written", "pass" if WI.file_size(cpath) else "fail",
            f"camera JSON {WI.file_size(cpath)} bytes", path=cpath)
    C.check(checks, "real_render_verified", "not_checked",
            "this task fits a camera to supplied correspondences; whether those "
            "pixels really belong to those 3D points is the caller's evidence, "
            "not something this module can confirm")

    return {
        "ok": True, "task": "match_camera",
        "artifacts": [WI.artifact("json", cpath)],
        "camera": cam,
        "reprojectionError": err,
        "perPoint": solved["perPoint"],
        "cameraPath": cpath,
        "cameraPathRel": WI.relpath(cpath, project_root),
        "metrics": {"points": solved["guard"]["points"],
                    "rmsPx": err["rmsPx"], "maxPx": err["maxPx"],
                    "initialRmsPx": err["initialRmsPx"],
                    "lens": cam["lens"], "fov": cam["fov"],
                    "distance": round(float(np.linalg.norm(
                        np.asarray(cam["target"]) - np.asarray(cam["position"]))), 4)},
        "checks": checks, "warnings": warnings,
        "notes": (f"solved from {solved['guard']['points']} correspondences at "
                  f"{int(width)}x{int(height)}: DLT + RQ decomposition, then LM "
                  f"refinement in Blender's parameterisation. RMS "
                  f"{err['rmsPx']} px, max {err['maxPx']} px."),
    }


# ======================================================= task: multiview

def default_components() -> list:
    """Five world-space component boxes derived from the contract geometry."""
    c = CONTRACT
    roof_x = c["footprintX"] + 2 * c["overhang"]
    roof_y = c["footprintY"] + 2 * c["overhang"]
    y = c["hallY"]
    return [
        {"name": "roof", "z": [c["eaveZ"], c["ridgeZ"]],
         "size": [roof_x, roof_y], "center": [0.0, y, 0.0]},
        {"name": "upper", "z": [c["floor2Z"], c["topZ"]],
         "size": [c["footprintX"], c["footprintY"]], "center": [0.0, y, 0.0]},
        {"name": "lower", "z": [c["floor1Z"], c["floor2Z"]],
         "size": [c["footprintX"], c["footprintY"]], "center": [0.0, y, 0.0]},
        {"name": "plinth", "z": [c["plinthBottomZ"], c["floor1Z"]],
         "size": [c["baseSize"], c["baseSize"]], "center": [0.0, 0.0, 0.0]},
        {"name": "ground", "z": [c["bracketBottomZ"], c["plinthBottomZ"]],
         "size": [c["baseSize"], c["baseSize"]], "center": [0.0, 0.0, 0.0]},
    ]


def component_corners(comp: dict) -> np.ndarray:
    """8 world-space corners of a component box, tolerant of spec spellings."""
    if "box3d" in comp or "worldBox" in comp:
        b = comp.get("box3d") or comp.get("worldBox")
        lo = np.asarray(b["min"], dtype=np.float64)
        hi = np.asarray(b["max"], dtype=np.float64)
    elif "min" in comp and "max" in comp:
        lo = np.asarray(comp["min"], dtype=np.float64)
        hi = np.asarray(comp["max"], dtype=np.float64)
    else:
        z0, z1 = (comp.get("z") or [0.0, 1.0])[:2]
        sx, sy = (comp.get("size") or [1.0, 1.0])[:2]
        cx, cy, _cz = (comp.get("center") or [0.0, 0.0, 0.0])[:3]
        zc = 0.5 * (float(z0) + float(z1))
        lo = np.array([cx - sx / 2.0, cy - sy / 2.0, float(z0) if "z" in comp else zc - 0.5])
        hi = np.array([cx + sx / 2.0, cy + sy / 2.0, float(z1) if "z" in comp else zc + 0.5])
    return np.array([[x, y, z] for x in (lo[0], hi[0])
                     for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


def load_json(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def validate_multiview(params: dict, ctx: dict) -> dict:
    params = params or {}
    project_root = ctx.get("projectRoot") or os.getcwd()
    reports = WI.resolve_path(params.get("reportsDir") or ctx.get("reportsDir")
                              or os.path.join(project_root, "outputs",
                                              "wenmai-3d", "reports"), ctx)
    checks, warnings, contradictions = [], [], []

    # ---- spec / component boxes
    spec_path = params.get("specPath")
    spec = load_json(WI.resolve_path(spec_path, ctx)) if spec_path else None
    comps = None
    comp_source = "contract-default"
    if spec:
        comps = spec.get("components") or (spec.get("spec") or {}).get("components")
        if comps:
            comp_source = "spec"
    if not comps:
        comps = default_components()
        warnings.append("no usable spec.components found; using the documented "
                        "contract-geometry component catalogue")

    # ---- measurements (measured bands per reference)
    meas_path = WI.resolve_path(
        params.get("measurementsPath") or os.path.join(reports, "analysis",
                                                      "measurements.json"), ctx)
    meas = load_json(meas_path)
    by_file, by_id = {}, {}
    if meas and isinstance(meas.get("images"), list):
        for e in meas["images"]:
            by_file[e.get("file")] = e
            by_id[e.get("id")] = e
    else:
        warnings.append(f"no measurements.json at {meas_path}; component offsets "
                        "cannot be compared with measured bands")

    # ---- views
    views = params.get("views")
    if not views:
        views = []
        sdir = os.path.join(reports, "specs")
        if os.path.isdir(sdir):
            for fn in sorted(os.listdir(sdir)):
                if fn.startswith("camera_") and fn.endswith(".json"):
                    views.append({"image": fn[len("camera_"):-len(".json")],
                                  "cameraPath": os.path.join(sdir, fn)})
    if not views:
        return C.fail("no views given and no camera_*.json found in "
                      f"{os.path.join(reports, 'specs')}")

    per_view, rms_all = [], []
    for v in views:
        image = v.get("image")
        cpath = v.get("cameraPath")
        cam = None
        cam_fitted_to = None
        if cpath:
            payload = load_json(WI.resolve_path(cpath, ctx))
            if payload:
                cam = payload.get("camera") or payload
                cam_fitted_to = payload.get("image")
        if cam is None:
            entry = by_file.get(os.path.basename(image or "")) or by_id.get(image)
            contradictions.append({"kind": "missing_camera", "image": image,
                                   "detail": "no readable camera was supplied for "
                                             "this view"})
            per_view.append({"image": image, "status": "fail",
                             "reason": "no camera"})
            continue

        # A camera fitted to a DIFFERENT image carries its own viewpoint error,
        # so band offsets then mix geometry error with viewpoint error.
        view_name = os.path.basename(image or "")
        cam_name = os.path.basename(cam_fitted_to) if cam_fitted_to else None
        camera_matches_view = (cam_name == view_name) if cam_name else None
        if camera_matches_view is False:
            contradictions.append({
                "kind": "camera_viewpoint_mismatch",
                "image": view_name,
                "detail": (f"the camera was fitted to '{cam_name}', not to this "
                           "view, so the band offsets below include viewpoint "
                           "error and must not be read as pure geometry error"),
            })

        measured = by_file.get(os.path.basename(image or "")) or by_id.get(image)
        w = float(cam.get("width") or (measured or {}).get("width") or 1448)
        h = float(cam.get("height") or (measured or {}).get("height") or 1086)
        cam = dict(cam, width=w, height=h)

        offsets, proj_rows = [], []
        resid = []
        for comp in comps:
            corners = component_corners(comp)
            proj = project_points(cam, corners)
            if float(np.min(proj[:, 2])) <= 0:
                contradictions.append({
                    "kind": "behind_camera", "image": image,
                    "component": comp.get("name"),
                    "detail": "at least one box corner projects behind the camera"})
                continue
            x0, x1 = float(proj[:, 0].min()), float(proj[:, 0].max())
            y0, y1 = float(proj[:, 1].min()), float(proj[:, 1].max())
            row = {"component": comp.get("name"),
                   "projectedBoxPx": [round(x0, 2), round(y0, 2),
                                      round(x1, 2), round(y1, 2)],
                   "projectedNorm": {"y0": round(y0 / h, 4), "y1": round(y1 / h, 4)}}
            if measured:
                bands = {b["name"]: b for b in measured.get("bands", [])}
                band = bands.get(comp.get("name"))
                if band:
                    my0, my1 = float(band["y0"]), float(band["y1"])
                    row["measuredRows"] = [int(my0), int(my1)]
                    row["measuredNorm"] = {"y0": round(my0 / h, 4),
                                           "y1": round(my1 / h, 4)}
                    row["deltaPx"] = {"top": round(y0 - my0, 2),
                                      "bottom": round(y1 - my1, 2),
                                      "height": round((y1 - y0) - (my1 - my0), 2)}
                    row["deltaNorm"] = {"top": round((y0 - my0) / h, 4),
                                        "bottom": round((y1 - my1) / h, 4),
                                        "height": round(((y1 - y0) - (my1 - my0)) / h, 4)}
                    resid.append(((y0 - my0) / h, (y1 - my1) / h))
                    if abs(row["deltaNorm"]["height"]) > 0.08:
                        contradictions.append({
                            "kind": "band_height_mismatch", "image": image,
                            "component": comp.get("name"),
                            "detail": (f"projected {comp.get('name')} band height "
                                       f"differs from the measured band by "
                                       f"{row['deltaNorm']['height']:+.3f} of the "
                                       "image height")})
            offsets.append(row)
        rms = None
        if resid:
            arr = np.asarray(resid, dtype=np.float64)
            rms = float(np.sqrt(np.mean(arr ** 2)))
            rms_all.append(rms)
        per_view.append({
            "image": image,
            "cameraPath": WI.resolve_path(cpath, ctx) if cpath else None,
            "cameraFittedTo": cam_name,
            "cameraMatchesView": camera_matches_view,
            "reprojectionRmsPx": None,
            "bandOffsetRmsNorm": round(rms, 5) if rms is not None else None,
            "componentOffsetsPx": offsets,
            "status": ("pass" if (rms is not None and rms <= 0.06
                                  and camera_matches_view is True)
                       else "warn" if rms is not None else "not_checked"),
            "caveat": (
                "band offsets include viewpoint error because the camera was not "
                "fitted to this reference" if camera_matches_view is False else
                "the camera records no source image, so viewpoint consistency "
                "with this reference is unverified" if camera_matches_view is None
                else None),
        })

    overall = ("pass" if rms_all and max(rms_all) <= 0.06
               else "warn" if rms_all else "not_checked")
    C.check(checks, "views_evaluated", "pass" if per_view else "fail",
            f"{len(per_view)} view(s) evaluated")
    C.check(checks, "component_source", "pass" if comp_source == "spec" else "warn",
            f"component boxes from {comp_source}")
    C.check(checks, "band_alignment", overall,
            (f"worst normalised band-offset RMS {max(rms_all):.4f} over "
             f"{len(rms_all)} view(s)" if rms_all else
             "no view had both a camera and measured bands"))
    C.check(checks, "contradictions", "pass" if not contradictions else "warn",
            f"{len(contradictions)} contradiction(s) between projected geometry "
            "and measured reference bands")
    mismatch = [pv["image"] for pv in per_view
                if pv.get("cameraMatchesView") is False]
    unverified = [pv["image"] for pv in per_view
                  if pv.get("cameraMatchesView") is None]
    C.check(checks, "camera_matches_view",
            "pass" if (not mismatch and not unverified) else "warn",
            ("every view was compared with a camera fitted to that same image"
             if not mismatch and not unverified else
             (f"{len(mismatch)} view(s) used a camera fitted to a different "
              "image, so their band offsets include viewpoint error: "
              + ", ".join(os.path.basename(m) for m in mismatch[:4])
              if mismatch else
              f"{len(unverified)} view(s) used a camera with no recorded source "
              "image, so viewpoint consistency is unverified")) +
            (f"; {len(unverified)} view(s) unverified" if (mismatch and unverified)
             else ""))
    C.check(checks, "geometry_conclusion", "not_checked",
            "band offsets mix geometry error with viewpoint error unless the "
            "camera was fitted to that same reference; no geometry conclusion is "
            "drawn here")
    C.check(checks, "pixel_level_verification", "not_checked",
            "band alignment compares projected contract boxes with measured "
            "bands; it does not confirm that the reference pixels match the "
            "model's actual silhouette")

    return {
        "ok": True, "task": "validate_multiview",
        "perView": per_view,
        "componentSource": comp_source,
        "components": [{"name": c.get("name"), "z": c.get("z"),
                        "size": c.get("size")} for c in comps],
        "contradictions": contradictions,
        "status": overall,
        "metrics": {"views": len(per_view),
                    "bandOffsetRmsWorst": round(max(rms_all), 5) if rms_all else None,
                    "contradictions": len(contradictions)},
        "checks": checks, "warnings": warnings,
        "notes": ("Component boxes are projected through each solved camera and "
                  "compared with the measured reference bands. 'status' describes "
                  "band alignment only; it is not a claim that the reference "
                  "pixels match the model."),
    }
