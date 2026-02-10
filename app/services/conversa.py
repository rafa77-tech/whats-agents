"""
Servico para gerenciamento de conversas.
"""

from typing import Optional, Literal
import logging

from app.core.timezone import agora_utc
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_conversa_ativa(cliente_id: str) -> Optional[dict]:
    """
    Busca conversa ativa (aberta) do cliente (query otimizada).

    Args:
        cliente_id: ID do medico

    Returns:
        Dados da conversa ou None
    """
    try:
        # Query otimizada - apenas campos necessários
        response = (
            supabase.table("conversations")
            .select("id, cliente_id, status, controlled_by, chatwoot_conversation_id, created_at")
            .eq("cliente_id", cliente_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao buscar conversa: {e}")
        return None


async def criar_conversa(
    cliente_id: str, controlled_by: Literal["ai", "human"] = "ai"
) -> Optional[dict]:
    """
    Cria nova conversa.

    Args:
        cliente_id: ID do medico
        controlled_by: Quem controla (ai ou human)

    Returns:
        Dados da conversa criada
    """
    try:
        response = (
            supabase.table("conversations")
            .insert(
                {
                    "cliente_id": cliente_id,
                    "status": "active",
                    "controlled_by": controlled_by,
                }
            )
            .execute()
        )
        logger.info(f"Conversa criada para cliente {cliente_id}")
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao criar conversa: {e}")
        return None


async def buscar_ou_criar_conversa(cliente_id: str) -> Optional[dict]:
    """
    Busca conversa ativa ou cria nova.

    Args:
        cliente_id: ID do medico

    Returns:
        Dados da conversa
    """
    # Buscar conversa ativa
    conversa = await buscar_conversa_ativa(cliente_id)

    if conversa:
        logger.debug(f"Conversa ativa encontrada: {conversa['id']}")
        return conversa

    # Criar nova
    logger.info(f"Criando nova conversa para {cliente_id}")
    conversa = await criar_conversa(cliente_id)

    # Iniciar métricas para a nova conversa
    if conversa:
        from app.services.metricas import metricas_service

        await metricas_service.iniciar_metricas_conversa(conversa["id"])

    return conversa


async def atualizar_conversa(conversa_id: str, **campos) -> Optional[dict]:
    """Atualiza campos da conversa."""
    try:
        campos["updated_at"] = agora_utc().isoformat()
        response = supabase.table("conversations").update(campos).eq("id", conversa_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error(f"Erro ao atualizar conversa: {e}")
        return None


async def fechar_conversa(conversa_id: str, motivo: str = "concluida") -> bool:
    """Fecha uma conversa."""
    result = await atualizar_conversa(
        conversa_id,
        status="completed",
    )
    return result is not None


async def transferir_para_humano(conversa_id: str) -> bool:
    """Transfere conversa para controle humano."""
    result = await atualizar_conversa(conversa_id, controlled_by="human")
    return result is not None


async def conversa_controlada_por_ia(conversa_id: str) -> bool:
    """Verifica se conversa esta sob controle da IA."""
    try:
        response = (
            supabase.table("conversations").select("controlled_by").eq("id", conversa_id).execute()
        )
        if response.data:
            return response.data[0]["controlled_by"] == "ai"
        return False
    except Exception as e:
        logger.error(f"Erro ao verificar controle: {e}")
        return False
