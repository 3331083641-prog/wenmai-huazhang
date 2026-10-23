"""用本地 Ollama Qwen3-VL 看一张图并回答问题（离线，不走任何付费接口）。

用法：
    python scripts/interactive/look.py <图片> [问题]

说明：本地 4B 模型不擅长自由给出坐标框，但非常适合「这张图整体如何 /
某个区域里是什么 / 有没有明显排版错误」这类判断题。截图审阅就用它。
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

ENDPOINT = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3-vl:4b-instruct-q4_K_M"


def look(image_path: Path, question: str, timeout: int = 300) -> str:
    payload = {
        "model": MODEL,
        "prompt": question,
        "images": [base64.b64encode(image_path.read_bytes()).decode("ascii")],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 700},
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return (data.get("response") or "").strip()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("用法：python scripts/interactive/look.py <图片> [问题]")
    image = Path(sys.argv[1]).resolve()
    if not image.exists():
        raise SystemExit(f"找不到图片：{image}")
    question = sys.argv[2] if len(sys.argv) > 2 else "请用中文详细描述这张图片的内容与版式。"
    print(look(image, question))


if __name__ == "__main__":
    main()