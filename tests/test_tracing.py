import os

from app.config import Settings
from app.generate.tracing import apply_tracing, llm_inputs, visible_inputs


def test_tracing_stays_off_without_a_key():
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="",
        langsmith_project="herbal-rag",
    )
    apply_tracing(settings)
    assert settings.langsmith_enabled is False
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_exports_project_without_the_model_key():
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key="lsv2-test",
        langsmith_endpoint="https://api.smith.langchain.com",
        langsmith_project="herbal-rag",
        llm_api_key="sk-secret",
        llm_model="gpt-4o-mini",
    )
    try:
        apply_tracing(settings)
        assert os.environ["LANGSMITH_TRACING"] == "true"
        assert os.environ["LANGSMITH_PROJECT"] == "herbal-rag"
        assert os.environ["LANGSMITH_ENDPOINT"] == "https://api.smith.langchain.com"
        assert "sk-secret" not in os.environ["LANGSMITH_API_KEY"]
    finally:
        os.environ["LANGSMITH_TRACING"] = "false"

    visible = visible_inputs({"question": "甘草", "conn": object(), "settings": settings})
    assert visible == {"question": "甘草"}
    recorded = llm_inputs({"settings": settings, "system": "规则", "user": "问题"})
    assert recorded["model"] == "gpt-4o-mini"
    assert "sk-secret" not in str(recorded)
