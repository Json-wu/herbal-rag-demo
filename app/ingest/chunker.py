"""按标题与段落切分正文。"""

import re
from dataclasses import dataclass

MAX_CHARS = 400
OVERLAP_CHARS = 80

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    section: str
    text: str
    char_start: int
    char_end: int


def chunk_body(body: str) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for section, text, base in _sections(body):
        for start, end in _windows(text):
            piece = text[start:end]
            if not piece.strip():
                continue
            drafts.append(
                ChunkDraft(
                    chunk_index=len(drafts),
                    section=section,
                    text=piece,
                    char_start=base + start,
                    char_end=base + end,
                )
            )
    return drafts


def _sections(body: str) -> list[tuple[str, str, int]]:
    matches = list(_HEADING.finditer(body))
    if not matches:
        return _plain_section(body)
    sections: list[tuple[str, str, int]] = []
    preamble = body[: matches[0].start()]
    sections.extend(_take(preamble, 0, "正文"))
    for index, match in enumerate(matches):
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        title = match.group(2).strip() or "正文"
        sections.extend(_take(body[content_start:content_end], content_start, title))
    return sections


def _plain_section(body: str) -> list[tuple[str, str, int]]:
    return _take(body, 0, "正文")


def _take(raw: str, origin: int, section: str) -> list[tuple[str, str, int]]:
    stripped = raw.strip()
    if not stripped:
        return []
    offset = raw.find(stripped)
    return [(section, stripped, origin + offset)]


def _windows(text: str) -> list[tuple[int, int]]:
    if len(text) <= MAX_CHARS:
        return [(0, len(text))]
    spans: list[tuple[int, int]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + MAX_CHARS)
        if end < len(text):
            cut = max(text.rfind(mark, start, end) for mark in ("。", "！", "？", "\n"))
            if cut >= start + MAX_CHARS // 2:
                end = cut + 1
        spans.append((start, end))
        if end >= len(text):
            break
        next_start = end - OVERLAP_CHARS
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return spans
