from app.ingest.chunker import chunk_body
from app.ingest.loader import load_text


def test_markdown_keeps_section_and_drops_front_matter():
    raw = """---
title: 黄芪
source: 测试来源
---

# 黄芪

## 性味归经

黄芪性味甘、微温。
"""
    loaded = load_text(raw, "黄芪.md")
    chunks = chunk_body(loaded.body)
    assert loaded.title == "黄芪"
    assert loaded.source == "测试来源"
    assert loaded.filename == "黄芪.md"
    assert len(chunks) == 1
    assert chunks[0].section == "性味归经"
    assert chunks[0].text == "黄芪性味甘、微温。"
    assert "---" not in chunks[0].text
    assert loaded.body[chunks[0].char_start : chunks[0].char_end] == chunks[0].text


def test_txt_uses_filename_and_body_section():
    loaded = load_text("只有正文。", "笔记.txt")
    chunks = chunk_body(loaded.body)
    assert loaded.title == "笔记"
    assert loaded.source == "未标注来源"
    assert chunks[0].section == "正文"
    assert chunks[0].text == "只有正文。"


def test_empty_text_has_no_chunks():
    assert chunk_body("") == []
    assert chunk_body("  \n\n  ") == []


def test_long_text_overlaps_and_stays_inside_source():
    body = ("甲" * 20 + "。") * 40
    chunks = chunk_body(body)
    assert len(chunks) >= 2
    assert chunks[0].section == "正文"
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].text[-30:] in chunks[1].text
    for chunk in chunks:
        assert body[chunk.char_start : chunk.char_end] == chunk.text
        assert len(chunk.text) <= 400
