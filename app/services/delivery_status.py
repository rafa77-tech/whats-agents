"""
Serviço para atualização de status de entrega de mensagens.

Sprint 41 - Rastreamento de Chips e Status de Entrega.

Atualiza o delivery_status das interações quando recebemos
webhooks de DELIVERY_ACK ou READ do WhatsApp.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class DeliveryStatusResult:
    """Resultado da atualização de status de entrega."""

    atualizado: bool
    interacao_id: Optional[str] = None
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    erro: Optional[str] = None


async def atualizar_delivery_status(
    provider_message_id: str, status: str, chip_id: Optional[str] = None
) -> DeliveryStatusResult:
    """
    Atualiza o status de entrega de uma interação.

    Usa RPC do banco para garantir atomicidade e só avançar
    na progressão de status (pending -> sent -> delivered -> read).

    Args:
        provider_message_id: ID da mensagem no provider (Evolution/Z-API)
        status: Novo status ('delivered', 'read', 'failed')
        chip_id: ID do chip (opcional, para preencher se ausente)

    Returns:
        DeliveryStatusResult com resultado da operação
    """
    if not provider_message_id:
        return DeliveryStatusResult(atualizado=False, erro="provider_message_id é obrigatório")

    # Normalizar status
    status_normalizado = _normalizar_status(status)
    if not status_normalizado:
        logger.debug(f"Status ignorado: {status}")
        return DeliveryStatusResult(atualizado=False, erro=f"Status não reconhecido: {status}")

    try:
        result = supabase.rpc(
            "interacao_atualizar_delivery_status",
            {
                "p_provider_message_id": provider_message_id,
                "p_status": status_normalizado,
                "p_chip_id": chip_id,
            },
        ).execute()

        if not result.data:
            return DeliveryStatusResult(atualizado=False, erro="RPC retornou vazio")

        row = result.data[0] if isinstance(result.data, list) else result.data
        atualizado = row.get("atualizado", False)
        interacao_id = row.get("interacao_id")

        if atualizado:
            logger.debug(
                f"[DeliveryStatus] {provider_message_id[:12]}... "
                f"{row.get('status_anterior')} -> {row.get('status_novo')}"
            )
        elif interacao_id:
            logger.debug(
                f"[DeliveryStatus] {provider_message_id[:12]}... "
                f"status mantido: {row.get('status_anterior')}"
            )
        else:
            logger.debug(
                f"[DeliveryStatus] Interação não encontrada: {provider_message_id[:12]}..."
            )

        return DeliveryStatusResult(
            atualizado=atualizado,
            interacao_id=str(interacao_id) if interacao_id else None,
            status_anterior=row.get("status_anterior"),
            status_novo=row.get("status_novo"),
        )

    except Exception as e:
        logger.error(f"[DeliveryStatus] Erro ao atualizar status: {e}")
        return DeliveryStatusResult(atualizado=False, erro=str(e))


def _normalizar_status(status: str) -> Optional[str]:
    """
    Normaliza status do webhook para o formato do banco.

    Args:
        status: Status recebido do webhook

    Returns:
        Status normalizado ou None se não reconhecido
    """
    status_upper = status.upper()

    # Evolution API
    if status_upper in ("DELIVERY_ACK", "SERVER_ACK"):
        return "delivered"
    if status_upper == "READ":
        return "read"

    # Z-API
    if status_upper == "DELIVERED":
        return "delivered"
    if status_upper in ("READ", "VIEWED"):
        return "read"
    if status_upper == "PLAYED":
        return "read"  # Áudio reproduzido = lido

    # Meta Cloud API (Sprint 66)
    if status_upper in ("SENT", "ACCEPTED"):
        return "sent"

    # Erros
    if status_upper in ("FAILED", "ERROR"):
        return "failed"

    # Já no formato esperado
    if status.lower() in ("pending", "sent", "delivered", "read", "failed"):
        return status.lower()

    return None


async def atualizar_status_lote(updates: list[tuple[str, str, Optional[str]]]) -> dict:
    """
    Atualiza status de várias mensagens em lote.

    Args:
        updates: Lista de tuplas (provider_message_id, status, chip_id)

    Returns:
        Estatísticas: total, atualizados, erros
    """
    total = len(updates)
    atualizados = 0
    erros = 0

    for provider_message_id, status, chip_id in updates:
        result = await atualizar_delivery_status(
            provider_message_id=provider_message_id,
            status=status,
            chip_id=chip_id,
        )
        if result.atualizado:
            atualizados += 1
        elif result.erro:
            erros += 1

    return {
        "total": total,
        "atualizados": atualizados,
        "erros": erros,
    }
