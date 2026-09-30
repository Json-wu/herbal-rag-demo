"""把问答链路记到 LangSmith。密钥只来自环境变量，未配置时不发送。"""

import os

from app.config import Settings
from app.retrieve.search import Hit
from app.schemas import AskResponse

_HIDDEN_INPUTS = {"conn", "settings"}


def apply_tracing(settings: Settings) -> None:
    if not settings.langsmith_enabled:
        os.environ["LANGSMITH_TRACING"] = "false"
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_ENDPOINT"] = (
        settings.langsmith_endpoint.strip() or "https://api.smith.langchain.com"
    )
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.strip()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project.strip() or "herbal-rag"


def visible_inputs(inputs: dict) -> dict:
    return {key: value for key, value in inputs.items() if key not in _HIDDEN_INPUTS}


def documents_from_hits(hits: list[Hit]) -> list[dict]:
    return [
        {
            "page_content": hit.text,
            "type": "Document",
            "metadata": {
                "title": hit.title,
                "source": hit.source,
                "section": hit.section,
                "filename": hit.filename,
                "score": hit.score,
                "chunk_id": hit.chunk_id,
            },
        }
        for hit in hits
    ]


def response_output(response: AskResponse) -> dict:
    return response.model_dump()


def llm_inputs(inputs: dict) -> dict:
    settings: Settings = inputs["settings"]
    return {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": inputs.get("system", "")},
            {"role": "user", "content": inputs.get("user", "")},
        ],
    }


def llm_output(text: str) -> dict:
    return {"content": text}
