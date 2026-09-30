"""调用 OpenAI 兼容接口。失败时由回答模块退回拒答。"""

import httpx

from app.config import Settings


def complete_chat(settings: Settings, system: str, user: str) -> str:
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    with httpx.Client(timeout=30) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data["choices"][0]["message"]["content"])
