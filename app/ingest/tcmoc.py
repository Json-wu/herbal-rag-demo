"""从中医开源医典拉取选定古籍，转成 Markdown 后写入本地索引。

只收录公版古籍，不拉取整库。提问时不再访问 GitHub。
"""

import os
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import quote

from app.ingest.service import ingest_file

REPO = "https://github.com/lab99x/tcmoc"
RAW = "https://raw.githubusercontent.com/lab99x/tcmoc/master/books/"
_ENTRY = re.compile(r"<篇名>")
_SKIP_HEADINGS = {"目录", "校勘记"}

# 允许名单：古代本草与医经。仓库里还有近现代著作，不在此列。
BOOKS = (
    {
        "file": "(6.1.1-02438.3).本草-本草经-本经辑本.《神农本草经》(三卷).吴普.魏.md",
        "title": "神农本草经",
        "source": f"《神农本草经》孙星衍辑本（清）；文本来自中医开源医典 {REPO}",
    },
    {
        "file": "437-黄帝内经素问.txt",
        "title": "黄帝内经素问",
        "source": f"《黄帝内经素问》；文本来自中医开源医典 {REPO}",
    },
    {
        "file": "(6.2.3-02511.1).本草-综合本草-明代本草.《本草纲目》(五十二卷).李时珍.md",
        "title": "本草纲目",
        "source": f"《本草纲目》李时珍（明）；文本来自中医开源医典 {REPO}",
    },
)


def book_filename(title: str) -> str:
    return f"tcmoc-{title}.md"


def book_url(filename: str) -> str:
    return RAW + quote(filename)


def fetch_text(url: str, timeout: float = 120) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "HerbalRAGDemo/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def checkout_books() -> dict[str, str]:
    """用 git 从 github.com 只检出三部书。不走 raw.githubusercontent.com。"""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "tcmoc"
        clone = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                f"{REPO}.git",
                str(dest),
            ],
            env=env,
            timeout=120,
        )
        if clone.returncode != 0:
            raise RuntimeError("无法从 GitHub 克隆中医开源医典")
        paths = [f"/books/{book['file']}" for book in BOOKS]
        picked = subprocess.run(
            ["git", "sparse-checkout", "set", "--no-cone", *paths],
            cwd=dest,
            env=env,
            timeout=180,
        )
        if picked.returncode != 0:
            raise RuntimeError("无法从中医开源医典检出选定古籍")
        texts: dict[str, str] = {}
        for book in BOOKS:
            path = dest / "books" / book["file"]
            if not path.is_file():
                raise FileNotFoundError(book["file"])
            texts[book["file"]] = path.read_text(encoding="utf-8-sig")
        return texts


def to_markdown(raw: str, title: str, source: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    if text.startswith("\ufeff"):
        text = text[1:]
    sections: list[str] = []
    for part in _ENTRY.split(text):
        lines = [line.strip() for line in part.splitlines()]
        lines = [line for line in lines if line]
        if not lines:
            continue
        heading = lines[0]
        if heading in _SKIP_HEADINGS or heading.startswith("<"):
            continue
        body = "".join(line for line in lines[1:] if not line.startswith("<"))
        if len(body) < 4:
            continue
        sections.append(f"## {heading}\n\n{body}")
    if not sections:
        body = "".join(
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.strip().startswith("<")
        )
        sections = [body]
    front = f"---\ntitle: {title}\nsource: {source}\n---\n\n# {title}\n\n"
    return front + "\n\n".join(sections) + "\n"


def count_imported(conn) -> int:
    row = conn.execute(
        "SELECT count(*) FROM documents WHERE filename LIKE 'tcmoc-%'"
    ).fetchone()
    return int(row[0])


def import_books(conn, *, refresh: bool = False, fetcher=None) -> list[dict]:
    results: list[dict] = []
    texts: dict[str, str] | None = None
    for book in BOOKS:
        filename = book_filename(book["title"])
        exists = conn.execute(
            "SELECT 1 FROM documents WHERE filename = ?",
            (filename,),
        ).fetchone()
        if exists and not refresh:
            results.append(
                {
                    "filename": filename,
                    "title": book["title"],
                    "skipped": True,
                    "chunks": 0,
                }
            )
            print(f"跳过\t{filename}\t已在索引中", flush=True)
            continue
        if fetcher is not None:
            raw = fetcher(book_url(book["file"]))
        else:
            if texts is None:
                texts = checkout_books()
            raw = texts[book["file"]]
        markdown = to_markdown(raw, book["title"], book["source"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / filename
            path.write_text(markdown, encoding="utf-8")
            saved = ingest_file(conn, path)
        results.append(saved)
        state = "跳过" if saved["skipped"] else "导入"
        print(f"{state}\t{filename}\t片段 {saved['chunks']}", flush=True)
    return results
