"""
Servico de fila de mensagens agendadas.
"""
from datetime import datetime, timezone
from typing import Optional
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def enfileirar_mensagem(
    cliente_id: str,
    conversa_id: str,
    conteudo: str,
    tipo: str = "lembrete",
    prioridade: int = 5,
    agendar_para: datetime = None,
    metadata: dict = None
) -> dict:
    """
    Enfileira mensagem para envio futuro.

    Args:
        cliente_id: ID do medico
        conversa_id: ID da conversa
        conteudo: Texto da mensagem
        tipo: Tipo da mensagem (lembrete, followup, etc)
        prioridade: Prioridade de 0-10 (maior = mais urgente)
        agendar_para: Data/hora para envio
        metadata: Dados adicionais

    Returns:
        Dados da mensagem enfileirada
    """
    data = {
        "cliente_id": cliente_id,
        "conversa_id": conversa_id,
        "conteudo": conteudo,
        "tipo": tipo,
        "prioridade": prioridade,
        "status": "pendente",
        "agendar_para": agendar_para.isoformat() if agendar_para else None,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    response = (
        supabase.table("fila_mensagens")
        .insert(data)
        .execute()
    )

    if response.data:
        logger.info(f"Mensagem enfileirada para {cliente_id}: {tipo}")
        return response.data[0]

    return None


async def buscar_mensagens_pendentes(limite: int = 10) -> list[dict]:
    """
    Busca mensagens pendentes para envio.

    Args:
        limite: Maximo de mensagens a retornar

    Returns:
        Lista de mensagens pendentes
    """
    agora = datetime.now(timezone.utc).isoformat()

    response = (
        supabase.table("fila_mensagens")
        .select("*")
        .eq("status", "pendente")
        .lte("agendar_para", agora)
        .order("prioridade", desc=True)
        .order("agendar_para")
        .limit(limite)
        .execute()
    )

    return response.data or []


async def marcar_como_enviada(mensagem_id: str) -> bool:
    """
    Marca mensagem como enviada.

    Args:
        mensagem_id: ID da mensagem

    Returns:
        True se atualizou
    """
    response = (
        supabase.table("fila_mensagens")
        .update({
            "status": "enviada",
            "enviada_em": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", mensagem_id)
        .execute()
    )

    return len(response.data) > 0


async def cancelar_mensagem(mensagem_id: str) -> bool:
    """
    Cancela mensagem pendente.

    Args:
        mensagem_id: ID da mensagem

    Returns:
        True se cancelou
    """
    response = (
        supabase.table("fila_mensagens")
        .update({"status": "cancelada"})
        .eq("id", mensagem_id)
        .eq("status", "pendente")
        .execute()
    )

    return len(response.data) > 0
