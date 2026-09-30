"""从本地索引检索片段，并用关键词覆盖率作为相关度。"""

import sqlite3
from dataclasses import dataclass

from app.retrieve.text import extract_entities, fts_query


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    title: str
    source: str
    section: str
    filename: str
    text: str
    score: float


def search(conn: sqlite3.Connection, question: str, top_k: int, min_score: float) -> list[Hit]:
    entities = extract_entities(question)
    query = fts_query(entities)
    if not entities or not query:
        return []
    limit = max(top_k * 4, 20)
    try:
        rows = conn.execute(
            """
            SELECT c.id, c.section, c.text, d.title, d.source, d.filename,
                   bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    scored: list[Hit] = []
    for row in rows:
        haystack = f"{row['title']}\n{row['section']}\n{row['text']}"
        covered = sum(1 for entity in entities if entity in haystack)
        score = covered / len(entities)
        if score < min_score:
            continue
        scored.append(
            Hit(
                chunk_id=row["id"],
                title=row["title"],
                source=row["source"],
                section=row["section"],
                filename=row["filename"],
                text=row["text"],
                score=round(score, 4),
            )
        )
    scored.sort(key=lambda hit: (-hit.score, hit.filename, hit.chunk_id))
    return scored[:top_k]
