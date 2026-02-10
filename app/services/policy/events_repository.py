"""
Repositório para policy_events.

Sprint 16 - Observability
Persiste decisões e efeitos para auditoria, métricas e replay.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase
from .types import DoctorState, PolicyDecision
from .version import POLICY_VERSION

logger = logging.getLogger(__name__)


async def persist_decision(
    event_id: str,
    policy_decision_id: str,
    state: DoctorState,
    decision: PolicyDecision,
    doctor_state_input: dict,
    snapshot_hash: str,
    conversation_id: Optional[str] = None,
    interaction_id: Optional[int] = None,
    is_first_message: bool = False,
    conversa_status: str = "active",
) -> bool:
    """
    Persiste uma decisão de policy na tabela policy_events.

    Args:
        event_id: UUID único do evento
        policy_decision_id: UUID da decisão (trace_id)
        state: Estado do médico
        decision: Decisão tomada
        doctor_state_input: Estado serializado para replay
        snapshot_hash: Hash do estado para verificação
        conversation_id: ID da conversa (opcional)
        interaction_id: ID da interação/mensagem (opcional)
        is_first_message: Se é primeira mensagem
        conversa_status: Status da conversa

    Returns:
        True se persistido com sucesso
    """
    try:
        # Sprint 16 Fix: usar forbid_all do decision (não mais "*" em forbidden_actions)
        forbid_all = decision.forbid_all
        forbidden_actions = decision.forbidden_actions

        event_data = {
            "event_id": event_id,
            "policy_decision_id": policy_decision_id,
            "event_type": "decision",
            "ts": datetime.now(timezone.utc).isoformat(),
            "policy_version": POLICY_VERSION,
            "cliente_id": state.cliente_id,
            "conversation_id": conversation_id,
            "interaction_id": interaction_id,
            "rule_matched": decision.rule_id,
            "primary_action": decision.primary_action.value,
            "tone": decision.tone.value,
            "requires_human": decision.requires_human,
            "forbid_all": forbid_all,
            "allowed_actions": decision.allowed_actions,
            "forbidden_actions": forbidden_actions,
            "doctor_state_input": doctor_state_input,
            "snapshot_hash": snapshot_hash,
            "reasoning": decision.reasoning,
            "is_first_message": is_first_message,
            "conversa_status": conversa_status,
        }

        supabase.table("policy_events").insert(event_data).execute()

        logger.debug(f"Decision persistido: {policy_decision_id[:8]}...")
        return True

    except Exception as e:
        logger.error(f"Erro ao persistir decision: {e}")
        return False


async def persist_effect(
    event_id: str,
    policy_decision_id: str,
    cliente_id: str,
    conversation_id: Optional[str],
    effect_type: str,
    interaction_id: Optional[int] = None,
    details: Optional[dict] = None,
) -> bool:
    """
    Persiste um efeito de policy na tabela policy_events.

    Args:
        event_id: UUID único do evento
        policy_decision_id: UUID da decisão que gerou o efeito
        cliente_id: ID do cliente
        conversation_id: ID da conversa
        effect_type: Tipo do efeito (message_sent, handoff_triggered, wait_applied, error, safe_mode_applied)
        interaction_id: ID da interação/mensagem (opcional)
        details: Detalhes adicionais (opcional)

    Returns:
        True se persistido com sucesso
    """
    try:
        event_data = {
            "event_id": event_id,
            "policy_decision_id": policy_decision_id,
            "event_type": "effect",
            "ts": datetime.now(timezone.utc).isoformat(),
            "policy_version": POLICY_VERSION,
            "cliente_id": cliente_id,
            "conversation_id": conversation_id,
            "interaction_id": interaction_id,
            "effect_type": effect_type,
            "effect_details": details or {},
        }

        supabase.table("policy_events").insert(event_data).execute()

        logger.debug(f"Effect persistido: {effect_type} -> {policy_decision_id[:8]}...")
        return True

    except Exception as e:
        logger.error(f"Erro ao persistir effect: {e}")
        return False


async def check_effect_exists(
    policy_decision_id: str,
    interaction_id: int,
    effect_type: str,
) -> bool:
    """
    Verifica se um efeito já foi registrado (idempotência).

    Usado para evitar duplicação quando a mesma interaction_id
    tenta registrar o mesmo tipo de efeito.

    Args:
        policy_decision_id: UUID da decisão
        interaction_id: ID da interação
        effect_type: Tipo do efeito

    Returns:
        True se já existe
    """
    try:
        response = (
            supabase.table("policy_events")
            .select("event_id")
            .eq("policy_decision_id", policy_decision_id)
            .eq("interaction_id", interaction_id)
            .eq("effect_type", effect_type)
            .limit(1)
            .execute()
        )

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao verificar effect existente: {e}")
        return False


async def get_decision_by_id(policy_decision_id: str) -> Optional[dict]:
    """
    Busca uma decisão pelo ID.

    Args:
        policy_decision_id: UUID da decisão

    Returns:
        Dados da decisão ou None
    """
    try:
        response = (
            supabase.table("policy_events")
            .select("*")
            .eq("policy_decision_id", policy_decision_id)
            .eq("event_type", "decision")
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]
        return None

    except Exception as e:
        logger.error(f"Erro ao buscar decision: {e}")
        return None


async def get_effects_for_decision(policy_decision_id: str) -> list[dict]:
    """
    Busca todos os efeitos de uma decisão.

    Args:
        policy_decision_id: UUID da decisão

    Returns:
        Lista de efeitos
    """
    try:
        response = (
            supabase.table("policy_events")
            .select("*")
            .eq("policy_decision_id", policy_decision_id)
            .eq("event_type", "effect")
            .order("ts", desc=False)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar effects: {e}")
        return []


async def get_events_for_cliente(
    cliente_id: str,
    limit: int = 100,
    event_type: Optional[str] = None,
) -> list[dict]:
    """
    Busca eventos de um cliente.

    Args:
        cliente_id: ID do cliente
        limit: Máximo de eventos
        event_type: Filtrar por tipo (decision, effect)

    Returns:
        Lista de eventos ordenados por ts desc
    """
    try:
        query = supabase.table("policy_events").select("*").eq("cliente_id", cliente_id)

        if event_type:
            query = query.eq("event_type", event_type)

        response = query.order("ts", desc=True).limit(limit).execute()

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos do cliente: {e}")
        return []


async def update_effect_interaction_id(
    policy_decision_id: str,
    effect_type: str,
    interaction_id: int,
    max_retries: int = 3,
    retry_delay: float = 0.1,
) -> bool:
    """
    Atualiza o interaction_id de um effect existente.

    Sprint 16 - E08: Fechar ciclo interaction_id
    Usado após salvar_interacao retornar o ID.

    Sprint 16 Fix: Retry para garantir que effect existe (fire-and-forget timing).

    Args:
        policy_decision_id: UUID da decisão
        effect_type: Tipo do efeito (message_sent, etc)
        interaction_id: ID da interação salva
        max_retries: Número máximo de tentativas
        retry_delay: Delay entre tentativas em segundos

    Returns:
        True se atualizado com sucesso
    """
    import asyncio

    for attempt in range(max_retries):
        try:
            response = (
                supabase.table("policy_events")
                .update({"interaction_id": interaction_id})
                .eq("policy_decision_id", policy_decision_id)
                .eq("effect_type", effect_type)
                .is_("interaction_id", "null")  # Só atualiza se ainda não tem
                .execute()
            )

            if response.data:
                logger.debug(f"Effect atualizado com interaction_id: {interaction_id}")
                return True

            # Se não atualizou, pode ser que o effect ainda não existe (fire-and-forget)
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))  # Backoff exponencial
                continue

            return False

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt + 1}/{max_retries} update interaction_id: {e}")
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"Erro ao atualizar interaction_id após {max_retries} tentativas: {e}")
                return False

    return False


async def count_decisions_by_rule(
    hours: int = 24,
) -> list[dict]:
    """
    Conta decisões agrupadas por regra nas últimas N horas.

    Útil para métricas de quais regras estão disparando.

    Args:
        hours: Janela de tempo em horas

    Returns:
        Lista de {rule_matched, count}
    """
    try:
        # RPC para query agregada
        response = supabase.rpc("count_policy_decisions_by_rule", {"hours_window": hours}).execute()

        return response.data or []

    except Exception as e:
        logger.warning(f"RPC não disponível, usando query manual: {e}")
        # Fallback: query manual (menos eficiente)
        try:
            from datetime import timedelta

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
                rule = row.get("rule_matched", "unknown")
                counts[rule] = counts.get(rule, 0) + 1

            return [{"rule_matched": k, "count": v} for k, v in counts.items()]

        except Exception as e2:
            logger.error(f"Erro no fallback de count_decisions_by_rule: {e2}")
            return []
