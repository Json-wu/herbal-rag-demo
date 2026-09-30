"""HTTP 请求与响应结构。"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


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


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str | None = None
    mode: str
    citations: list[Citation]
    hits: list[HitOut]


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
