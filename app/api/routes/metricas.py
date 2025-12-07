"""
Endpoints para métricas e dashboard.
"""
from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.services.supabase import supabase

router = APIRouter(prefix="/metricas", tags=["Métricas"])
logger = logging.getLogger(__name__)


@router.get("/resumo")
async def obter_resumo(dias: int = 7):
    """
    Retorna resumo de métricas dos últimos N dias.
    """
    data_inicio = (datetime.now() - timedelta(days=dias)).isoformat()

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

