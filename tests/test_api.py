from fastapi.testclient import TestClient

from app.examples import EXAMPLES
from app.main import create_app
from app.texts import INSUFFICIENT, MEDICAL_BOUNDARY, SAMPLE_SOURCE


def test_health_examples_and_demo_path(settings):
    app = create_app(settings, auto_ingest=True)
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        body = health.json()
        assert body["status"] == "ok"
        assert body["llm_mode"] == "extractive"
        assert body["llm_ready"] is False
        assert body["documents"] == 6

        examples = client.get("/api/examples")
        assert [item["question"] for item in examples.json()] == [item.question for item in EXAMPLES]

        asked = client.post("/api/ask", json={"question": "金银花和连翘在资料中有什么不同？"})
        payload = asked.json()
        assert "金银花味甘，性寒" in payload["answer"]
        assert "连翘味苦，性微寒" in payload["answer"]
        assert {hit["title"] for hit in payload["hits"]} == {"金银花", "连翘"}
        for cite in payload["citations"]:
            assert payload["hits"][cite["marker"] - 1]["chunk_id"] == cite["chunk_id"]

        refused = client.post("/api/ask", json={"question": "阿司匹林适用于哪些疾病？"})
        assert refused.json()["answer"] == INSUFFICIENT

        blocked = client.post("/api/ask", json={"question": "我发烧咳嗽，麻黄每天该吃多少克？"})
        assert blocked.json()["answer"] == MEDICAL_BOUNDARY
        assert blocked.json()["citations"] == []

        docs = client.get("/api/documents").json()
        assert {item["filename"] for item in docs} == {
            "黄芪.md",
            "甘草.md",
            "四气五味.md",
            "金银花.md",
            "连翘.md",
            "麻黄.md",
        }
        assert all(item["source"] == SAMPLE_SOURCE for item in docs)


def test_upload_markdown(settings):
    app = create_app(settings, auto_ingest=False)
    content = "---\ntitle: 测试笔记\nsource: 单测来源\n---\n\n# 测试笔记\n\n白芷演示词写入正文。\n"
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            files={"file": ("测试笔记.md", content.encode("utf-8"), "text/markdown")},
        )
        assert response.status_code == 200
        assert response.json()["chunks"] == 1
        asked = client.post("/api/ask", json={"question": "测试笔记里的白芷演示词是什么？"})
        assert "白芷演示词" in asked.json()["answer"]

        rejected = client.post("/api/ingest", files={"file": ("笔记.pdf", b"%PDF", "application/pdf")})
        assert rejected.status_code == 400
