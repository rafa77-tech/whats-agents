"""
Repositório para conversation_mode.

Sprint 29 - Conversation Mode
"""

import logging
from typing import Optional

from app.core.timezone import agora_utc
from app.services.supabase import supabase
from .types import ConversationMode, ModeInfo

logger = logging.getLogger(__name__)


async def get_conversation_mode(conversa_id: str) -> ModeInfo:
    """
    Busca modo atual da conversa.

    Args:
        conversa_id: ID da conversa

    Returns:
        ModeInfo com modo atual (default: discovery)
    """
    try:
        response = (
            supabase.table("conversations")
            .select(
                "id, conversation_mode, mode_updated_at, mode_updated_reason, "
                "mode_source, pending_transition, pending_transition_at"
            )
            .eq("id", conversa_id)
            .single()
            .execute()
        )

        if response.data:
            return ModeInfo.from_row(response.data)

        # Conversa não encontrada - retornar default
        logger.warning(f"Conversa não encontrada: {conversa_id}")
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )

    except Exception as e:
        logger.error(f"Erro ao buscar conversation_mode: {e}")
        return ModeInfo(
            conversa_id=conversa_id,
            mode=ConversationMode.DISCOVERY,
        )


async def set_conversation_mode(
    conversa_id: str,
    mode: ConversationMode,
    reason: str,
    source: Optional[str] = None,
) -> bool:
    """
    Atualiza modo da conversa.

    Args:
        conversa_id: ID da conversa
        mode: Novo modo
        reason: Motivo da transição (para auditoria)
        source: Origem do modo (inbound, campaign:<id>, manual)

    Returns:
        True se sucesso
    """
    try:
        update_data = {
            "conversation_mode": mode.value,
            "mode_updated_at": agora_utc().isoformat(),
            "mode_updated_reason": reason,
            # Limpa pending quando transiciona
            "pending_transition": None,
            "pending_transition_at": None,
        }

        if source:
            update_data["mode_source"] = source

        (supabase.table("conversations").update(update_data).eq("id", conversa_id).execute())

        logger.info(
            f"Mode atualizado: {conversa_id} -> {mode.value}",
            extra={
                "conversa_id": conversa_id,
                "mode": mode.value,
                "reason": reason,
                "source": source,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar conversation_mode: {e}")
        return False


async def set_pending_transition(
    conversa_id: str,
    pending_mode: ConversationMode,
) -> bool:
    """
    Define transição pendente de confirmação.

    Usado para micro-confirmação: salva a transição proposta
    e aguarda confirmação do médico.

    Args:
        conversa_id: ID da conversa
        pending_mode: Modo para o qual transicionar se confirmado

    Returns:
        True se sucesso
    """
    try:
        (
            supabase.table("conversations")
            .update(
                {
                    "pending_transition": pending_mode.value,
                    "pending_transition_at": agora_utc().isoformat(),
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        logger.info(
            f"Pending transition: {conversa_id} -> {pending_mode.value}",
            extra={
                "conversa_id": conversa_id,
                "pending_mode": pending_mode.value,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao definir pending_transition: {e}")
        return False


async def clear_pending_transition(
    conversa_id: str,
    reason: str = "cancelled",
) -> bool:
    """
    Limpa transição pendente (cancelada ou expirada).

    Args:
        conversa_id: ID da conversa
        reason: Motivo do cancelamento

    Returns:
        True se sucesso
    """
    try:
        (
            supabase.table("conversations")
            .update(
                {
                    "pending_transition": None,
                    "pending_transition_at": None,
                }
            )
            .eq("id", conversa_id)
            .execute()
        )

        logger.info(
            f"Pending transition cleared: {conversa_id} ({reason})",
            extra={
                "conversa_id": conversa_id,
                "reason": reason,
            },
        )
        return True

    except Exception as e:
        logger.error(f"Erro ao limpar pending_transition: {e}")
        return False
