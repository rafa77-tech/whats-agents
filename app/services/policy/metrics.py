"""
Métricas do Policy Engine.

Sprint 16 - Observability
5 queries principais para monitoramento.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def get_decisions_count(
    hours: int = 24,
    cliente_id: Optional[str] = None,
) -> int:
    """
    Conta total de decisões nas últimas N horas.

    Args:
        hours: Janela de tempo em horas
        cliente_id: Filtrar por cliente (opcional)

    Returns:
        Total de decisões
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            supabase.table("policy_events")
            .select("event_id", count="exact")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
        )

        if cliente_id:
            query = query.eq("cliente_id", cliente_id)

        response = query.execute()
        return response.count or 0

    except Exception as e:
        logger.error(f"Erro ao contar decisions: {e}")
        return 0


async def get_decisions_by_rule(
    hours: int = 24,
) -> list[dict]:
    """
    Agrupa decisões por regra nas últimas N horas.

    Métricas:
    - Qual regra está disparando mais
    - Distribuição de regras

    Returns:
        Lista de {rule_matched, count}
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        response = (
            supabase.table("policy_events")
            .select("rule_matched")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
            .execute()
        )

        # Agregar manualmente
        counts: dict[str, int] = {}
        for row in response.data or []:
            rule = row.get("rule_matched") or "unknown"
            counts[rule] = counts.get(rule, 0) + 1

        # Ordenar por count desc
        result = [
            {"rule_matched": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]
        return result

    except Exception as e:
        logger.error(f"Erro ao agrupar decisions por regra: {e}")
        return []


async def get_decisions_by_action(
    hours: int = 24,
) -> list[dict]:
    """
    Agrupa decisões por primary_action nas últimas N horas.

    Métricas:
    - Distribuição de ações (followup, wait, handoff, etc)

    Returns:
        Lista de {primary_action, count}
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        response = (
            supabase.table("policy_events")
            .select("primary_action")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
            .execute()
        )

        # Agregar manualmente
        counts: dict[str, int] = {}
        for row in response.data or []:
            action = row.get("primary_action") or "unknown"
            counts[action] = counts.get(action, 0) + 1

        # Ordenar por count desc
        result = [
            {"primary_action": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]
        return result

    except Exception as e:
        logger.error(f"Erro ao agrupar decisions por action: {e}")
        return []


async def get_effects_by_type(
    hours: int = 24,
) -> list[dict]:
    """
    Agrupa efeitos por tipo nas últimas N horas.

    Métricas:
    - Quantas mensagens enviadas
    - Quantos handoffs
    - Quantos waits
    - Quantos erros

    Returns:
        Lista de {effect_type, count}
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        response = (
            supabase.table("policy_events")
            .select("effect_type")
            .eq("event_type", "effect")
            .gte("ts", cutoff.isoformat())
            .execute()
        )

        # Agregar manualmente
        counts: dict[str, int] = {}
        for row in response.data or []:
            effect = row.get("effect_type") or "unknown"
            counts[effect] = counts.get(effect, 0) + 1

        # Ordenar por count desc
        result = [
            {"effect_type": k, "count": v}
            for k, v in sorted(counts.items(), key=lambda x: -x[1])
        ]
        return result

    except Exception as e:
        logger.error(f"Erro ao agrupar effects por type: {e}")
        return []


async def get_handoff_count(
    hours: int = 24,
) -> int:
    """
    Conta handoffs nas últimas N horas.

    Args:
        hours: Janela de tempo

    Returns:
        Total de handoffs (decisions com requires_human=true)
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        response = (
            supabase.table("policy_events")
            .select("event_id", count="exact")
            .eq("event_type", "decision")
            .eq("requires_human", True)
            .gte("ts", cutoff.isoformat())
            .execute()
        )

        return response.count or 0

    except Exception as e:
        logger.error(f"Erro ao contar handoffs: {e}")
        return 0


async def get_decisions_per_hour(
    hours: int = 24,
) -> list[dict]:
    """
    Decisões agrupadas por hora nas últimas N horas.

    Útil para visualizar volume ao longo do tempo.

    Returns:
        Lista de {hour, count}
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        response = (
            supabase.table("policy_events")
            .select("ts")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
            .execute()
        )

        # Agregar por hora
        counts: dict[str, int] = {}
        for row in response.data or []:
            ts_str = row.get("ts", "")
            if ts_str:
                # Extrair hora (formato: 2024-01-15T10:00:00)
                hour = ts_str[:13]  # "2024-01-15T10"
                counts[hour] = counts.get(hour, 0) + 1

        # Ordenar cronologicamente
        result = [
            {"hour": k, "count": v}
            for k, v in sorted(counts.items())
        ]
        return result

    except Exception as e:
        logger.error(f"Erro ao agrupar decisions por hora: {e}")
        return []


async def get_orphan_decisions(
    hours: int = 24,
    limit: int = 100,
) -> list[dict]:
    """
    Encontra decisões sem efeitos correspondentes.

    Decisões órfãs podem indicar:
    - Bugs no pipeline
    - Erros de rede
    - Timeouts

    Args:
        hours: Janela de tempo
        limit: Máximo de resultados

    Returns:
        Lista de decisions sem effects
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Buscar todas as decisions
        decisions_response = (
            supabase.table("policy_events")
            .select("policy_decision_id, cliente_id, rule_matched, ts")
            .eq("event_type", "decision")
            .gte("ts", cutoff.isoformat())
            .limit(500)  # Limitar para performance
            .execute()
        )

        if not decisions_response.data:
            return []

        # Buscar effects correspondentes
        decision_ids = [d["policy_decision_id"] for d in decisions_response.data]

        effects_response = (
            supabase.table("policy_events")
            .select("policy_decision_id")
            .eq("event_type", "effect")
            .in_("policy_decision_id", decision_ids)
            .execute()
        )

        # IDs que têm effect
        effect_ids = {e["policy_decision_id"] for e in effects_response.data or []}

        # Filtrar órfãos
        orphans = [
            d for d in decisions_response.data
            if d["policy_decision_id"] not in effect_ids
        ]

        return orphans[:limit]

    except Exception as e:
        logger.error(f"Erro ao buscar orphan decisions: {e}")
        return []


async def get_policy_summary(hours: int = 24) -> dict:
    """
    Resumo geral do Policy Engine nas últimas N horas.

    Combina todas as métricas em um único objeto.

    Returns:
        Dict com todas as métricas
    """
    try:
        # Executar queries em paralelo
        import asyncio

        results = await asyncio.gather(
            get_decisions_count(hours),
            get_handoff_count(hours),
            get_decisions_by_rule(hours),
            get_decisions_by_action(hours),
            get_effects_by_type(hours),
            return_exceptions=True,
        )

        # Tratar erros individuais
        decisions_count = results[0] if not isinstance(results[0], Exception) else 0
        handoff_count = results[1] if not isinstance(results[1], Exception) else 0
        by_rule = results[2] if not isinstance(results[2], Exception) else []
        by_action = results[3] if not isinstance(results[3], Exception) else []
        by_effect = results[4] if not isinstance(results[4], Exception) else []

        return {
            "period_hours": hours,
            "total_decisions": decisions_count,
            "total_handoffs": handoff_count,
            "handoff_rate": round(handoff_count / decisions_count * 100, 2) if decisions_count > 0 else 0,
            "decisions_by_rule": by_rule,
            "decisions_by_action": by_action,
            "effects_by_type": by_effect,
        }

    except Exception as e:
        logger.error(f"Erro ao gerar policy summary: {e}")
        return {
            "error": str(e),
            "period_hours": hours,
        }
