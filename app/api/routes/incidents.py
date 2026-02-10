"""
Rotas de incidentes de saúde.

Sprint 55 - Epic 03
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.timezone import agora_utc
from app.services.supabase import supabase

router = APIRouter(tags=["incidents"])
logger = get_logger(__name__)


class RegistrarIncidenteRequest(BaseModel):
    """Request para registrar um incidente."""

    from_status: Optional[str] = None
    to_status: str
    from_score: Optional[int] = None
    to_score: int
    trigger_source: str = "api"
    details: Optional[dict] = None


class IncidenteResponse(BaseModel):
    """Response de um incidente."""

    id: str
    from_status: Optional[str]
    to_status: str
    from_score: Optional[int]
    to_score: int
    trigger_source: str
    details: dict
    started_at: str
    resolved_at: Optional[str]
    duration_seconds: Optional[int]


@router.post("/incidents")
async def registrar_incidente(request: RegistrarIncidenteRequest):
    """
    Registra uma mudança de status.

    Chamado pelo dashboard quando detecta transição.
    """
    try:
        # Se mudando para não-crítico, resolver incidente anterior
        if request.to_status != "critical" and request.from_status == "critical":
            await _resolver_incidente_ativo()

        # Inserir novo incidente
        result = (
            supabase.table("health_incidents")
            .insert(
                {
                    "from_status": request.from_status,
                    "to_status": request.to_status,
                    "from_score": request.from_score,
                    "to_score": request.to_score,
                    "trigger_source": request.trigger_source,
                    "details": request.details or {},
                    "started_at": agora_utc().isoformat(),
                }
            )
            .execute()
        )

        return {"success": True, "incident_id": result.data[0]["id"]}

    except Exception as e:
        logger.error(f"Erro ao registrar incidente: {e}")
        return {"success": False, "error": str(e)}


@router.get("/incidents")
async def listar_incidentes(
    limit: int = 20,
    status: Optional[str] = None,
    since: Optional[str] = None,
):
    """
    Lista histórico de incidentes.
    """
    try:
        query = supabase.table("health_incidents").select("*")

        if status:
            query = query.eq("to_status", status)

        if since:
            query = query.gte("started_at", since)

        result = query.order("started_at", desc=True).limit(limit).execute()

        return {
            "incidents": result.data,
            "total": len(result.data),
        }

    except Exception as e:
        logger.error(f"Erro ao listar incidentes: {e}")
        return {"incidents": [], "error": str(e)}


@router.get("/incidents/stats")
async def estatisticas_incidentes(dias: int = 30):
    """
    Retorna estatísticas de incidentes.
    """
    try:
        since = (agora_utc() - timedelta(days=dias)).isoformat()

        result = (
            supabase.table("health_incidents")
            .select("to_status, duration_seconds")
            .gte("started_at", since)
            .execute()
        )

        incidents = result.data or []

        # Calcular métricas
        total = len(incidents)
        critical_count = len([i for i in incidents if i["to_status"] == "critical"])
        degraded_count = len([i for i in incidents if i["to_status"] == "degraded"])

        # MTTR (Mean Time To Recover)
        resolved = [i for i in incidents if i.get("duration_seconds")]
        mttr = sum(i["duration_seconds"] for i in resolved) / len(resolved) if resolved else 0

        # Uptime aproximado (período total - tempo em crítico)
        total_seconds = dias * 24 * 60 * 60
        critical_time = sum(
            i.get("duration_seconds", 0) for i in incidents if i["to_status"] == "critical"
        )
        uptime_pct = ((total_seconds - critical_time) / total_seconds) * 100

        return {
            "period_days": dias,
            "total_incidents": total,
            "critical_incidents": critical_count,
            "degraded_incidents": degraded_count,
            "mttr_seconds": int(mttr),
            "uptime_percent": round(uptime_pct, 2),
        }

    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {e}")
        return {"error": str(e)}


async def _resolver_incidente_ativo():
    """Resolve o incidente crítico ativo (se houver)."""
    try:
        # Buscar incidente ativo
        result = (
            supabase.table("health_incidents")
            .select("id, started_at")
            .eq("to_status", "critical")
            .is_("resolved_at", "null")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )

        if not result.data:
            return

        incident = result.data[0]
        started = datetime.fromisoformat(incident["started_at"].replace("Z", "+00:00"))
        duration = int((agora_utc() - started).total_seconds())

        # Atualizar como resolvido
        (
            supabase.table("health_incidents")
            .update(
                {
                    "resolved_at": agora_utc().isoformat(),
                    "duration_seconds": duration,
                }
            )
            .eq("id", incident["id"])
            .execute()
        )

        logger.info(f"Incidente {incident['id']} resolvido após {duration}s")

    except Exception as e:
        logger.error(f"Erro ao resolver incidente: {e}")
