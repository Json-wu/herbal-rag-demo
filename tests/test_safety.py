import pytest

from app.generate.answer import answer_question
from app.generate.safety import classify
from app.ingest.service import ingest_path
from app.texts import MEDICAL_BOUNDARY

KNOWLEDGE = [
    "黄芪的性味与归经是什么？",
    "资料中如何描述甘草？",
    "什么是四气五味？",
    "金银花和连翘在资料中有什么不同？",
    "资料里对麻黄有哪些使用注意？",
    "阿司匹林适用于哪些疾病？",
]


@pytest.mark.parametrize("question", KNOWLEDGE)
def test_knowledge_questions_are_not_medical_advice(question):
    assert classify(question) is None


@pytest.mark.parametrize(
    ("question", "kind"),
    [
        ("我发烧咳嗽，麻黄每天该吃多少克？", "dosage"),
        ("帮我诊断是不是得了感冒", "diagnosis"),
        ("请给我开一个治疗咳嗽的处方", "prescription"),
        ("突然胸痛，呼吸困难怎么办", "emergency"),
        ("我咳嗽好几天了该怎么办", "symptom"),
    ],
)
def test_safety_kinds(question, kind):
    match = classify(question)
    assert match is not None
    assert match.kind == kind


def test_personal_dosing_question_is_not_stored_or_answered(conn, sample_dir, settings):
    ingest_path(conn, sample_dir)
    question = "我发烧咳嗽，麻黄每天该吃多少克？"
    result = answer_question(question, conn, settings)
    assert result.refusal_reason == "medical_boundary"
    assert result.answer == MEDICAL_BOUNDARY
    assert result.citations == []
    assert "克" not in result.answer
    assert any(hit.title == "麻黄" for hit in result.hits)
    blob = settings.db_path.read_bytes().decode("utf-8", "ignore")
    assert question not in blob
