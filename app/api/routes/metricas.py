"""
Endpoints para métricas e dashboard.

Sprint 17 - E06: Endpoints de funil
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase
from app.services.business_events.metrics import (
    get_funnel_metrics,
    get_funnel_by_hospital,
    get_funnel_trend,
    get_top_doctors,
    get_conversion_time,
)

router = APIRouter(prefix="/metricas", tags=["Métricas"])
logger = logging.getLogger(__name__)


@router.get("/resumo")
async def obter_resumo(dias: int = 7):
    """
    Retorna resumo de métricas dos últimos N dias.
    """
    data_inicio = (agora_brasilia() - timedelta(days=dias)).isoformat()

    try:
        # Total de conversas
        conversas_response = (
            supabase.table("conversations")
            .select("id, status, created_at")
            .gte("created_at", data_inicio)
            .execute()
        )
        conversas = conversas_response.data or []

        # Total de interações
        interacoes_response = (
            supabase.table("interacoes")
            .select("id, direcao, origem, created_at")
            .gte("created_at", data_inicio)
            .execute()
        )
        interacoes = interacoes_response.data or []

        # Handoffs
        handoffs_response = (
            supabase.table("handoffs")
            .select("id, trigger_type, status, created_at")
            .gte("created_at", data_inicio)
            .execute()
        )
        handoffs = handoffs_response.data or []

        # Calcular métricas
        total_conversas = len(conversas)
        conversas_ativas = len([c for c in conversas if c.get("status") == "active" or c.get("status") == "ativa"])

        msgs_entrada = len([i for i in interacoes if i.get("direcao") == "entrada"])
        msgs_saida = len([i for i in interacoes if i.get("direcao") == "saida"])

        total_handoffs = len(handoffs)
        handoffs_por_tipo = {}
        for h in handoffs:
            tipo = h.get("trigger_type", "desconhecido")
            handoffs_por_tipo[tipo] = handoffs_por_tipo.get(tipo, 0) + 1

        # Taxa de resposta (mensagens enviadas / recebidas)
        taxa_resposta = msgs_saida / msgs_entrada if msgs_entrada > 0 else 0
        # Taxa de handoff (handoffs / conversas)
        taxa_handoff = total_handoffs / total_conversas if total_conversas > 0 else 0

        return {
            "periodo_dias": dias,
            "conversas": {
                "total": total_conversas,
                "ativas": conversas_ativas,
            },
            "mensagens": {
                "recebidas": msgs_entrada,
                "enviadas": msgs_saida,
            },
            "handoffs": {
                "total": total_handoffs,
                "por_tipo": handoffs_por_tipo,
            },
            "taxas": {
                "resposta": taxa_resposta,
                "handoff": taxa_handoff,
            }
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo de métricas: {e}")
        return {
            "periodo_dias": dias,
            "conversas": {"total": 0, "ativas": 0},
            "mensagens": {"recebidas": 0, "enviadas": 0},
            "handoffs": {"total": 0, "por_tipo": {}},
            "taxas": {"resposta": 0, "handoff": 0},
            "erro": str(e)
        }


# =============================================================================
# Sprint 17 - E06: Endpoints de Funil de Negócio
# =============================================================================


@router.get("/funil")
async def funil_geral(
    hours: int = Query(24, ge=1, le=720, description="Janela de tempo em horas"),
    hospital_id: Optional[str] = Query(None, description="Filtrar por hospital"),
):
    """
    Retorna métricas de funil de conversão.

    O funil mostra a jornada:
    outbound → inbound → offer → accepted → completed

    - **hours**: Janela de tempo em horas (default 24, max 720 = 30 dias)
    - **hospital_id**: Filtrar por hospital específico (opcional)
    """
    metrics = await get_funnel_metrics(hours=hours, hospital_id=hospital_id)
    return metrics.to_dict()


@router.get("/funil/hospitais")
async def funil_por_hospital(
    hours: int = Query(24, ge=1, le=720, description="Janela de tempo em horas"),
):
    """
    Retorna métricas de funil segmentadas por hospital.

    Útil para identificar quais hospitais têm melhor conversão.

    - **hours**: Janela de tempo em horas (default 24)
    """
    return await get_funnel_by_hospital(hours=hours)


@router.get("/funil/tendencia")
async def funil_tendencia(
    days: int = Query(7, ge=1, le=30, description="Número de dias"),
    hospital_id: Optional[str] = Query(None, description="Filtrar por hospital"),
):
    """
    Retorna tendência do funil nos últimos dias.

    Mostra contagens diárias de cada evento para análise de tendência.

    - **days**: Número de dias (default 7, max 30)
    - **hospital_id**: Filtrar por hospital específico (opcional)
    """
    return await get_funnel_trend(days=days, hospital_id=hospital_id)


@router.get("/funil/top-medicos")
async def top_medicos(
    hours: int = Query(168, ge=1, le=720, description="Janela de tempo em horas"),
    limit: int = Query(50, ge=1, le=200, description="Número máximo de resultados"),
):
    """
    Retorna médicos mais ativos (temperatura operacional).

    Proxy para identificar a "base quente" de médicos engajados.

    - **hours**: Janela de tempo (default 168 = 7 dias)
    - **limit**: Número máximo de resultados (default 50)
    """
    return await get_top_doctors(hours=hours, limit=limit)


@router.get("/funil/tempo-conversao")
async def tempo_conversao(
    hours: int = Query(720, ge=1, le=2160, description="Janela de tempo em horas"),
    hospital_id: Optional[str] = Query(None, description="Filtrar por hospital"),
):
    """
    Retorna tempo médio de conversão entre etapas do funil.

    Mede quanto tempo demora para uma oferta ser aceita e o plantão ser realizado.

    - **hours**: Janela de tempo (default 720 = 30 dias, max 2160 = 90 dias)
    - **hospital_id**: Filtrar por hospital específico (opcional)
    """
    return await get_conversion_time(hours=hours, hospital_id=hospital_id)

