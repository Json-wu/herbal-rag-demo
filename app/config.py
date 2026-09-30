"""运行配置。密钥只从环境变量或本地 .env 读取。"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    llm_mode: str = "extractive"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    retrieval_top_k: int = Field(default=5, ge=1, le=20)
    retrieval_min_score: float = Field(default=0.5, ge=0, le=1)
    database_path: str = "data/index/herbal.db"
    sample_dir: str = "data/sample"
    uploads_dir: str = "data/uploads"

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("llm_mode")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        mode = value.strip().lower()
        if mode not in {"extractive", "llm"}:
            raise ValueError("LLM_MODE 只能是 extractive 或 llm")
        return mode

    def path_of(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT / path
        return path

    @property
    def db_path(self) -> Path:
        return self.path_of(self.database_path)

    @property
    def sample_path(self) -> Path:
        return self.path_of(self.sample_dir)

    @property
    def uploads_path(self) -> Path:
        return self.path_of(self.uploads_dir)

    @property
    def llm_ready(self) -> bool:
        return self.llm_mode == "llm" and bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
