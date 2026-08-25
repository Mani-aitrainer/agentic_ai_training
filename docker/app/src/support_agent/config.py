"""Centralised configuration.

Every value here can be overridden by an environment variable, which is what
makes the *same image* runnable on a laptop, in `docker run`, and in Docker
Compose without a rebuild. Build once, configure per environment - that is the
whole point of the twelve-factor "config in the environment" rule.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- service identity -------------------------------------------------
    app_name: str = "support-triage-agent"
    environment: Literal["local", "dev", "staging", "prod"] = "local"
    log_level: str = "INFO"

    # --- http server ------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- llm --------------------------------------------------------------
    openai_api_key: str | None = None
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.0
    request_timeout: int = 30

    # --- optional shared state (the second service in docker-compose) -----
    redis_url: str | None = None

    # --- agent behaviour --------------------------------------------------
    max_tool_iterations: int = Field(
        default=4, description="Guard rail so the agent loop can never run forever."
    )

    @property
    def llm_enabled(self) -> bool:
        """No key -> we fall back to a deterministic stub so the container
        still starts and the health check still passes during a classroom demo."""
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
