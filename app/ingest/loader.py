"""读取 Markdown / TXT，并解析标题与来源。"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_FRONT_MATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_H1 = re.compile(r"^#\s+(.+)$", re.M)


@dataclass(frozen=True)
class LoadedDocument:
    title: str
    source: str
    filename: str
    body: str
    content_hash: str


def load_file(path: Path) -> LoadedDocument:
    raw = path.read_text(encoding="utf-8-sig")
    return load_text(raw, path.name)


def load_text(text: str, filename: str) -> LoadedDocument:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.startswith("\ufeff"):
        normalized = normalized[1:]
    meta, body = _split_front_matter(normalized)
    title = meta.get("title") or _first_h1(body) or Path(filename).stem
    source = meta.get("source") or "未标注来源"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return LoadedDocument(
        title=title,
        source=source,
        filename=Path(filename).name,
        body=body,
        content_hash=digest,
    )


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, text[match.end() :]


def _first_h1(body: str) -> str:
    match = _H1.search(body)
    return match.group(1).strip() if match else ""
