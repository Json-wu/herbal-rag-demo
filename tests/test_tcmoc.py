from app.ingest.service import ingest_file
from app.ingest.tcmoc import book_filename, count_imported, import_books, to_markdown
from app.retrieve.search import search

RAW = """书名：测试

<篇名>目录
甘草
<篇名>甘草
味甘，平。
主五脏六腑寒热邪气。
<篇名>空条
<
"""


def test_to_markdown_keeps_entries_and_drops_catalog():
    text = to_markdown(RAW, "神农本草经", "来源 https://github.com/lab99x/tcmoc")
    assert "title: 神农本草经" in text
    assert "## 甘草" in text
    assert "味甘，平。主五脏六腑寒热邪气。" in text
    assert "## 目录" not in text
    assert "## 空条" not in text


def test_import_skips_when_filename_exists(conn):
    calls = {"n": 0}

    def fetcher(url: str) -> str:
        calls["n"] += 1
        assert url.startswith("https://raw.githubusercontent.com/lab99x/tcmoc/master/books/")
        return RAW

    first = import_books(conn, fetcher=fetcher)
    assert calls["n"] == 3
    assert count_imported(conn) == 3
    assert all(not item["skipped"] for item in first)
    assert book_filename("神农本草经") in {item["filename"] for item in first}

    second = import_books(conn, fetcher=fetcher)
    assert calls["n"] == 3
    assert all(item["skipped"] for item in second)

    import_books(conn, refresh=True, fetcher=fetcher)
    assert calls["n"] == 6


def test_long_entry_keeps_the_property_sentence(conn, tmp_path):
    filler = "叶似槐叶而微尖小，开黄紫花。" * 40
    target = tmp_path / "tcmoc-本草纲目.md"
    target.write_text(
        "---\ntitle: 本草纲目\nsource: 测试\n---\n\n# 本草纲目\n\n## 黄耆\n\n"
        + filler
        + "【气味】甘，微温，无毒。\n",
        encoding="utf-8",
    )
    ingest_file(conn, target)
    for index in range(45):
        path = tmp_path / f"decoy-{index:02d}.md"
        path.write_text(
            f"---\ntitle: 杂记{index}\nsource: 测试\n---\n\n# 杂记\n\n## 备忘\n\n气味甘温，并不讨论目标药。\n",
            encoding="utf-8",
        )
        ingest_file(conn, path)
    hits = search(conn, "黄耆在本草纲目中的气味是什么？", top_k=3, min_score=0.5)
    assert any("甘，微温" in hit.text and hit.section == "黄耆" for hit in hits)
