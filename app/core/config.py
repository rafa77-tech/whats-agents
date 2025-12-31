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

    # DEV Guardrails - Proteção contra envio acidental em ambiente de desenvolvimento
    # APP_ENV: "production" | "dev" (padronizado para auditoria)
    # OUTBOUND_ALLOWLIST: lista de números permitidos em DEV (separados por vírgula)
    # Exemplo: "5511999999999,5511888888888"
    # IMPORTANTE: Se APP_ENV != "production" e OUTBOUND_ALLOWLIST vazia → bloqueia TUDO
    APP_ENV: str = "dev"  # Sempre "dev" por padrão, PROD deve setar "production"
    OUTBOUND_ALLOWLIST: str = ""  # Vazio = fail-closed em DEV

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
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""

    # Voyage AI (embeddings - recomendado pela Anthropic)
    VOYAGE_API_KEY: str = ""
    VOYAGE_MODEL: str = "voyage-3.5-lite"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Julia API (para scheduler)
    JULIA_API_URL: str = "http://localhost:8000"

    # JWT para External Handoff (Sprint 20)
    JWT_SECRET_KEY: str = ""  # Obrigatório em produção
    APP_BASE_URL: str = "https://api.revoluna.com"  # URL base para links de confirmacao

    # CORS - origens permitidas (separadas por vírgula)
    # Em produção, definir explicitamente: "https://app.revoluna.com,https://admin.revoluna.com"
    CORS_ORIGINS: str = "*"  # "*" apenas para desenvolvimento

    @property
    def jwt_secret(self) -> str:
        """
        Retorna JWT secret.

        Em produção, JWT_SECRET_KEY é obrigatório.
        Em desenvolvimento, usa ANTHROPIC_API_KEY como fallback (não recomendado).
        """
        if self.ENVIRONMENT == "production" and not self.JWT_SECRET_KEY:
            raise ValueError(
                "JWT_SECRET_KEY é obrigatório em produção. "
                "Gere um secret seguro com: openssl rand -hex 32"
            )
        return self.JWT_SECRET_KEY or self.ANTHROPIC_API_KEY

    @property
    def outbound_allowlist_numbers(self) -> set[str]:
        """
        Retorna set de números permitidos para outbound em DEV.

        Números são normalizados (só dígitos).
        Set vazio significa que NENHUM outbound é permitido em DEV (fail-closed).
        """
        if not self.OUTBOUND_ALLOWLIST:
            return set()
        return {
            "".join(filter(str.isdigit, num.strip()))
            for num in self.OUTBOUND_ALLOWLIST.split(",")
            if num.strip()
        }

    @property
    def is_production(self) -> bool:
        """Retorna True se está em produção (APP_ENV == 'production')."""
        return self.APP_ENV.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """
        Retorna lista de origens CORS permitidas.

        Em produção, deve ser configurado explicitamente.
        """
        if self.CORS_ORIGINS == "*":
            if self.ENVIRONMENT == "production":
                # Log warning mas permite (para não quebrar deploy)
                import logging
                logging.warning(
                    "⚠️ CORS_ORIGINS='*' em produção. "
                    "Configure origens específicas para maior segurança."
                )
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

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


class GruposConfig:
    """
    Configurações do pipeline de grupos WhatsApp.

    Sprint 14 - Centralizando constantes.
    """

    # Heurística
    MIN_TAMANHO_MENSAGEM: int = 15
    MAX_TAMANHO_MENSAGEM: int = 2000
    THRESHOLD_HEURISTICA: float = 0.25
    THRESHOLD_HEURISTICA_ALTO: float = 0.8

    # Classificação LLM
    THRESHOLD_LLM: float = 0.7
    CACHE_TTL_CLASSIFICACAO: int = 86400  # 24 horas

    # Importação
    THRESHOLD_IMPORTAR: float = 0.90
    THRESHOLD_REVISAR: float = 0.70

    # Worker
    BATCH_SIZE: int = 50
    MAX_WORKERS: int = 5
    INTERVALO_CICLO_SEGUNDOS: int = 10

    # Alertas
    ALERTA_THRESHOLD_ERROS: int = 10
    ALERTA_THRESHOLD_CUSTO_USD: float = 1.0
    ALERTA_THRESHOLD_PENDENTES_HORAS: int = 4


class DatabaseConfig:
    """
    Configuracoes centralizadas de banco de dados e cache.

    Sprint 10 - S10.E1.4
    """

    # Cache TTLs (segundos)
    CACHE_TTL_CONTEXTO: int = 120  # 2 minutos - contexto de conversa
    CACHE_TTL_MEDICO: int = 300  # 5 minutos - dados de medico
    CACHE_TTL_VAGAS: int = 60  # 1 minuto - vagas mudam frequentemente
    CACHE_TTL_ABERTURA: int = 86400 * 30  # 30 dias - aberturas usadas
    CACHE_TTL_HOSPITAIS: int = 3600  # 1 hora - hospitais raramente mudam
    CACHE_TTL_PROMPTS: int = 300  # 5 minutos - prompts do sistema
    CACHE_TTL_DOCS: int = 300  # 5 minutos - cache Google Docs

    # Session timeouts
    SESSION_TIMEOUT_MINUTES: int = 30  # Sessao Slack

    # Limites de query
    MAX_RESULTS_DEFAULT: int = 100
    MAX_RESULTS_ABSOLUTE: int = 1000

    # Intervalos de timing (rate limiting)
    INTERVALO_MIN_SEGUNDOS: int = 45
    INTERVALO_MAX_SEGUNDOS: int = 180

    # Horario comercial
    HORA_INICIO: int = 8   # 08:00
    HORA_FIM: int = 20     # 20:00

    # Retry
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: float = 0.5

    # Embeddings
    EMBEDDING_DIMENSION: int = 1024


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
