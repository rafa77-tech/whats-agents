"""
Monitoramento de jobs do scheduler.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import logging
from datetime import datetime, timedelta

from app.core.timezone import agora_utc
from app.services.supabase import supabase
from app.services.health.constants import JOB_SLA_SECONDS, CRITICAL_JOBS

logger = logging.getLogger(__name__)


async def obter_status_jobs() -> dict:
    """
    Retorna status das execucoes dos jobs do scheduler.

    Sprint 18 - GAP 1: Observabilidade de jobs.

    Mostra:
    - Ultima execucao de cada job
    - Status (success/error/timeout)
    - Duracao media
    - Erros nas ultimas 24h
    - Stale jobs (nao rodaram dentro do SLA)

    Returns:
        dict com status, jobs, alerts, sla_config, period e total_executions.
    """
    try:
        now = agora_utc()

        # Ultimas 24h
        since = (now - timedelta(hours=24)).isoformat()

        # Buscar todas execucoes das ultimas 24h
        result = (
            supabase.table("job_executions")
            .select(
                "job_name, started_at, finished_at, status, duration_ms, items_processed, error"
            )
            .gte("started_at", since)
            .order("started_at", desc=True)
            .execute()
        )

        executions = result.data or []

        # Agrupar por job
        jobs_summary = {}
        for ex in executions:
            name = ex["job_name"]
            if name not in jobs_summary:
                jobs_summary[name] = {
                    "last_run": None,
                    "last_status": None,
                    "runs_24h": 0,
                    "success_24h": 0,
                    "errors_24h": 0,
                    "timeouts_24h": 0,
                    "avg_duration_ms": 0,
                    "total_items_processed": 0,
                    "last_error": None,
                    "durations": [],
                    "sla_seconds": JOB_SLA_SECONDS.get(name),
                    "is_stale": False,
                    "seconds_since_last_run": None,
                }

            summary = jobs_summary[name]
            summary["runs_24h"] += 1

            # Primeira execucao encontrada = mais recente
            if summary["last_run"] is None:
                summary["last_run"] = ex["started_at"]
                summary["last_status"] = ex["status"]

                # Calcular idade da ultima execucao
                try:
                    last_run_dt = datetime.fromisoformat(
                        ex["started_at"].replace("+00:00", "").replace("Z", "")
                    )
                    age_seconds = (now - last_run_dt).total_seconds()
                    summary["seconds_since_last_run"] = int(age_seconds)

                    # Verificar se esta stale
                    sla = JOB_SLA_SECONDS.get(name)
                    if sla and age_seconds > sla:
                        summary["is_stale"] = True
                except Exception:
                    pass

            # Contadores por status
            if ex["status"] == "success":
                summary["success_24h"] += 1
            elif ex["status"] == "error":
                summary["errors_24h"] += 1
                if summary["last_error"] is None:
                    summary["last_error"] = ex.get("error")
            elif ex["status"] == "timeout":
                summary["timeouts_24h"] += 1

            # Duracao
            if ex.get("duration_ms"):
                summary["durations"].append(ex["duration_ms"])

            # Items processados
            if ex.get("items_processed"):
                summary["total_items_processed"] += ex["items_processed"]

        # Calcular medias e limpar
        for name, summary in jobs_summary.items():
            if summary["durations"]:
                summary["avg_duration_ms"] = int(
                    sum(summary["durations"]) / len(summary["durations"])
                )
            del summary["durations"]

        # Coletar alertas
        jobs_with_errors = [n for n, s in jobs_summary.items() if s["errors_24h"] > 0]
        jobs_with_timeouts = [n for n, s in jobs_summary.items() if s["timeouts_24h"] > 0]
        stale_jobs = [n for n, s in jobs_summary.items() if s["is_stale"]]

        # Jobs criticos que nao aparecem (nunca rodaram ou nao rodaram nas ultimas 24h)
        missing_critical = [j for j in CRITICAL_JOBS if j not in jobs_summary]

        # Jobs criticos que estao stale
        critical_stale = [j for j in stale_jobs if j in CRITICAL_JOBS]

        # Determinar status geral
        status = "healthy"

        if jobs_with_errors or jobs_with_timeouts:
            status = "degraded"

        # CRITICAL: scheduler pode estar morto
        if critical_stale or missing_critical:
            status = "critical"

        return {
            "status": status,
            "jobs": jobs_summary,
            "alerts": {
                "jobs_with_errors": jobs_with_errors,
                "jobs_with_timeouts": jobs_with_timeouts,
                "stale_jobs": stale_jobs,
                "critical_stale": critical_stale,
                "missing_critical": missing_critical,
            },
            "sla_config": {
                "critical_jobs": CRITICAL_JOBS,
                "sla_definitions": JOB_SLA_SECONDS,
            },
            "period": "24h",
            "total_executions": len(executions),
        }

    except Exception as e:
        logger.error(f"[health/jobs] Error: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
