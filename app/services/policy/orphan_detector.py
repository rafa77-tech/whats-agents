"""
Detector de decisões órfãs do Policy Engine.

Sprint 16 - Observability
Identifica decisões sem efeitos correspondentes, indicando:
- Erros no pipeline
- Timeouts
- Bugs de integração
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class OrphanAnalysis:
    """Resultado da análise de órfãos."""

    total_decisions: int
    total_with_effects: int
    total_orphans: int
    orphan_rate: float
    orphans_by_rule: dict[str, int]
    orphans_by_action: dict[str, int]
    sample_orphans: list[dict]


async def detect_orphans(
    hours: int = 24,
    sample_limit: int = 20,
) -> OrphanAnalysis:
    """
    Detecta decisões sem efeitos correspondentes.

    Uma decisão é órfã se:
    - Não tem nenhum effect registrado
    - Foi criada há mais de 5 minutos (janela de tolerância)

    Args:
        hours: Janela de tempo para análise
        sample_limit: Quantidade de órfãos para retornar como amostra

    Returns:
        OrphanAnalysis com estatísticas
    """
    try:
        # Janela: últimas N horas até 5 minutos atrás (tolerância)
        now = datetime.now(timezone.utc)
        cutoff_start = now - timedelta(hours=hours)
        cutoff_end = now - timedelta(minutes=5)  # Tolerância

        # 1. Buscar todas as decisions na janela
        decisions_response = (
            supabase.table("policy_events")
            .select("policy_decision_id, rule_matched, primary_action, cliente_id, ts")
            .eq("event_type", "decision")
            .gte("ts", cutoff_start.isoformat())
            .lte("ts", cutoff_end.isoformat())
            .execute()
        )

        decisions = decisions_response.data or []
        if not decisions:
            return OrphanAnalysis(
                total_decisions=0,
                total_with_effects=0,
                total_orphans=0,
                orphan_rate=0,
                orphans_by_rule={},
                orphans_by_action={},
                sample_orphans=[],
            )

        # 2. Buscar effects correspondentes
        decision_ids = [d["policy_decision_id"] for d in decisions]

        # Buscar em lotes de 100 para evitar query muito grande
        effect_ids: set[str] = set()
        for i in range(0, len(decision_ids), 100):
            batch = decision_ids[i:i+100]
            effects_response = (
                supabase.table("policy_events")
                .select("policy_decision_id")
                .eq("event_type", "effect")
                .in_("policy_decision_id", batch)
                .execute()
            )
            for e in effects_response.data or []:
                effect_ids.add(e["policy_decision_id"])

        # 3. Identificar órfãos
        orphans = [
            d for d in decisions
            if d["policy_decision_id"] not in effect_ids
        ]

        # 4. Agregar por regra e ação
        by_rule: dict[str, int] = {}
        by_action: dict[str, int] = {}
        for o in orphans:
            rule = o.get("rule_matched") or "unknown"
            action = o.get("primary_action") or "unknown"
            by_rule[rule] = by_rule.get(rule, 0) + 1
            by_action[action] = by_action.get(action, 0) + 1

        # 5. Calcular estatísticas
        total = len(decisions)
        with_effects = len(effect_ids)
        total_orphans = len(orphans)
        orphan_rate = round(total_orphans / total * 100, 2) if total > 0 else 0

        return OrphanAnalysis(
            total_decisions=total,
            total_with_effects=with_effects,
            total_orphans=total_orphans,
            orphan_rate=orphan_rate,
            orphans_by_rule=by_rule,
            orphans_by_action=by_action,
            sample_orphans=orphans[:sample_limit],
        )

    except Exception as e:
        logger.error(f"Erro ao detectar órfãos: {e}")
        return OrphanAnalysis(
            total_decisions=0,
            total_with_effects=0,
            total_orphans=0,
            orphan_rate=0,
            orphans_by_rule={},
            orphans_by_action={},
            sample_orphans=[],
        )


async def get_orphan_rate_trend(
    days: int = 7,
) -> list[dict]:
    """
    Taxa de órfãos por dia nos últimos N dias.

    Útil para identificar regressões.

    Returns:
        Lista de {date, total, orphans, rate}
    """
    try:
        results = []

        for day_offset in range(days):
            date = datetime.now(timezone.utc).date() - timedelta(days=day_offset)
            start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)

            # Contar decisions do dia
            decisions_response = (
                supabase.table("policy_events")
                .select("policy_decision_id", count="exact")
                .eq("event_type", "decision")
                .gte("ts", start.isoformat())
                .lte("ts", end.isoformat())
                .execute()
            )

            total = decisions_response.count or 0

            if total == 0:
                results.append({
                    "date": date.isoformat(),
                    "total": 0,
                    "orphans": 0,
                    "rate": 0,
                })
                continue

            # Buscar IDs das decisions
            ids_response = (
                supabase.table("policy_events")
                .select("policy_decision_id")
                .eq("event_type", "decision")
                .gte("ts", start.isoformat())
                .lte("ts", end.isoformat())
                .execute()
            )

            decision_ids = [d["policy_decision_id"] for d in ids_response.data or []]

            # Contar effects
            effects_response = (
                supabase.table("policy_events")
                .select("policy_decision_id", count="exact")
                .eq("event_type", "effect")
                .in_("policy_decision_id", decision_ids[:500])  # Limitar
                .execute()
            )

            with_effects = effects_response.count or 0
            orphans = total - with_effects
            rate = round(orphans / total * 100, 2) if total > 0 else 0

            results.append({
                "date": date.isoformat(),
                "total": total,
                "orphans": orphans,
                "rate": rate,
            })

        # Ordenar cronologicamente
        return sorted(results, key=lambda x: x["date"])

    except Exception as e:
        logger.error(f"Erro ao calcular trend de órfãos: {e}")
        return []


async def investigate_orphan(
    policy_decision_id: str,
) -> Optional[dict]:
    """
    Investiga uma decisão órfã específica.

    Busca informações adicionais para debug.

    Args:
        policy_decision_id: ID da decisão

    Returns:
        Dict com informações detalhadas
    """
    try:
        # Buscar a decision
        decision_response = (
            supabase.table("policy_events")
            .select("*")
            .eq("policy_decision_id", policy_decision_id)
            .eq("event_type", "decision")
            .single()
            .execute()
        )

        if not decision_response.data:
            return None

        decision = decision_response.data

        # Verificar se há effects
        effects_response = (
            supabase.table("policy_events")
            .select("*")
            .eq("policy_decision_id", policy_decision_id)
            .eq("event_type", "effect")
            .execute()
        )

        effects = effects_response.data or []

        # Buscar interação correspondente (se existir)
        interaction_id = decision.get("interaction_id")
        interaction = None
        if interaction_id:
            try:
                int_response = (
                    supabase.table("interacoes")
                    .select("*")
                    .eq("id", interaction_id)
                    .single()
                    .execute()
                )
                interaction = int_response.data
            except Exception:
                pass

        return {
            "decision": decision,
            "effects": effects,
            "has_effects": len(effects) > 0,
            "interaction": interaction,
            "cliente_id": decision.get("cliente_id"),
            "conversation_id": decision.get("conversation_id"),
            "rule_matched": decision.get("rule_matched"),
            "primary_action": decision.get("primary_action"),
            "ts": decision.get("ts"),
            "time_since": str(
                datetime.now(timezone.utc) - datetime.fromisoformat(
                    decision.get("ts", "").replace("Z", "+00:00")
                )
            ) if decision.get("ts") else None,
        }

    except Exception as e:
        logger.error(f"Erro ao investigar órfão {policy_decision_id}: {e}")
        return None


async def check_health() -> dict:
    """
    Health check do pipeline baseado em taxa de órfãos.

    Returns:
        Dict com status de saúde
    """
    analysis = await detect_orphans(hours=1)

    # Critérios de saúde
    healthy = analysis.orphan_rate < 5  # Menos de 5% de órfãos
    warning = 5 <= analysis.orphan_rate < 15
    critical = analysis.orphan_rate >= 15

    status = "healthy" if healthy else ("warning" if warning else "critical")

    return {
        "status": status,
        "orphan_rate": analysis.orphan_rate,
        "total_decisions_1h": analysis.total_decisions,
        "total_orphans_1h": analysis.total_orphans,
        "top_orphan_rules": dict(
            sorted(analysis.orphans_by_rule.items(), key=lambda x: -x[1])[:3]
        ),
    }
