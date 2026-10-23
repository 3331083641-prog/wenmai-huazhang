"""Check tracked publication inputs without printing credential values.

Run from any directory: python scripts/check_publication.py
The index supplies the file list, including newly staged files. Contents are
checked in the working tree; stage final changes before running this gate.
Only the Python standard library is required.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


FORBIDDEN_DIRS = {
    "node_modules", "venv", ".venv", "__pycache__", ".cache",
    ".huggingface", "logs", ".backup", "_backup_before_cleanup",
    "_trash_backup", ".pytest_cache", ".mypy_cache", ".aws", ".ssh",
    ".secrets", "dist", "outputs", "uploads",
}
CREDENTIAL_EXTENSIONS = {".pem", ".key", ".p12", ".pfx", ".jks"}
WEIGHT_EXTENSIONS = {".safetensors", ".gguf", ".ggml", ".ckpt", ".pth", ".pt", ".onnx", ".tflite"}
TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json",
    ".md", ".txt", ".html", ".htm", ".css", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".ps1", ".bat", ".cmd", ".sh", ".xml", ".svg",
}
TOKEN_PATTERNS = [
    re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{30,}"),
]
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
USER_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!Public(?:[\\/]|\b))[^\\/\s\"'`]+", re.I)
ASSIGNMENT = re.compile(
    r'''(?i)["']?(?:api_key|access_token|auth_token|secret_key|password)["']?\s*[:=]\s*["']([^"'\s]{12,})["']'''
)
PLACEHOLDER = re.compile(
    r"(?i)(?:your[_ -]|example|placeholder|dummy|sample|test[_-]|replace[_-]|change[_-]|"
    r"not[_-]?(?:a[_-]?)?real|redacted|insert[_-]|这里|填写|替换|示例|x{6,}|\*{4,}|<|>|\{|\}|\$)"
)


def is_placeholder(value: str) -> bool:
    if PLACEHOLDER.search(value):
        return True
    suffix = value.rsplit("-", 1)[-1].replace("_", "")
    return len(suffix) >= 12 and len(set(suffix.lower())) <= 2


def forbidden_reason(path: Path) -> str | None:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if parts & FORBIDDEN_DIRS:
        return "forbidden_runtime_or_cache_directory"
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "environment_credentials_file"
    if path.suffix.lower() in CREDENTIAL_EXTENSIONS:
        return "credential_file"
    if path.suffix.lower() in WEIGHT_EXTENSIONS:
        return "model_weights"
    if name in {"credentials", "credentials.json", "service-account.json", "id_rsa", "id_ed25519"}:
        return "credential_file"
    if path.suffix.lower() in {".log", ".pyc", ".pyo"}:
        return "runtime_artifact"
    if name in {"pytorch_model.bin", "adapter_model.bin", "model.bin"}:
        return "model_weights"
    return None


class ReadmeHTML(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, int, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value and ((tag in {"img", "source"} and key == "src") or (tag == "a" and key == "href")):
                self.links.append((value, self.getpos()[0], tag != "a"))


def readme_links(text: str) -> list[tuple[str, int, bool]]:
    # Code examples can contain illustrative URLs and are not rendered links.
    rendered = re.sub(r"^```[^\n]*\n.*?^```[^\n]*$", lambda m: "\n" * m.group().count("\n"), text, flags=re.M | re.S)
    result: list[tuple[str, int, bool]] = []
    definitions = {
        m.group(1).strip().casefold(): m.group(2).strip("<>")
        for m in re.finditer(r"^\s*\[([^\]]+)\]:\s*(<[^>]+>|\S+)", rendered, re.M)
    }
    for m in re.finditer(r"(!?)\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", rendered):
        result.append((m.group(2).strip("<>"), rendered.count("\n", 0, m.start()) + 1, bool(m.group(1))))
    for m in re.finditer(r"(!?)\[([^\]\n]+)\]\[([^\]\n]*)\]", rendered):
        key = (m.group(3) or m.group(2)).strip().casefold()
        if key in definitions:
            result.append((definitions[key], rendered.count("\n", 0, m.start()) + 1, bool(m.group(1))))
    parser = ReadmeHTML()
    parser.feed(rendered)
    result.extend(parser.links)
    return result


def check(root: Path, pillow: bool = False) -> dict:
    raw = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
    paths = sorted({item.decode("utf-8") for item in raw.split(b"\0") if item})
    tracked = set(paths)
    findings: list[dict] = []
    counters: Counter = Counter()

    def add(level: str, path: str, category: str, line: int | None = None) -> None:
        item = {"level": level, "path": path, "category": category}
        if line is not None:
            item["line"] = line
        findings.append(item)

    for rel in paths:
        path = root / rel
        reason = forbidden_reason(Path(rel))
        if reason:
            add("error", rel, reason)
            continue  # In particular, never read .env or credential contents.
        if not path.is_file():
            add("error", rel, "tracked_file_missing_from_worktree")
            continue
        size = path.stat().st_size
        counters["tracked_bytes"] += size
        if size > 50 * 1024 * 1024:
            add("warning", rel, "file_larger_than_50MiB")
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {"LICENSE", ".gitignore"}:
            continue
        try:
            content = path.read_text(encoding="utf-8-sig")
        except UnicodeError:
            add("warning", rel, "text_not_utf8")
            continue
        counters["text_files_scanned"] += 1
        for line_number, line in enumerate(content.splitlines(), 1):
            if PRIVATE_KEY.search(line):
                add("error", rel, "private_key_header", line_number)
            for pattern in TOKEN_PATTERNS:
                if any(not is_placeholder(m.group()) for m in pattern.finditer(line)):
                    add("error", rel, "token_like_secret", line_number)
                    break
            if any(not is_placeholder(m.group(1)) for m in ASSIGNMENT.finditer(line)):
                add("error", rel, "credential_literal_assignment", line_number)
            if USER_PATH.search(line):
                add("warning", rel, "private_user_absolute_path", line_number)
        if rel != "README.md":
            continue
        for target, line, is_image in readme_links(content):
            if re.match(r"^[A-Za-z]:[\\/]", target):
                add("error", rel, "readme_machine_local_path", line)
                continue
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            decoded = unquote(parsed.path).replace("\\", "/")
            candidate = (root / decoded.lstrip("/")).resolve()
            try:
                local = candidate.relative_to(root).as_posix()
            except ValueError:
                add("error", rel, "readme_link_outside_repository", line)
                continue
            counters["readme_local_links"] += 1
            if not candidate.exists():
                add("error", rel, "readme_local_target_missing", line)
            elif candidate.is_file() and local not in tracked:
                add("error", rel, "readme_local_target_not_tracked", line)
            elif candidate.is_dir() and not any(p.startswith(local.rstrip("/") + "/") for p in tracked):
                add("error", rel, "readme_directory_not_tracked", line)
            elif is_image and not candidate.is_file():
                add("error", rel, "readme_image_not_file", line)
            elif is_image and pillow and candidate.suffix.lower() != ".svg":
                try:
                    from PIL import Image
                    with Image.open(candidate) as img:
                        img.verify()
                except ImportError:
                    add("warning", rel, "optional_pillow_not_installed", line)
                except Exception:
                    add("error", rel, "readme_image_decode_failed", line)
    return {
        "tracked_files": len(paths),
        **dict(counters),
        "errors": sum(item["level"] == "error" for item in findings),
        "warnings": sum(item["level"] == "warning" for item in findings),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pillow", action="store_true", help="Optionally verify README raster images with installed Pillow")
    parser.add_argument("--json", action="store_true", help="Print a structured report; never includes matched credential values")
    args = parser.parse_args()
    try:
        result = check(args.root.resolve(), args.pillow)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Publication check could not complete: {type(exc).__name__}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        for finding in result["findings"]:
            location = finding["path"] + (f":{finding['line']}" if "line" in finding else "")
            print(f"{finding['level'].upper()} {location} {finding['category']}")
        print(f"Checked {result['tracked_files']} tracked files; {result['errors']} errors, {result['warnings']} warnings.")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
