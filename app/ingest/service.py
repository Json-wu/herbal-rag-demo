"""把文件写入资料库。"""

from pathlib import Path

from app.ingest.chunker import chunk_body
from app.ingest.loader import load_file
from app.retrieve.store import save_document

_SUFFIXES = {".md", ".txt", ".markdown"}


def ingest_path(conn, path: Path) -> list[dict]:
    path = path.expanduser().resolve()
    if path.is_file():
        return [ingest_file(conn, path)]
    files = [
        item
        for item in path.rglob("*")
        if item.is_file() and not item.name.startswith(".") and item.suffix.lower() in _SUFFIXES
    ]
    return [ingest_file(conn, item) for item in sorted(files)]


def ingest_file(conn, path: Path) -> dict:
    loaded = load_file(path)
    drafts = chunk_body(loaded.body)
    return save_document(conn, loaded, drafts)
