"""
Queries e persistencia de handoffs.

Sprint 10 - S10.E3.4
"""
from datetime import datetime, timedelta
import logging

from app.core.timezone import agora_brasilia
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def listar_handoffs_pendentes() -> list:
    """
    Lista todos os handoffs pendentes.

    Returns:
        Lista de handoffs com dados da conversa e cliente
    """
    try:
        handoffs_response = (
            supabase.table("handoffs")
            .select("*")
            .eq("status", "pendente")
            .order("created_at", desc=False)
            .execute()
        )

        handoffs = handoffs_response.data or []
        resultado = []

        for handoff in handoffs:
            conversa_id = handoff.get("conversa_id")
            if conversa_id:
                conversa_response = (
                    supabase.table("conversations")
                    .select("*, clientes(*)")
                    .eq("id", conversa_id)
                    .single()
                    .execute()
                )
                if conversa_response.data:
                    handoff["conversations"] = conversa_response.data
            resultado.append(handoff)

        return resultado

    except Exception as e:
        logger.error(f"Erro ao listar handoffs pendentes: {e}")
        return []


async def obter_metricas_handoff(periodo_dias: int = 30) -> dict:
    """
    Retorna metricas de handoff do periodo.

    Args:
        periodo_dias: Numero de dias para calcular metricas

    Returns:
        Dict com metricas agregadas
    """
    try:
        data_inicio = (agora_brasilia() - timedelta(days=periodo_dias)).isoformat()

        response = (
            supabase.table("handoffs")
            .select("trigger_type, status, created_at, resolvido_em")
            .gte("created_at", data_inicio)
            .execute()
        )

        handoffs = response.data or []

        # Agrupar por tipo
        por_tipo = {}
        for h in handoffs:
            tipo = h.get("trigger_type", "manual")
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        # Calcular tempo medio de resolucao
        resolvidos = [h for h in handoffs if h.get("status") == "resolvido" and h.get("resolvido_em")]
        tempo_medio_minutos = _calcular_tempo_medio(resolvidos)

        return {
            "total": len(handoffs),
            "pendentes": len([h for h in handoffs if h.get("status") == "pendente"]),
            "resolvidos": len(resolvidos),
            "por_tipo": por_tipo,
            "tempo_medio_resolucao_minutos": tempo_medio_minutos
        }

    except Exception as e:
        logger.error(f"Erro ao obter metricas de handoff: {e}")
        return {
            "total": 0,
            "pendentes": 0,
            "resolvidos": 0,
            "por_tipo": {},
            "tempo_medio_resolucao_minutos": 0
        }


def _calcular_tempo_medio(handoffs_resolvidos: list) -> int:
    """Calcula tempo medio de resolucao em minutos."""
    if not handoffs_resolvidos:
        return 0

    tempos = []
    for h in handoffs_resolvidos:
        try:
            criado = datetime.fromisoformat(h["created_at"].replace("Z", "+00:00"))
            resolvido = datetime.fromisoformat(h["resolvido_em"].replace("Z", "+00:00"))
            minutos = (resolvido - criado).total_seconds() / 60
            tempos.append(minutos)
        except Exception:
            pass

    return int(sum(tempos) / len(tempos)) if tempos else 0


async def verificar_handoff_ativo(conversa_id: str) -> bool:
    """
    Verifica se ha handoff ativo para a conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        True se conversa esta sob controle humano
    """
    try:
        response = (
            supabase.table("conversations")
            .select("controlled_by")
            .eq("id", conversa_id)
            .execute()
        )

        if response.data:
            return response.data[0].get("controlled_by") == "human"

        return False

    except Exception as e:
        logger.error(f"Erro ao verificar handoff: {e}")
        return False
