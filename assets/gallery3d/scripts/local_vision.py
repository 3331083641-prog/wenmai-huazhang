"""用本地 Qwen3-VL（ollama，免费、离线）看图，补上统计量看不出来的语义判断。

    python local_vision.py <图片路径> [问题]

为什么需要它：measure_v2 / verify_web 只能回答"覆盖多少、多亮、色带像不像"，
回答不了"这看起来像一座两层重檐楼阁，还是一个方盒子"。
本地 4B 视觉模型足够判断这类粗粒度语义，而且不产生费用、不上传外网。
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.request

ENDPOINT = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3-vl:4b-instruct-q4_K_M"

DEFAULT_PROMPT = (
    "请客观描述这张图里的建筑，只说你真的看见的，不要推测：\n"
    "1) 建筑是几层？屋顶是什么形式（单檐/重檐、庑殿/歇山/攒尖）？\n"
    "2) 有没有台基？台基是方形还是圆形？大约占画面高度的几分之几？\n"
    "3) 主色是哪几种（用颜色名，不要用色号）？\n"
    "4) 能看到檐下的斗拱/柱子/门窗/灯笼/匾额吗？逐一回答有还是没有。\n"
    "5) 这张图是室外还是室内？如果是渲染图，哪里看起来不自然？\n"
    "用中文回答，控制在 200 字以内。"
)


def ask(image_path: str, prompt: str, timeout: int = 300) -> str:
    with open(image_path, "rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [encoded],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 400},
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return (body.get("response") or "").strip()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PROMPT
    print(f"== {path}")
    print(ask(path, prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())