"""引用标记必须对应本轮返回的片段。"""

import re

from app.retrieve.search import Hit
from app.schemas import Citation
from app.texts import INSUFFICIENT

_MARKER = re.compile(r"\[(\d+)\]")


def validate_citations(answer: str, hits: list[Hit]) -> tuple[str, list[Citation], bool]:
    valid = set(range(1, len(hits) + 1))
    used: list[int] = []

    def replace(match: re.Match[str]) -> str:
        marker = int(match.group(1))
        if marker not in valid:
            return ""
        if marker not in used:
            used.append(marker)
        return f"[{marker}]"

    cleaned = _MARKER.sub(replace, answer)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if not used:
        return INSUFFICIENT, [], True
    citations = [Citation(marker=marker, chunk_id=hits[marker - 1].chunk_id) for marker in used]
    return cleaned, citations, False
