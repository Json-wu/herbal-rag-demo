from app.ingest.service import ingest_file, ingest_path
from app.retrieve.search import search
from app.retrieve.store import connect
from app.retrieve.text import extract_entities
from app.texts import SAMPLE_SOURCE


def test_entities_for_demo_questions():
    assert extract_entities("黄芪的性味与归经是什么？") == ["黄芪", "性味", "归经"]
    assert extract_entities("资料中如何描述甘草？") == ["甘草"]
    assert extract_entities("什么是四气五味？") == ["四气五味"]
    assert extract_entities("金银花和连翘在资料中有什么不同？") == ["金银花", "连翘"]
    assert extract_entities("资料里对麻黄有哪些使用注意？") == ["麻黄", "使用注意"]
    assert extract_entities("阿司匹林适用于哪些疾病？") == ["阿司匹林"]


def test_sample_metadata_and_known_hits(conn, sample_dir):
    ingest_path(conn, sample_dir)
    hits = search(conn, "黄芪的性味与归经是什么？", top_k=5, min_score=0.5)
    assert hits
    assert hits[0].title == "黄芪"
    assert hits[0].section == "性味归经"
    assert hits[0].filename == "黄芪.md"
    assert hits[0].source == SAMPLE_SOURCE
    assert "微温" in hits[0].text
    assert all(hit.title == "黄芪" for hit in hits)

    compare = search(conn, "金银花和连翘在资料中有什么不同？", top_k=5, min_score=0.5)
    assert {hit.title for hit in compare} == {"金银花", "连翘"}

    missing = search(conn, "阿司匹林适用于哪些疾病？", top_k=5, min_score=0.5)
    assert missing == []


def test_index_persists_after_reopen(settings, sample_dir):
    first = connect(settings.db_path)
    ingest_path(first, sample_dir)
    first.close()
    second = connect(settings.db_path)
    hits = search(second, "什么是四气五味？", top_k=5, min_score=0.5)
    second.close()
    assert hits[0].title == "四气五味"
    assert "寒、热、温、凉" in hits[0].text


def test_reimport_replaces_changed_file_and_skips_same_hash(conn, tmp_path):
    path = tmp_path / "甘草.md"
    path.write_text("---\ntitle: 甘草\nsource: 旧来源\n---\n\n# 甘草\n\n旧记载。\n", encoding="utf-8")
    first = ingest_file(conn, path)
    assert first["skipped"] is False
    assert search(conn, "资料中如何描述甘草？", top_k=5, min_score=0.5)[0].text.startswith("旧记载")

    again = ingest_file(conn, path)
    assert again["skipped"] is True

    path.write_text("---\ntitle: 甘草\nsource: 新来源\n---\n\n# 甘草\n\n新记载含调和二字。\n", encoding="utf-8")
    updated = ingest_file(conn, path)
    assert updated["skipped"] is False
    assert updated["source"] == "新来源"
    hits = search(conn, "资料中如何描述甘草？", top_k=5, min_score=0.5)
    assert len(hits) == 1
    assert "新记载" in hits[0].text
    assert "旧记载" not in hits[0].text
