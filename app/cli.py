"""命令行导入。用法：python -m app.cli ingest data/sample"""

import argparse
from pathlib import Path

from app.config import get_settings
from app.ingest.service import ingest_path
from app.ingest.tcmoc import import_books
from app.retrieve.store import connect


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest", help="导入 Markdown 或 TXT 文件，或整个目录")
    ingest.add_argument("path")
    pull = sub.add_parser("import-tcmoc", help="从中医开源医典拉取选定古籍并写入索引")
    pull.add_argument("--refresh", action="store_true", help="已存在时也重新下载")
    args = parser.parse_args(argv)
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        if args.command == "ingest":
            results = ingest_path(conn, Path(args.path))
        else:
            results = import_books(conn, refresh=args.refresh)
    finally:
        conn.close()
    if args.command != "ingest":
        return
    if not results:
        print("没有找到 Markdown 或 TXT 文件")
        return
    for item in results:
        state = "跳过" if item["skipped"] else "导入"
        print(f"{state}\t{item['filename']}\t{item['title']}\t片段 {item['chunks']}")


if __name__ == "__main__":
    main()
