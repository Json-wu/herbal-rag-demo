"""编排安全判断、检索、摘录或模型回答。"""

import json
import re

from langsmith import traceable

from app.config import Settings
from app.generate.citations import validate_citations
from app.generate.llm import complete_chat
from app.generate.prompt import build_prompt
from app.generate.safety import classify
from app.generate.tracing import documents_from_hits, response_output, visible_inputs
from app.retrieve.context import retrieval_query, safety_text
from app.retrieve.recall import measure
from app.retrieve.search import Hit, search
from app.schemas import AskResponse, Citation, HitOut
from app.texts import EXTRACTIVE_PREFIX, INSUFFICIENT, MEDICAL_BOUNDARY

_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


@traceable(
    name="herbal_rag",
    run_type="chain",
    process_inputs=visible_inputs,
    process_outputs=response_output,
)
def answer_question(
    question: str,
    conn,
    settings: Settings,
    history: list[tuple[str, str]] | None = None,
) -> AskResponse:
    text = (question or "").strip()
    mode = "llm" if settings.llm_ready else "extractive"
    if not text:
        return _insufficient(mode, [])
    prior = history or []
    safety = classify(safety_text(text, prior))
    hits = _retrieve(retrieval_query(text, prior), conn, settings)
    report = measure(conn, text, settings)

    def finish(response: AskResponse) -> AskResponse:
        response.recall = report
        return response

    if safety is not None:
        return finish(
            AskResponse(
                answer=MEDICAL_BOUNDARY,
                refused=True,
                refusal_reason="medical_boundary",
                mode=mode,
                citations=[],
                hits=[_hit_out(hit) for hit in hits],
            )
        )
    if not hits:
        return finish(_insufficient(mode, []))
    if settings.llm_ready:
        return finish(_from_model(text, hits, settings, prior))
    return finish(_extractive(hits))


@traceable(
    name="retrieve",
    run_type="retriever",
    process_inputs=visible_inputs,
    process_outputs=documents_from_hits,
)
def _retrieve(question: str, conn, settings: Settings) -> list[Hit]:
    return search(conn, question, settings.retrieval_top_k, settings.retrieval_min_score)


def _extractive(hits: list[Hit]) -> AskResponse:
    lines = [EXTRACTIVE_PREFIX]
    for index, hit in enumerate(hits, start=1):
        snippet = " ".join(hit.text.split())
        if len(snippet) > 220:
            snippet = snippet[:220] + "…"
        lines.append(f"{snippet}[{index}]")
    answer = "\n".join(lines)
    citations = [Citation(marker=index, chunk_id=hit.chunk_id) for index, hit in enumerate(hits, start=1)]
    return AskResponse(
        answer=answer,
        refused=False,
        refusal_reason=None,
        mode="extractive",
        citations=citations,
        hits=[_hit_out(hit) for hit in hits],
    )


def _from_model(
    question: str,
    hits: list[Hit],
    settings: Settings,
    history: list[tuple[str, str]] | None = None,
) -> AskResponse:
    system, user = build_prompt(question, hits, history)
    try:
        raw = complete_chat(settings, system, user)
    except Exception:
        return _insufficient("llm", hits)
    return _parse_model(raw, hits)


def _parse_model(raw: str, hits: list[Hit]) -> AskResponse:
    payload = _load_json(raw)
    if payload is None:
        return _insufficient("llm", hits)
    answer = str(payload.get("answer") or "").strip()
    cited = payload.get("cited")
    if not isinstance(cited, list) or answer.startswith(INSUFFICIENT):
        return _insufficient("llm", hits)
    allowed = {item for item in cited if isinstance(item, int)}
    cleaned, citations, refused = validate_citations(answer, hits)
    if refused:
        return _insufficient("llm", hits)
    citations = [item for item in citations if item.marker in allowed]
    if not citations:
        return _insufficient("llm", hits)
    kept = {item.marker for item in citations}
    cleaned = re.sub(r"\[(\d+)\]", lambda match: match.group(0) if int(match.group(1)) in kept else "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return AskResponse(
        answer=cleaned,
        refused=False,
        refusal_reason=None,
        mode="llm",
        citations=citations,
        hits=[_hit_out(hit) for hit in hits],
    )


def _load_json(raw: str) -> dict | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = _JSON_OBJECT.search(text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(data, dict) or "answer" not in data:
        return None
    return data


def _insufficient(mode: str, hits: list[Hit]) -> AskResponse:
    return AskResponse(
        answer=INSUFFICIENT,
        refused=True,
        refusal_reason="insufficient_evidence",
        mode=mode,
        citations=[],
        hits=[_hit_out(hit) for hit in hits],
    )


def _hit_out(hit: Hit) -> HitOut:
    return HitOut(
        chunk_id=hit.chunk_id,
        title=hit.title,
        source=hit.source,
        section=hit.section,
        filename=hit.filename,
        text=hit.text,
        score=hit.score,
    )
