"""
Dead Letter Queue para webhooks.

Sprint 26 - E06

Armazena webhooks que falharam para reprocessamento.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def salvar_dlq(
    instance_name: str,
    event_type: str,
    payload: dict,
    erro: str,
    tentativa: int = 1,
) -> str:
    """
    Salva webhook na DLQ.

    Args:
        instance_name: Instancia que recebeu
        event_type: Tipo do evento
        payload: Payload original
        erro: Mensagem de erro
        tentativa: Numero da tentativa

    Returns:
        ID do registro DLQ
    """
    result = supabase.table("webhook_dlq").insert({
        "instance_name": instance_name,
        "event_type": event_type,
        "payload": payload,
        "erro": erro,
        "tentativa": tentativa,
        "status": "pending" if tentativa < MAX_RETRIES else "failed",
    }).execute()

    dlq_id = result.data[0]["id"] if result.data else None

    logger.warning(
        f"[DLQ] Webhook salvo: {dlq_id} ({instance_name}/{event_type}) - "
        f"Tentativa {tentativa}/{MAX_RETRIES}"
    )

    return dlq_id


async def listar_pendentes(limit: int = 50) -> List[Dict]:
    """
    Lista webhooks pendentes para reprocessamento.

    Returns:
        Lista de webhooks pendentes
    """
    result = supabase.table("webhook_dlq").select("*").eq(
        "status", "pending"
    ).order(
        "created_at", desc=False  # FIFO
    ).limit(limit).execute()

    return result.data or []


async def marcar_sucesso(dlq_id: str):
    """Marca webhook como processado com sucesso."""
    supabase.table("webhook_dlq").update({
        "status": "processed",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", dlq_id).execute()

    logger.info(f"[DLQ] Webhook processado: {dlq_id}")


async def marcar_falha_permanente(dlq_id: str, erro: str):
    """Marca webhook como falha permanente."""
    supabase.table("webhook_dlq").update({
        "status": "failed",
        "erro": erro,
    }).eq("id", dlq_id).execute()

    logger.error(f"[DLQ] Webhook falhou permanentemente: {dlq_id}")


async def incrementar_tentativa(dlq_id: str, erro: str) -> int:
    """
    Incrementa tentativa e atualiza erro.

    Returns:
        Nova contagem de tentativas
    """
    # Buscar atual
    result = supabase.table("webhook_dlq").select("tentativa").eq(
        "id", dlq_id
    ).single().execute()

    if not result.data:
        return 0

    nova_tentativa = result.data["tentativa"] + 1

    status = "pending" if nova_tentativa < MAX_RETRIES else "failed"

    supabase.table("webhook_dlq").update({
        "tentativa": nova_tentativa,
        "erro": erro,
        "status": status,
    }).eq("id", dlq_id).execute()

    return nova_tentativa


async def obter_estatisticas() -> Dict:
    """
    Retorna estatisticas da DLQ.

    Returns:
        {
            "pending": N,
            "processing": N,
            "processed": N,
            "failed": N,
        }
    """
    result = supabase.table("webhook_dlq").select(
        "status", count="exact"
    ).execute()

    # Contar por status
    stats = {"pending": 0, "processing": 0, "processed": 0, "failed": 0}

    # Buscar contagens individuais
    for status in ["pending", "processing", "processed", "failed"]:
        count_result = supabase.table("webhook_dlq").select(
            "id", count="exact"
        ).eq("status", status).execute()
        stats[status] = count_result.count or 0

    return stats
