"""
Servicos de health check.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

from app.services.health.constants import (
    CRITICAL_TABLES,
    CRITICAL_VIEWS,
    CRITICAL_JOBS,
    EXPECTED_SCHEMA_VERSION,
    JOB_SLA_SECONDS,
    REQUIRED_PROMPTS,
    APP_ENV,
    GIT_SHA,
    DEPLOYMENT_ID,
    RAILWAY_ENVIRONMENT,
    RUN_MODE,
    SUPABASE_PROJECT_REF,
)
from app.services.health.connectivity import (
    verificar_redis,
    verificar_supabase,
    verificar_evolution,
)
from app.services.health.schema import (
    gerar_schema_fingerprint,
    verificar_contrato_prompts,
)
from app.services.health.scoring import calcular_health_score
from app.services.health.alerts import coletar_alertas_sistema
from app.services.health.jobs_monitor import obter_status_jobs
from app.services.health.deep import executar_deep_health_check
from app.services.health.chips import obter_saude_chips
from app.services.health.fila import obter_saude_fila

__all__ = [
    # Constants
    "CRITICAL_TABLES",
    "CRITICAL_VIEWS",
    "CRITICAL_JOBS",
    "EXPECTED_SCHEMA_VERSION",
    "JOB_SLA_SECONDS",
    "REQUIRED_PROMPTS",
    "APP_ENV",
    "GIT_SHA",
    "DEPLOYMENT_ID",
    "RAILWAY_ENVIRONMENT",
    "RUN_MODE",
    "SUPABASE_PROJECT_REF",
    # Connectivity
    "verificar_redis",
    "verificar_supabase",
    "verificar_evolution",
    # Schema
    "gerar_schema_fingerprint",
    "verificar_contrato_prompts",
    # Scoring
    "calcular_health_score",
    # Alerts
    "coletar_alertas_sistema",
    # Jobs
    "obter_status_jobs",
    # Deep
    "executar_deep_health_check",
    # Chips
    "obter_saude_chips",
    # Fila
    "obter_saude_fila",
]
