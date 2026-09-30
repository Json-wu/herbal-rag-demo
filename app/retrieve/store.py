"""SQLite 资料表与 FTS5 索引。"""

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.ingest.chunker import ChunkDraft
from app.ingest.loader import LoadedDocument
from app.retrieve.text import index_tokens


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            filename TEXT NOT NULL UNIQUE,
            content_hash TEXT NOT NULL,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(id),
            chunk_index INTEGER NOT NULL,
            section TEXT NOT NULL,
            text TEXT NOT NULL,
            char_start INTEGER NOT NULL,
            char_end INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED,
            body,
            tokenize = 'unicode61'
        );
        """
    )


def count_documents(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT count(*) FROM documents").fetchone()[0])


def list_documents(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT d.id, d.title, d.source, d.filename, d.imported_at,
               (SELECT count(*) FROM chunks c WHERE c.document_id = d.id) AS chunks
        FROM documents d
        ORDER BY d.filename
        """
    ).fetchall()
    return [dict(row) for row in rows]


def save_document(conn: sqlite3.Connection, loaded: LoadedDocument, drafts: list[ChunkDraft]) -> dict:
    doc_id = hashlib.sha256(loaded.filename.encode("utf-8")).hexdigest()[:16]
    with conn:
        existing = conn.execute(
            "SELECT content_hash FROM documents WHERE id = ?",
            (doc_id,),
        ).fetchone()
        if existing and existing["content_hash"] == loaded.content_hash:
            count = conn.execute(
                "SELECT count(*) FROM chunks WHERE document_id = ?",
                (doc_id,),
            ).fetchone()[0]
            return {
                "filename": loaded.filename,
                "title": loaded.title,
                "source": loaded.source,
                "chunks": int(count),
                "skipped": True,
            }
        _delete_document(conn, doc_id)
        conn.execute(
            """
            INSERT INTO documents (id, title, source, filename, content_hash, imported_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                loaded.title,
                loaded.source,
                loaded.filename,
                loaded.content_hash,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        for draft in drafts:
            chunk_id = f"{doc_id}:{draft.chunk_index:04d}"
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, chunk_index, section, text, char_start, char_end)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    doc_id,
                    draft.chunk_index,
                    draft.section,
                    draft.text,
                    draft.char_start,
                    draft.char_end,
                ),
            )
            conn.execute(
                "INSERT INTO chunks_fts (chunk_id, body) VALUES (?, ?)",
                (chunk_id, index_tokens(loaded.title, draft.section, draft.text)),
            )
    return {
        "filename": loaded.filename,
        "title": loaded.title,
        "source": loaded.source,
        "chunks": len(drafts),
        "skipped": False,
    }


def _delete_document(conn: sqlite3.Connection, doc_id: str) -> None:
    rows = conn.execute("SELECT id FROM chunks WHERE document_id = ?", (doc_id,)).fetchall()
    for row in rows:
        conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (row["id"],))
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
