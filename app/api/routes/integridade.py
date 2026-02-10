"""
Endpoints de integridade de dados e KPIs operacionais.

Sprint 18 - E10, E11, E12: Data Integrity
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional
from pydantic import BaseModel
import logging

from app.services.business_events.audit import (
    run_full_audit,
    get_invariant_violations,
)
from app.services.business_events.reconciliation import (
    reconciliation_job,
    listar_anomalias,
    listar_anomalias_recorrentes,
    resolver_anomalia,
)
from app.services.business_events.kpis import (
    get_conversion_rates,
    get_time_to_fill_breakdown,
    get_health_score,
    get_kpis_summary,
)

router = APIRouter(prefix="/integridade", tags=["Data Integrity"])
logger = logging.getLogger(__name__)


# =============================================================================
# E10: Auditoria de Cobertura
# =============================================================================


@router.get("/auditoria")
async def executar_auditoria(
    hours: int = Query(24, ge=1, le=168, description="Janela de tempo em horas"),
):
    """
    Executa auditoria completa de cobertura de eventos.

    Verifica:
    - Pipeline inbound: mensagens recebidas geraram eventos
    - Agente outbound: mensagens enviadas geraram eventos
    - Transicoes de status: mudancas no DB geraram eventos

    Args:
        hours: Janela de tempo (default 24h, max 7 dias)

    Returns:
        Resultado da auditoria com status por fonte
    """
    try:
        result = await run_full_audit(hours=hours)
        return result.to_dict()
    except Exception as e:
        logger.error(f"Erro na auditoria: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/violacoes")
async def listar_violacoes(
    days: int = Query(7, ge=1, le=30, description="Janela de tempo em dias"),
):
    """
    Lista violacoes de invariantes do funil.

    Invariantes verificadas:
    - Toda vaga realizada tem cliente_id
    - Toda reserva tem offer_made antes
    - etc.

    Args:
        days: Janela de tempo (default 7 dias)

    Returns:
        Lista de violacoes agrupadas por tipo
    """
    try:
        violations = await get_invariant_violations(days=days)

        # Agrupar por tipo
        by_type: dict = {}
        for v in violations:
            if v.violation_type not in by_type:
                by_type[v.violation_type] = []
            by_type[v.violation_type].append(
                {
                    "event_id": v.event_id,
                    "vaga_id": v.vaga_id,
                    "cliente_id": v.cliente_id,
                    "invariant": v.invariant_name,
                    "details": v.details,
                }
            )

        return {
            "period_days": days,
            "total": len(violations),
            "by_type": by_type,
        }
    except Exception as e:
        logger.error(f"Erro ao listar violacoes: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# E11: Reconciliacao e Anomalias
# =============================================================================


@router.post("/reconciliacao")
async def executar_reconciliacao():
    """
    Executa reconciliacao bidirecional DB vs Eventos.

    Verifica:
    - DB -> Eventos: entidades no DB tem eventos correspondentes
    - Eventos -> DB: eventos tem reflexo correto no DB

    Anomalias detectadas sao persistidas com deduplicacao.
    """
    try:
        result = await reconciliation_job()
        return result
    except Exception as e:
        logger.error(f"Erro na reconciliacao: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/anomalias")
async def listar_anomalias_endpoint(
    days: int = Query(7, ge=1, le=30, description="Janela de tempo em dias"),
    resolved: Optional[bool] = Query(None, description="Filtrar por resolvidas"),
    anomaly_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    entity_type: Optional[str] = Query(None, description="Filtrar por entidade"),
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
):
    """
    Lista anomalias de dados detectadas.

    Args:
        days: Janela de tempo (default 7 dias)
        resolved: Filtrar por status de resolucao
        anomaly_type: Filtrar por tipo de anomalia
        entity_type: Filtrar por tipo de entidade
        severity: Filtrar por severidade (warning, critical)

    Returns:
        Summary e lista de anomalias
    """
    try:
        result = await listar_anomalias(
            days=days,
            resolved=resolved,
            anomaly_type=anomaly_type,
            entity_type=entity_type,
            severity=severity,
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao listar anomalias: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/anomalias/recorrentes")
async def listar_recorrentes(
    min_count: int = Query(3, ge=2, le=100, description="Contagem minima"),
):
    """
    Lista anomalias recorrentes (detectadas multiplas vezes).

    Util para identificar problemas sistematicos.

    Args:
        min_count: Contagem minima de ocorrencias (default 3)
    """
    try:
        result = await listar_anomalias_recorrentes(min_count=min_count)
        return result
    except Exception as e:
        logger.error(f"Erro ao listar recorrentes: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


class ResolverAnomaliaRequest(BaseModel):
    resolution_notes: str
    resolved_by: str = "api"


@router.post("/anomalias/{anomaly_id}/resolver")
async def resolver_anomalia_endpoint(
    anomaly_id: str,
    request: ResolverAnomaliaRequest,
):
    """
    Marca uma anomalia como resolvida.

    Args:
        anomaly_id: UUID da anomalia
        resolution_notes: Notas sobre a resolucao
        resolved_by: Quem resolveu
    """
    try:
        result = await resolver_anomalia(
            anomaly_id=anomaly_id,
            resolution_notes=request.resolution_notes,
            resolved_by=request.resolved_by,
        )
        return result
    except Exception as e:
        logger.error(f"Erro ao resolver anomalia {anomaly_id}: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# E12: KPIs Operacionais
# =============================================================================


@router.get("/kpis")
async def obter_kpis_summary():
    """
    Retorna resumo dos 3 KPIs principais.

    KPIs:
    - Conversion Rate: offer_made -> offer_accepted
    - Time-to-Fill: Tempos em cada etapa (breakdown)
    - Health Score: Pressao, friccao, qualidade, spam

    Usado como dashboard executivo.
    """
    try:
        result = await get_kpis_summary()
        return result
    except Exception as e:
        logger.error(f"Erro ao obter KPIs: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/kpis/conversion")
async def obter_conversion_rates(
    hours: int = Query(168, ge=1, le=720, description="Janela de tempo em horas"),
    hospital_id: Optional[str] = Query(None, description="Filtrar por hospital"),
):
    """
    Retorna taxas de conversao.

    Segmentado por:
    - Global
    - Por hospital
    - Por especialidade

    Args:
        hours: Janela de tempo (default 168h = 7 dias)
        hospital_id: Filtrar por hospital especifico
    """
    try:
        rates = await get_conversion_rates(hours=hours, hospital_id=hospital_id)
        return {
            "period_hours": hours,
            "hospital_filter": hospital_id,
            "rates": [
                {
                    "segment_type": r.segment_type,
                    "segment_value": r.segment_value,
                    "offers_made": r.offers_made,
                    "offers_accepted": r.offers_accepted,
                    "conversion_rate": r.conversion_rate,
                    "status": r.status,
                }
                for r in rates
            ],
        }
    except Exception as e:
        logger.error(f"Erro ao obter conversion rates: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/kpis/time-to-fill")
async def obter_time_to_fill(
    days: int = Query(30, ge=1, le=90, description="Janela de tempo em dias"),
    hospital_id: Optional[str] = Query(None, description="Filtrar por hospital"),
):
    """
    Retorna breakdown de tempos do funil.

    Metricas:
    - Time-to-Reserve: Anunciada -> Reservada (performance Julia)
    - Time-to-Confirm: Pendente -> Realizada (performance operacional)
    - Time-to-Fill: Anunciada -> Realizada (ROI completo)

    Args:
        days: Janela de tempo (default 30 dias)
        hospital_id: Filtrar por hospital especifico
    """
    try:
        breakdown = await get_time_to_fill_breakdown(days=days, hospital_id=hospital_id)
        global_metrics = breakdown.get_global_metrics()

        return {
            "period_days": days,
            "hospital_filter": hospital_id,
            "global": {
                name: {
                    "avg_hours": m.avg_hours if m else 0,
                    "avg_days": m.avg_days if m else 0,
                    "median_hours": m.median_hours if m else 0,
                    "p90_hours": m.p90_hours if m else 0,
                    "sample_size": m.sample_size if m else 0,
                    "status": m.status if m else "unknown",
                    "description": m.description if m else "",
                }
                for name, m in global_metrics.items()
            },
            "by_segment": {
                "time_to_reserve": [
                    {
                        "segment_type": m.segment_type,
                        "segment_value": m.segment_value,
                        "avg_hours": m.avg_hours,
                        "sample_size": m.sample_size,
                        "status": m.status,
                    }
                    for m in breakdown.time_to_reserve
                    if m.segment_type != "global"
                ],
                "time_to_confirm": [
                    {
                        "segment_type": m.segment_type,
                        "segment_value": m.segment_value,
                        "avg_hours": m.avg_hours,
                        "sample_size": m.sample_size,
                        "status": m.status,
                    }
                    for m in breakdown.time_to_confirm
                    if m.segment_type != "global"
                ],
                "time_to_fill": [
                    {
                        "segment_type": m.segment_type,
                        "segment_value": m.segment_value,
                        "avg_hours": m.avg_hours,
                        "sample_size": m.sample_size,
                        "status": m.status,
                    }
                    for m in breakdown.time_to_fill
                    if m.segment_type != "global"
                ],
            },
        }
    except Exception as e:
        logger.error(f"Erro ao obter time-to-fill: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/kpis/health")
async def obter_health_score():
    """
    Retorna Health Score composto.

    Componentes:
    - Pressao (25%): contact_count_7d acima do limite
    - Friccao (35%): opted_out + cooling_off
    - Qualidade (25%): taxa de handoff
    - Spam (15%): campaign_blocked rate

    Retorna recomendacoes baseadas nos componentes.
    """
    try:
        health = await get_health_score()
        return health.to_dict()
    except Exception as e:
        logger.error(f"Erro ao obter health score: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
