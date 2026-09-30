import os
from pathlib import Path

import pytest

os.environ["LANGSMITH_TRACING"] = "false"

from app.config import Settings
from app.retrieve.store import connect

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_dir() -> Path:
    return ROOT / "data" / "sample"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_path=str(tmp_path / "herbal.db"),
        uploads_dir=str(tmp_path / "uploads"),
        llm_mode="extractive",
        llm_api_key="",
        langsmith_tracing=False,
        langsmith_api_key="",
    )


@pytest.fixture
def conn(settings):
    connection = connect(settings.db_path)
    yield connection
    connection.close()
