"""按标注原文计算召回率和 Recall@K。"""

from app.config import Settings
from app.examples import EXAMPLES
from app.retrieve.labels import GOLD, GoldPassage
from app.retrieve.search import Hit, search
from app.schemas import RecallItem, RecallReport, RecallSummary

_POOL = 40


def measure(conn, question: str, settings: Settings) -> RecallReport:
    k = settings.retrieval_top_k
    gold = GOLD.get(question.strip())
    if gold is None:
        return RecallReport(labeled=False, applicable=False, k=k, relevant=0, recalled=0, recalled_at_k=0)
    if not gold:
        return RecallReport(labeled=True, applicable=False, k=k, relevant=0, recalled=0, recalled_at_k=0)
    pool = search(conn, question, top_k=_POOL, min_score=settings.retrieval_min_score)
    return _score(pool, gold, k)


def summary(conn, settings: Settings) -> RecallSummary:
    items: list[RecallItem] = []
    recalls: list[float] = []
    at_k: list[float] = []
    for example in EXAMPLES:
        report = measure(conn, example.question, settings)
        if report.applicable and report.recall is not None and report.recall_at_k is not None:
            recalls.append(report.recall)
            at_k.append(report.recall_at_k)
        items.append(
            RecallItem(
                id=example.id,
                question=example.question,
                recall=report.recall,
                recall_at_k=report.recall_at_k,
                applicable=report.applicable,
            )
        )
    count = len(recalls)
    return RecallSummary(
        k=settings.retrieval_top_k,
        questions=count,
        recall=sum(recalls) / count if count else None,
        recall_at_k=sum(at_k) / count if count else None,
        items=items,
    )


def _score(pool: list[Hit], gold: tuple[GoldPassage, ...], k: int) -> RecallReport:
    filenames = {hit.filename for hit in pool}
    top_filenames = {hit.filename for hit in pool[:k]}
    found = [item for item in gold if item.filename in filenames]
    found_at_k = [item for item in gold if item.filename in top_filenames]
    relevant = len(gold)
    return RecallReport(
        labeled=True,
        applicable=True,
        k=k,
        relevant=relevant,
        recalled=len(found),
        recalled_at_k=len(found_at_k),
        recall=len(found) / relevant,
        recall_at_k=len(found_at_k) / relevant,
        found=[item.label for item in found_at_k],
        missed=[item.label for item in gold if item.filename not in top_filenames],
    )
