from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Agente Júlia"
    environment: str = "development"
    log_level: str = "DEBUG"
    nome_empresa: str = "Revoluna"

    @property
    def log_level_upper(self) -> str:
        """Retorna log level em maiusculo para logging module."""
        return self.log_level.upper()

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Anthropic
    anthropic_api_key: str
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_model_complex: str = "claude-sonnet-4-20250514"

    # Evolution API
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str
    evolution_instance: str = "Revoluna"

    # Chatwoot (opcional no MVP)
    chatwoot_url: str = "http://localhost:3000"
    chatwoot_api_key: str = ""
    chatwoot_account_id: int = 1
    chatwoot_inbox_id: int = 1

    # Slack (opcional)
    slack_webhook: str = ""

    # Rate Limiting
    max_msgs_por_hora: int = 20
    max_msgs_por_dia: int = 100
    intervalo_min_seg: int = 45
    intervalo_max_seg: int = 180
    horario_inicio: str = "08:00"
    horario_fim: str = "20:00"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
