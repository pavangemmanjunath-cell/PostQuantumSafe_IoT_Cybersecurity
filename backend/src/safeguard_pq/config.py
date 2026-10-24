"""Runtime configuration loaded from environment variables or a `.env` file.

Every setting has a safe default so the backend runs fully offline with no
LLM and no outbound network access.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["none", "openai_compatible", "anthropic"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Optional LLM used only for the narrative report. "none" = deterministic template.
    llm_provider: LLMProvider = "none"
    llm_model: str | None = None
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_timeout_s: float = 30.0
    llm_max_tokens: int = 1200

    # Reproducibility: default seed for the QIRO simulated-annealing optimizer.
    qiro_default_seed: int = 2026

    # Outbound "live" tools (e.g. openFDA). Disabled by default.
    online_tools_enabled: bool = False

    max_upload_mb: int = 25
    max_upload_rows: int = 5000
    assessment_store_size: int = 200

    # Optional directory of user-downloaded CICIoMT-style CSV files for the replay data source.
    replay_data_dir: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider != "none" and bool(self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
