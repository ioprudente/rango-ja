from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    max_agent_iterations: int = Field(default=6, ge=1, le=20)
    reference_datetime: str = "2026-10-10T21:00:00-03:00"

    orders_path: str = Field(
        default="data/pedidos.json",
        validation_alias=AliasChoices("ORDERS_PATH", "PEDIDOS_PATH"),
    )
    policies_path: str = Field(
        default="data/politicas.md",
        validation_alias=AliasChoices("POLICIES_PATH", "POLITICAS_PATH"),
    )

    max_refund_auto: float = 50.0
    claim_window_days: int = 7
    delay_threshold_minutes: int = 30
    delay_refund_percent: float = 0.20


@lru_cache
def get_settings() -> Settings:
    return Settings()