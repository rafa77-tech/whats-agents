"""
Finalizacao centralizada de envio outbound.

Sprint 58 E04 - Extraido de outbound.py monolitico.
Sprint 24 E03 - Centraliza last_touch e atribuicao.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.guardrails import OutboundContext

from app.services.guardrails import SendOutcome

logger = logging.getLogger(__name__)


async def _atualizar_last_touch(
    cliente_id: str,
    method: str,
    campaign_id: Optional[str] = None,
) -> None:
    """
    Atualiza campos last_touch_* no doctor_state.

    Sprint 24 E03: Centralizacao do tracking de ultimo touch.
    Usado pelo guardrail campaign_cooldown (E04).

    Args:
        cliente_id: ID do cliente
        method: Metodo do envio (campaign, followup, reply, etc)
        campaign_id: ID da campanha (se aplicavel)
    """
    from app.services.supabase import supabase

    try:
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "last_touch_at": now,
            "last_touch_method": method,
        }

        # campaign_id so e setado para method=campaign
        if campaign_id:
            update_data["last_touch_campaign_id"] = campaign_id
        else:
            # Limpar campaign_id se nao for campanha
            update_data["last_touch_campaign_id"] = None

        supabase.table("doctor_state").upsert(
            {"cliente_id": cliente_id, **update_data},
            on_conflict="cliente_id",
        ).execute()

        logger.debug(
            f"Last touch atualizado: {cliente_id[:8]}... method={method}, campaign_id={campaign_id}"
        )

    except Exception as e:
        # Nao falha o envio se nao conseguir atualizar
        logger.error(f"Erro ao atualizar last_touch: {e}")


async def _finalizar_envio(
    ctx: "OutboundContext",
    outcome: "SendOutcome",
    dedupe_key: Optional[str] = None,
    provider_message_id: Optional[str] = None,
) -> None:
    """
    Finalizacao centralizada de envio outbound.

    Sprint 24 E03: Garante que todas as acoes de finalizacao
    sejam executadas, independente do outcome.

    Acoes executadas:
    - Atualizar last_touch_* no doctor_state (so para SENT/BYPASS)
    - Registrar campaign_touch para atribuicao (so para SENT/BYPASS com campaign_id)

    Args:
        ctx: Contexto do envio
        outcome: Resultado do envio (SENT, BLOCKED_*, DEDUPED, FAILED_*)
        dedupe_key: Chave de deduplicacao usada
        provider_message_id: ID da mensagem no provedor
    """
    try:
        # So atualiza last_touch para envios bem-sucedidos
        if outcome in (SendOutcome.SENT, SendOutcome.BYPASS):
            method = ctx.method.value if ctx.method else "manual"

            # Atualizar doctor_state.last_touch_*
            await _atualizar_last_touch(
                cliente_id=ctx.cliente_id,
                method=method,
                campaign_id=str(ctx.campaign_id) if ctx.campaign_id else None,
            )

            # Registrar campaign attribution
            if ctx.campaign_id and ctx.conversation_id:
                from app.services.campaign_attribution import registrar_campaign_touch

                await registrar_campaign_touch(
                    conversation_id=ctx.conversation_id,
                    campaign_id=int(ctx.campaign_id),
                    touch_type=method,
                    cliente_id=ctx.cliente_id,
                )

            # Registrar envio no historico de campanhas (legado)
            if ctx.campaign_id:
                from app.services.campaign_cooldown import registrar_envio_campanha

                await registrar_envio_campanha(
                    cliente_id=ctx.cliente_id,
                    campaign_id=int(ctx.campaign_id),
                    campaign_type=method,
                )

            logger.debug(
                f"Finalizacao completa: {ctx.cliente_id[:8]}... "
                f"outcome={outcome.value}, method={method}"
            )

    except Exception as e:
        # Nao falha o retorno se finalizacao falhar
        logger.error(f"Erro na finalizacao de envio: {e}")
