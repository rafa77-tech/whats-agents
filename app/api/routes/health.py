"""
Rotas de health check.

Sprint 58 - Epic 3: Thin router delegando para app/services/health/.

Endpoints (16):
- /health: Liveness basico
- /health/ready: Readiness (Redis + Supabase)
- /health/deep: Deep check para CI/CD
- /health/rate-limit: Rate limiter stats
- /health/circuits: Circuit breaker status
- /health/circuits/history: Circuit breaker history
- /health/whatsapp: Evolution API connection
- /health/grupos: Group processing status
- /health/schema: Schema fingerprint
- /health/jobs: Job execution status
- /health/telefones: Phone validation status
- /health/pilot: Pilot mode status
- /health/chips: Chip health
- /health/fila: Message queue health
- /health/alerts: Alert aggregation
- /health/score: Composite health score
"""

from fastapi import APIRouter, Response
import logging

from app.core.timezone import agora_utc
from app.services.redis import verificar_conexao_redis
from app.services.rate_limiter import obter_estatisticas
from app.services.circuit_breaker import obter_status_circuits
from app.services.whatsapp import evolution
from app.services.supabase import supabase

from app.services.health.constants import (
    APP_ENV,
    SUPABASE_PROJECT_REF,
    GIT_SHA,
    DEPLOYMENT_ID,
    RAILWAY_ENVIRONMENT,
    RUN_MODE,
    CRITICAL_TABLES,
    CRITICAL_VIEWS,
    EXPECTED_SCHEMA_VERSION,
    REQUIRED_PROMPTS,
    JOB_SLA_SECONDS,
    CRITICAL_JOBS,
)
from app.services.health.schema import gerar_schema_fingerprint, verificar_contrato_prompts
from app.services.health.scoring import calcular_health_score
from app.services.health.alerts import coletar_alertas_sistema
from app.services.health.jobs_monitor import obter_status_jobs
from app.services.health.deep import executar_deep_health_check
from app.services.health.connectivity import verificar_evolution
from app.services.health.chips import obter_saude_chips
from app.services.health.fila import obter_saude_fila

# Aliases mantidos para backward compat de mocks em testes
_generate_schema_fingerprint = gerar_schema_fingerprint
_check_prompt_contract = verificar_contrato_prompts

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Liveness & Readiness
# =============================================================================


@router.get("/health")
async def health_check():
    """Liveness check - 200 se app rodando."""
    return {
        "status": "healthy",
        "timestamp": agora_utc().isoformat(),
        "service": "julia-api",
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check - verifica Redis, Supabase, Evolution."""
    checks = {}
    all_ok = True

    try:
        redis_ok = await verificar_conexao_redis()
        checks["redis"] = "ok" if redis_ok else "error"
        if not redis_ok:
            all_ok = False
    except Exception as e:
        checks["redis"] = "error"
        checks["redis_error"] = str(e)
        all_ok = False

    try:
        supabase.table("clientes").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = "error"
        checks["database_error"] = str(e)
        all_ok = False

    try:
        evolution_status = await evolution.verificar_conexao()
        state = None
        if evolution_status:
            if "instance" in evolution_status:
                state = evolution_status.get("instance", {}).get("state")
            else:
                state = evolution_status.get("state")
        checks["evolution"] = "ok" if state == "open" else "degraded"
    except Exception:
        checks["evolution"] = "unknown"

    if all_ok:
        status = "ready"
    elif checks.get("database") == "ok":
        status = "degraded"
    else:
        status = "not_ready"

    return {"status": status, "checks": checks, "timestamp": agora_utc().isoformat()}


# =============================================================================
# Subsystem Health Checks
# =============================================================================


@router.get("/health/rate-limit")
async def rate_limit_stats():
    """Estatisticas de rate limiting."""
    return {"rate_limit": await obter_estatisticas(), "timestamp": agora_utc().isoformat()}


@router.get("/health/circuits")
async def circuit_status():
    """Status dos circuit breakers."""
    return {"circuits": obter_status_circuits(), "timestamp": agora_utc().isoformat()}


@router.get("/health/whatsapp")
async def whatsapp_status():
    """Status da conexao WhatsApp com Evolution API."""
    result = await verificar_evolution()
    result["timestamp"] = agora_utc().isoformat()
    return result


@router.get("/health/grupos")
async def grupos_worker_health():
    """Health check do worker de processamento de grupos WhatsApp."""
    try:
        from app.services.grupos.fila import obter_estatisticas_fila, obter_itens_travados

        fila_stats = await obter_estatisticas_fila()
        travados = await obter_itens_travados(horas=1)

        status = "healthy"
        if len(travados) > 100:
            status = "degraded"
        if len(travados) > 500:
            status = "unhealthy"

        return {
            "status": status,
            "fila": fila_stats,
            "travados": {
                "count": len(travados),
                "threshold_degraded": 100,
                "threshold_unhealthy": 500,
            },
            "timestamp": agora_utc().isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "timestamp": agora_utc().isoformat()}


# =============================================================================
# Deep Health Check
# =============================================================================


@router.get("/health/deep")
async def deep_health_check(response: Response):
    """Deep health check para CI/CD. Delegates to service layer."""
    result = await executar_deep_health_check()
    http_status = result.pop("http_status", 200)
    if http_status != 200:
        response.status_code = http_status
    result["timestamp"] = agora_utc().isoformat()
    return result


# =============================================================================
# Schema & Jobs
# =============================================================================


@router.get("/health/schema")
async def schema_info():
    """Informacoes do schema do banco."""
    try:
        result = (
            supabase.table("app_settings")
            .select("key, value")
            .in_("key", ["schema_version", "schema_applied_at"])
            .execute()
        )
        settings_map = {r["key"]: r["value"] for r in (result.data or [])}
        current_version = settings_map.get("schema_version")
        applied_at = settings_map.get("schema_applied_at")
        schema_fp = gerar_schema_fingerprint()

        return {
            "current_version": current_version,
            "expected_version": EXPECTED_SCHEMA_VERSION,
            "schema_up_to_date": current_version >= EXPECTED_SCHEMA_VERSION
            if current_version
            else False,
            "applied_at": applied_at,
            "fingerprint": schema_fp.get("fingerprint"),
            "critical_tables": CRITICAL_TABLES,
            "critical_views": CRITICAL_VIEWS,
            "timestamp": agora_utc().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": agora_utc().isoformat()}


@router.get("/health/jobs")
async def job_executions_status():
    """Status das execucoes dos jobs do scheduler."""
    result = await obter_status_jobs()
    result["timestamp"] = agora_utc().isoformat()
    return result


# =============================================================================
# Telefones, Pilot, Chips, Fila
# =============================================================================


@router.get("/health/telefones")
async def telefones_validation_status():
    """Estatisticas de validacao de telefones."""
    from app.services.validacao_telefone import obter_estatisticas_validacao

    stats = await obter_estatisticas_validacao()
    total = sum(stats.values()) if stats else 0
    validados = stats.get("validado", 0)
    invalidos = stats.get("invalido", 0)
    pendentes = stats.get("pendente", 0)

    status = "healthy"
    if pendentes > 10000:
        status = "degraded"
    if pendentes > 50000:
        status = "warning"

    return {
        "status": status,
        "stats": stats,
        "total": total,
        "taxa_validos_pct": round(validados / total * 100, 2) if total > 0 else 0,
        "taxa_invalidos_pct": round(invalidos / total * 100, 2) if total > 0 else 0,
        "backlog_pendentes": pendentes,
        "timestamp": agora_utc().isoformat(),
    }


@router.get("/health/pilot")
async def pilot_mode_status():
    """Status do modo piloto."""
    from app.workers.pilot_mode import get_pilot_status

    return {**get_pilot_status(), "timestamp": agora_utc().isoformat()}


@router.get("/health/chips")
async def chips_health_status():
    """Dashboard de saude dos chips. Delegates to service layer."""
    result = await obter_saude_chips()
    result["timestamp"] = agora_utc().isoformat()
    return result


@router.get("/health/fila")
async def fila_health_status():
    """Metricas da fila de mensagens. Delegates to service layer."""
    result = await obter_saude_fila()
    result["timestamp"] = agora_utc().isoformat()
    return result


# =============================================================================
# Alerts & Score
# =============================================================================


@router.get("/health/alerts")
async def system_alerts():
    """Alertas consolidados do sistema. Delegates to service layer."""
    result = await coletar_alertas_sistema()
    result["timestamp"] = agora_utc().isoformat()
    return result


@router.get("/health/score")
async def system_health_score():
    """Health score consolidado do sistema (0-100). Delegates to service layer."""
    result = await calcular_health_score()
    result["timestamp"] = agora_utc().isoformat()
    return result


# =============================================================================
# Circuit Breaker History
# =============================================================================


@router.get("/health/circuits/history")
async def circuit_breaker_history(circuit_name: str = None, horas: int = 24):
    """Historico de transicoes dos circuit breakers."""
    try:
        from app.services.circuit_breaker import obter_historico_transicoes

        transicoes = await obter_historico_transicoes(circuit_name, horas)
        by_circuit = {}
        for t in transicoes:
            name = t.get("circuit_name", "unknown")
            if name not in by_circuit:
                by_circuit[name] = []
            by_circuit[name].append(
                {
                    "from": t.get("from_state"),
                    "to": t.get("to_state"),
                    "reason": t.get("reason"),
                    "falhas": t.get("falhas_consecutivas"),
                    "at": t.get("created_at"),
                }
            )

        return {
            "circuit_filter": circuit_name,
            "period_hours": horas,
            "total_transitions": len(transicoes),
            "by_circuit": by_circuit,
            "transitions": transicoes[:50],
            "timestamp": agora_utc().isoformat(),
        }
    except Exception as e:
        logger.error(f"[health/circuits/history] Error: {e}")
        return {"error": str(e), "timestamp": agora_utc().isoformat()}
