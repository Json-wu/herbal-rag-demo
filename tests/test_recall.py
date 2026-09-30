from app.ingest.service import ingest_path
from app.retrieve.recall import measure, summary


def test_labeled_questions_report_recall_at_five(conn, settings, sample_dir):
    ingest_path(conn, sample_dir)
    compare = measure(conn, "金银花和连翘在资料中有什么不同？", settings)
    assert compare.applicable is True
    assert compare.k == 5
    assert compare.relevant == 2
    assert compare.recall == 1
    assert compare.recall_at_k == 1
    assert compare.missed == []

    huangqi = measure(conn, "黄芪的性味与归经是什么？", settings)
    assert huangqi.recall_at_k == 1
    assert huangqi.found == ["黄芪 · 性味归经"]

    classic = measure(conn, "黄耆在本草纲目中的气味是什么？", settings)
    assert classic.recall_at_k == 1

    aspirin = measure(conn, "阿司匹林适用于哪些疾病？", settings)
    assert aspirin.labeled is True
    assert aspirin.applicable is False
    assert aspirin.recall is None

    custom = measure(conn, "今天天气怎么样？", settings)
    assert custom.labeled is False
    assert custom.recall is None


def test_summary_averages_only_applicable_questions(conn, settings, sample_dir):
    ingest_path(conn, sample_dir)
    report = summary(conn, settings)
    assert report.k == 5
    assert report.questions == 9
    assert report.recall_at_k == 1
    assert any(item.question.startswith("阿司匹林") and item.applicable is False for item in report.items)
