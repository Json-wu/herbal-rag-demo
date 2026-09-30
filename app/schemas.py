"""HTTP 请求与响应结构。"""

from typing import Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    history: list[Turn] = Field(default_factory=list, max_length=8)


class Citation(BaseModel):
    marker: int
    chunk_id: str


class HitOut(BaseModel):
    chunk_id: str
    title: str
    source: str
    section: str
    filename: str
    text: str
    score: float


class RecallReport(BaseModel):
    labeled: bool
    applicable: bool
    k: int
    relevant: int
    recalled: int
    recalled_at_k: int
    recall: float | None = None
    recall_at_k: float | None = None
    found: list[str] = []
    missed: list[str] = []


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str | None = None
    mode: str
    citations: list[Citation]
    hits: list[HitOut]
    recall: RecallReport | None = None


class RecallItem(BaseModel):
    id: str
    question: str
    applicable: bool
    recall: float | None = None
    recall_at_k: float | None = None


class RecallSummary(BaseModel):
    k: int
    questions: int
    recall: float | None = None
    recall_at_k: float | None = None
    items: list[RecallItem]


class ExampleQuestion(BaseModel):
    id: str
    question: str
    kind: str


class DocumentOut(BaseModel):
    id: str
    title: str
    source: str
    filename: str
    imported_at: str
    chunks: int


class IngestResult(BaseModel):
    filename: str
    title: str
    source: str
    chunks: int
    skipped: bool
