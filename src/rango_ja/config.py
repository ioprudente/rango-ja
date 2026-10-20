from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: str = "ollama"
    llm_api_key: str = "nao_precisa"
    llm_model: str = "llama3.2:3b"
    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 2
    ollama_url: str = "http://localhost:11434"

    max_agent_iterations: int = Field(default=6, ge=1, le=20)
    reference_datetime: str = "2026-10-10T21:00:00-03:00"

    pedidos_path: str = "data/pedidos.json"
    politicas_path: str = "data/politicas.md"
    state_path: str = "data/pedidos_state.json"
    actions_path: str = "data/actions.json"
    escalations_path: str = "data/escalations.json"

    max_refund_auto: float = 50.0
    claim_window_days: int = 7
    delay_threshold_minutes: int = 30
    delay_refund_percent: float = 0.20

@lru_cache
def get_settings() -> Settings:
    return Settings()
