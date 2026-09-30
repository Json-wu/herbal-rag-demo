from app.generate.citations import validate_citations
from app.retrieve.search import Hit
from app.texts import INSUFFICIENT


def _hit(chunk_id: str = "doc:0000") -> Hit:
    return Hit(
        chunk_id=chunk_id,
        title="黄芪",
        source="测试来源",
        section="性味归经",
        filename="黄芪.md",
        text="黄芪性味甘、微温。",
        score=1,
    )


def test_valid_marker_maps_to_returned_chunk():
    answer, citations, refused = validate_citations("黄芪性味甘、微温。[1]", [_hit("doc:0000")])
    assert refused is False
    assert answer == "黄芪性味甘、微温。[1]"
    assert citations[0].marker == 1
    assert citations[0].chunk_id == "doc:0000"


def test_unknown_marker_is_removed_and_refuses_when_none_remain():
    answer, citations, refused = validate_citations("参见[9]。", [_hit()])
    assert refused is True
    assert citations == []
    assert answer == INSUFFICIENT


def test_mixed_markers_keep_only_real_hits():
    hits = [_hit("a:0000"), _hit("b:0001")]
    answer, citations, refused = validate_citations("第一段[1]，伪造[8]，第二段[2]。", hits)
    assert refused is False
    assert "[1]" in answer and "[2]" in answer and "[8]" not in answer
    assert [item.chunk_id for item in citations] == ["a:0000", "b:0001"]
