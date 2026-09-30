"""命令行导入。用法：python -m app.cli ingest data/sample"""

import argparse
from pathlib import Path

from app.config import get_settings
from app.ingest.service import ingest_path
from app.retrieve.store import connect


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="导入 Markdown 或 TXT 文件，或整个目录")
    ingest.add_argument("path")
    args = parser.parse_args(argv)
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        results = ingest_path(conn, Path(args.path))
    finally:
        conn.close()
    if not results:
        print("没有找到 Markdown 或 TXT 文件")
        return
    for item in results:
        state = "跳过" if item["skipped"] else "导入"
        print(f"{state}\t{item['filename']}\t{item['title']}\t片段 {item['chunks']}")


if __name__ == "__main__":
    main()
