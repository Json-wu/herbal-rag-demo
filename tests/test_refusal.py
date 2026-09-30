import httpx

from app.config import Settings
from app.generate.answer import answer_question
from app.ingest.service import ingest_path
from app.texts import INSUFFICIENT


def test_out_of_corpus_question_refuses(conn, sample_dir, settings):
    ingest_path(conn, sample_dir)
    result = answer_question("阿司匹林适用于哪些疾病？", conn, settings)
    assert result.refused is True
    assert result.refusal_reason == "insufficient_evidence"
    assert result.answer == INSUFFICIENT
    assert result.citations == []
    assert "适应" not in result.answer


def test_extractive_citations_match_hits(conn, sample_dir, settings):
    ingest_path(conn, sample_dir)
    result = answer_question("黄芪的性味与归经是什么？", conn, settings)
    assert result.refused is False
    assert result.mode == "extractive"
    assert "微温" in result.answer
    assert result.citations
    for cite in result.citations:
        assert f"[{cite.marker}]" in result.answer
        assert result.hits[cite.marker - 1].chunk_id == cite.chunk_id


def test_llm_without_key_stays_on_extractive(conn, sample_dir, settings):
    ingest_path(conn, sample_dir)
    online = Settings(
        database_path=settings.database_path,
        llm_mode="llm",
        llm_api_key="",
    )
    result = answer_question("资料中如何描述甘草？", conn, online)
    assert result.mode == "extractive"
    assert "调和诸药" in result.answer


def test_llm_non_json_does_not_pass_through(conn, sample_dir, monkeypatch):
    ingest_path(conn, sample_dir)
    settings = Settings(
        database_path=str(conn.execute("PRAGMA database_list").fetchone()[2]),
        llm_mode="llm",
        llm_api_key="test-key",
    )

    def fake_chat(*_args, **_kwargs):
        return "黄芪能治百病，无需引用。"

    monkeypatch.setattr("app.generate.answer.complete_chat", fake_chat)
    result = answer_question("黄芪的性味与归经是什么？", conn, settings)
    assert result.answer == INSUFFICIENT
    assert "百病" not in result.answer
    assert result.hits


def test_llm_invalid_citation_refuses(conn, sample_dir, monkeypatch):
    ingest_path(conn, sample_dir)
    settings = Settings(
        database_path=str(conn.execute("PRAGMA database_list").fetchone()[2]),
        llm_mode="llm",
        llm_api_key="test-key",
    )
    monkeypatch.setattr(
        "app.generate.answer.complete_chat",
        lambda *_args, **_kwargs: '{"answer":"有毒[9]","cited":[9]}',
    )
    result = answer_question("黄芪的性味与归经是什么？", conn, settings)
    assert result.refused is True
    assert result.answer == INSUFFICIENT
    assert result.citations == []


def test_llm_accepts_citation_that_matches_a_hit(conn, sample_dir, monkeypatch):
    ingest_path(conn, sample_dir)
    settings = Settings(
        database_path=str(conn.execute("PRAGMA database_list").fetchone()[2]),
        llm_mode="llm",
        llm_api_key="test-key",
    )
    monkeypatch.setattr(
        "app.generate.answer.complete_chat",
        lambda *_args, **_kwargs: '{"answer":"黄芪性味甘、微温。[1]","cited":[1]}',
    )
    result = answer_question("黄芪的性味与归经是什么？", conn, settings)
    assert result.refused is False
    assert result.mode == "llm"
    assert result.citations[0].chunk_id == result.hits[0].chunk_id
    assert "[1]" in result.answer


def test_llm_network_failure_refuses_without_inventing(conn, sample_dir, monkeypatch):
    ingest_path(conn, sample_dir)
    settings = Settings(
        database_path=str(conn.execute("PRAGMA database_list").fetchone()[2]),
        llm_mode="llm",
        llm_api_key="test-key",
    )

    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.generate.answer.complete_chat", boom)
    result = answer_question("什么是四气五味？", conn, settings)
    assert result.answer == INSUFFICIENT
    assert result.hits
    assert "寒、热、温、凉" not in result.answer
