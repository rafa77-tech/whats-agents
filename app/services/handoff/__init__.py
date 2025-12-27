"""
Services de handoff IA <-> Humano.

Sprint 10 - S10.E3.4
Sprint 15 - policy_decision_id tracking
"""
from typing import Optional

from .messages import (
    MENSAGENS_TRANSICAO,
    obter_mensagem_transicao,
)

from .flow import (
    iniciar_handoff,
    finalizar_handoff,
    resolver_handoff,
)

from .repository import (
    listar_handoffs_pendentes,
    obter_metricas_handoff,
    verificar_handoff_ativo,
)


async def criar_handoff(
    conversa_id: str,
    motivo: str,
    trigger_type: str = "manual",
    policy_decision_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Alias simplificado para iniciar_handoff (busca cliente_id automaticamente).

    Sprint 15: Usado pelo agente quando PolicyDecide retorna HANDOFF.

    Args:
        conversa_id: ID da conversa
        motivo: Motivo do handoff
        trigger_type: Tipo do trigger
        policy_decision_id: ID da decisão de policy que originou

    Returns:
        Dados do handoff criado ou None
    """
    from app.services.supabase import supabase

    # Buscar cliente_id da conversa
    response = (
        supabase.table("conversations")
        .select("cliente_id")
        .eq("id", conversa_id)
        .single()
        .execute()
    )

    if not response.data:
        return None

    cliente_id = response.data["cliente_id"]

    return await iniciar_handoff(
        conversa_id=conversa_id,
        cliente_id=cliente_id,
        motivo=motivo,
        trigger_type=trigger_type,
        policy_decision_id=policy_decision_id,
    )


__all__ = [
    # Messages
    "MENSAGENS_TRANSICAO",
    "obter_mensagem_transicao",
    # Flow
    "iniciar_handoff",
    "finalizar_handoff",
    "resolver_handoff",
    "criar_handoff",  # Alias simplificado
    # Repository
    "listar_handoffs_pendentes",
    "obter_metricas_handoff",
    "verificar_handoff_ativo",
]
