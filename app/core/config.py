"""
Configurações da aplicação.
Carrega variáveis de ambiente.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configurações carregadas do .env"""

    # App
    APP_NAME: str = "Agente Júlia"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-3-5-haiku-20241022"
    LLM_MODEL_COMPLEX: str = "claude-sonnet-4-20250514"

    # Evolution API
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = ""
    EVOLUTION_INSTANCE: str = "Revoluna"

    # Chatwoot
    CHATWOOT_URL: str = "http://localhost:3000"
    CHATWOOT_API_KEY: str = ""
    CHATWOOT_ACCOUNT_ID: int = 1
    CHATWOOT_INBOX_ID: int = 1

    # Slack
    SLACK_WEBHOOK_URL: str = ""
    SLACK_CHANNEL: str = "#julia-gestao"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Julia API (para scheduler)
    JULIA_API_URL: str = "http://localhost:8000"

    # Rate Limiting
    MAX_MSGS_POR_HORA: int = 20
    MAX_MSGS_POR_DIA: int = 100
    HORARIO_INICIO: str = "08:00"
    HORARIO_FIM: str = "20:00"

    # Empresa
    NOME_EMPRESA: str = "Revoluna"

    # Limites de mensagem
    MAX_MENSAGEM_CHARS: int = 4000  # Máximo para processar normalmente
    MAX_MENSAGEM_CHARS_TRUNCAR: int = 10000  # Acima disso, truncar
    MAX_MENSAGEM_CHARS_REJEITAR: int = 50000  # Acima disso, pedir resumo

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignora variáveis extras do .env


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
