"""
Constantes de health check.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import os


# Hard guards de ambiente - CRITICO para evitar staging<->prod mix
APP_ENV = os.getenv("APP_ENV", "development")
SUPABASE_PROJECT_REF = os.getenv("SUPABASE_PROJECT_REF", "")


# Versioning info (injected by CI/CD build or Railway runtime)
# Railway fornece RAILWAY_GIT_COMMIT_SHA automaticamente em runtime
# Nota: Dockerfile seta GIT_SHA="unknown" como default, entao precisamos ignorar esse valor
def _get_version_var(explicit_name: str, railway_name: str) -> str:
    """Busca variavel de versao, ignorando 'unknown' do Dockerfile."""
    explicit = os.getenv(explicit_name)
    railway = os.getenv(railway_name)
    # Ignora se for "unknown" (default do Dockerfile)
    if explicit and explicit != "unknown":
        return explicit
    if railway:
        return railway
    return "unknown"


GIT_SHA = _get_version_var("GIT_SHA", "RAILWAY_GIT_COMMIT_SHA")
DEPLOYMENT_ID = _get_version_var("BUILD_TIME", "RAILWAY_DEPLOYMENT_ID")
RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT", "unknown")
RUN_MODE = os.getenv("RUN_MODE", "unknown")

# Views criticas que DEVEM existir para o app funcionar
CRITICAL_VIEWS = [
    "campaign_sends",
    "campaign_metrics",
]

# Tabelas criticas que DEVEM existir
CRITICAL_TABLES = [
    "clientes",
    "conversations",
    "fila_mensagens",
    "doctor_state",
    "intent_log",
    "touch_reconciliation_log",
    "app_settings",  # Nova tabela critica para markers
]

# Ultima migration conhecida (atualizar quando adicionar migrations criticas)
EXPECTED_SCHEMA_VERSION = "20251231211500"  # create_get_table_columns_for_fingerprint

# Contrato de prompts - sentinelas obrigatorias para deploy seguro
REQUIRED_PROMPTS = {
    "julia_base": {
        "min_len": 2000,
        "required_sentinels": [
            "[INVARIANT:INBOUND_ALWAYS_REPLY]",
            "[INVARIANT:OPTOUT_ABSOLUTE]",
            "[INVARIANT:KILL_SWITCHES_PRIORITY]",
            "[INVARIANT:NO_CONFIRM_WITHOUT_RESERVATION]",
            "[INVARIANT:NO_IDENTITY_DEBATE]",
            "[CAPABILITY:HANDOFF]",  # Promovido para BLOQUEADOR - handoff eh critico
            "[FALLBACK:DIRETRIZES_EMPTY_OK]",
        ],
        "warning_sentinels": [
            "[INVARIANT:OUTBOUND_QUIET_HOURS]",
            "[INVARIANT:NO_METACOMMUNICATION]",
        ],
    },
    "julia_primeira_msg": {
        "min_len": 100,
        "required_sentinels": [],
        "warning_sentinels": [],
    },
    "julia_tools": {
        "min_len": 300,
        "required_sentinels": [],
        "warning_sentinels": [],
    },
}

# SLA por job: max_age_seconds baseado na frequencia do cron
# Se job nao roda ha mais tempo que o SLA, eh considerado "stale" (critico)
JOB_SLA_SECONDS = {
    # Jobs de 1 minuto: SLA = 3 minutos (3x a frequencia)
    "processar_fila_mensagens": 180,
    "processar_campanhas_agendadas": 180,
    # Jobs de 5 minutos: SLA = 15 minutos
    "verificar_whatsapp": 900,
    "processar_grupos": 900,
    # Jobs de 10 minutos: SLA = 30 minutos
    "processar_handoffs": 1800,
    # Jobs de 15 minutos: SLA = 45 minutos
    "verificar_alertas": 2700,
    "verificar_alertas_grupos": 2700,
    # Jobs horarios: SLA = 2 horas
    "sincronizar_briefing": 7200,
    "processar_confirmacao_plantao": 7200,
    # Jobs diarios: SLA = 25 horas (margem para variacao)
    "processar_followups": 90000,
    "processar_pausas_expiradas": 90000,
    "avaliar_conversas_pendentes": 90000,
    "report_manha": 90000,
    "report_fim_dia": 90000,
    "sincronizar_templates": 90000,
    "limpar_grupos_finalizados": 90000,
    "consolidar_metricas_grupos": 90000,
    "doctor_state_manutencao_diaria": 90000,
    # Jobs semanais: SLA = 8 dias
    "report_semanal": 691200,
    "atualizar_prompt_feedback": 691200,
    "doctor_state_manutencao_semanal": 691200,
    # Jobs seg-sex: SLA = 3 dias (pode pular fim de semana)
    "processar_retomadas": 259200,
}

# Jobs criticos que DEVEM estar rodando para o sistema funcionar
CRITICAL_JOBS = [
    "processar_fila_mensagens",
    "processar_campanhas_agendadas",
    "verificar_whatsapp",
    "processar_grupos",
]
