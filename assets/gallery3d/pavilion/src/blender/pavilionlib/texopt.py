# -*- coding: utf-8 -*-
"""贴图体积优化：把程序化生成的 PNG 压成 Web 发布用的混合格式。

为什么需要它：
  textures.py 是纯 numpy 噪点图，2048² 的无损 PNG 单张 3~9 MB，
  11 材质 × 3 张一共 40+ MB，塞进 GLB 后是 56 MB —— Web 首屏灾难。

策略（体积 / 质量 / 通道正确性三者折中）：
  basecolor → JPEG q92，保持原尺寸
      彩色漫反射，人眼对 JPEG 误差不敏感；sRGB 下 q92 肉眼无感。
  normal    → JPEG q92，上限 1024
      glTF 法线是切线空间两通道，JPEG 的轻微模糊只让凹凸略钝，
      不会引入可见色块；降到 1024 直接省 3/4 体积。
  orm       → JPEG q92 **4:4:4（不做色度下采样）**，保持原尺寸
      R=AO / G=Roughness / B=Metallic 三通道分别被下游读取。4:2:0 的色度下采样
      会让金属度渗进粗糙度；4:4:4 三通道独立编码，串扰可忽略。
      实测 22.96 MB -> 8.18 MB。像素级转换交给系统 python + Pillow
      （Blender 内置 python 没有 Pillow，且 imbuf JPEG 固定 4:2:0）。

原 PNG 不删除，移到 tex_dir/_src/ 下留档（.blend 源工程可回退）。

用法（在 assemble 管线内自动调用；也可单跑）：
  blender -b --factory-startup -P pavilionlib/texopt.py -- --tex D:\\Design\\textures
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import bpy

JPEG_Q = 92
NORMAL_MAX = 1024
CONVERT = ("basecolor", "normal")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ORM_SCRIPT = os.path.join(ROOT, "tools", "orm_jpeg.py")


def _convert_orm(tex_dir):
    """ORM -> 4:4:4 JPEG。借系统 python + Pillow（Blender 内置 python 没有 PIL）。"""
    if not os.path.exists(ORM_SCRIPT):
        print(f"[texopt] 缺 {ORM_SCRIPT}，ORM 保持 PNG")
        return
    py = shutil.which("python") or shutil.which("python3")
    if not py:
        print("[texopt] 找不到系统 python，ORM 保持 PNG")
        return
    try:
        r = subprocess.run([py, ORM_SCRIPT, tex_dir, str(JPEG_Q)],
                           capture_output=True, text=True, timeout=900,
                           encoding="utf-8", errors="replace")
        for line in (r.stdout or "").splitlines():
            if line.strip():
                print(line)
        if r.returncode != 0:
            print(f"[texopt] ORM 转换退出码 {r.returncode}: {(r.stderr or '')[:400]}")
    except Exception as e:
        print(f"[texopt] ORM 转换异常: {e}")


def _deal(i, key, attr):
    ext = ".jpg"
    src = os.path.join(i, f"{key}_{attr}.png")
    if not os.path.exists(src):
        return 0
    dst = os.path.join(i, f"{key}_{attr}.jpg")
    try:
        img = bpy.data.images.load(src, check_existing=False)
    except Exception as e:
        print(f"[texopt] {key}_{attr} 载入失败: {e}")
        return 0
    try:
        w, h = img.size[:]
        if attr == "normal" and max(w, h) > NORMAL_MAX:
            img.scale(NORMAL_MAX, NORMAL_MAX)
        img.file_format = "JPEG"
        try:
            bpy.context.scene.render.image_settings.quality = JPEG_Q
        except Exception:
            pass
        img.filepath_raw = dst
        img.save()
        # 校验产物
        if not os.path.exists(dst) or os.path.getsize(dst) < 200:
            print(f"[texopt] !! {key}_{attr} 写盘失败")
            return 0
        got = os.path.getsize(dst)
        old = os.path.getsize(src)
        print(f"[texopt] {key:<11} {attr:<9} {old/1024:8.1f} KB -> {got/1024:8.1f} KB"
              f"  ({got/old*100:5.1f}%)  {w}x{h}"
              + (f" -> {NORMAL_MAX}x{NORMAL_MAX}" if attr == "normal" and max(w, h) > NORMAL_MAX else ""))
        return got
    except Exception as e:
        print(f"[texopt] {key}_{attr} 转换异常: {e}")
        return 0
    finally:
        try:
            bpy.data.images.remove(img)
        except Exception:
            pass


def optimize(tex_dir, archive=True):
    """转换 tex_dir 下的 basecolor / normal 为 jpg。返回 (before, after) 字节数。"""
    if not os.path.isdir(tex_dir):
        print(f"[texopt] 目录不存在: {tex_dir}")
        return 0, 0
    keys = sorted({f.rsplit("_", 1)[0] for f in os.listdir(tex_dir)
                   if f.endswith(".png") and "_" in f})
    before = sum(os.path.getsize(os.path.join(tex_dir, f))
                 for f in os.listdir(tex_dir) if f.endswith(".png"))
    for key in keys:
        for attr in CONVERT:
            _deal(tex_dir, key, attr)
    _convert_orm(tex_dir)
    if archive:
        src_dir = os.path.join(tex_dir, "_src")
        os.makedirs(src_dir, exist_ok=True)
        for key in keys:
            for attr in CONVERT:
                p = os.path.join(tex_dir, f"{key}_{attr}.png")
                if os.path.exists(p):
                    try:
                        shutil.move(p, os.path.join(src_dir, os.path.basename(p)))
                    except Exception:
                        pass
    after = sum(os.path.getsize(os.path.join(tex_dir, f))
                for f in os.listdir(tex_dir) if os.path.isfile(os.path.join(tex_dir, f)))
    print(f"[texopt] 合计 {before/1048576:.2f} MB -> {after/1048576:.2f} MB "
          f"({after/max(before,1)*100:.1f}%)")
    return before, after


def _main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    tex = r"D:\Design\textures"
    i = 0
    while i < len(argv):
        if argv[i] == "--tex" and i + 1 < len(argv):
            tex = argv[i + 1]
            i += 2
        else:
            i += 1
    optimize(tex)


if __name__ == "__main__":
    _main()