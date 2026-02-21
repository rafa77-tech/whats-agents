"""
Envio outbound de mensagens interativas.

Sprint 67 (R2, Chunk 7a).

Função send_outbound_interactive() é o ponto de entrada para
envio de mensagens interativas (botões, listas, CTA).

Segue o mesmo padrão de send_outbound_message():
DEV allowlist → dedup → guardrails → multi-chip → finalization.

Diferença: se chip não é Meta ou fora da janela, envia fallback_text.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.guardrails import (
    OutboundContext,
    OutboundMethod,
    OutboundChannel,
    ActorType,
    SendOutcome,
    map_guardrail_to_outcome,
    check_outbound_guardrails,
)
from app.services.outbound_dedupe import (
    verificar_e_reservar,
    marcar_enviado,
    marcar_falha,
)
from app.services.outbound.types import OutboundResult
from app.services.outbound.dev_guardrails import _verificar_dev_allowlist

logger = logging.getLogger(__name__)


async def send_outbound_interactive(
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
    conversa_id: Optional[str] = None,
) -> OutboundResult:
    """
    Envia mensagem interativa outbound.

    Se chip Meta + dentro da janela: envia interactive
    Se chip não-Meta ou fora da janela: envia fallback_text
    Se nenhum chip disponível: retorna NO_CAPACITY

    Args:
        telefone: Número do destinatário
        interactive_payload: Payload interativo (type=button|list|cta_url)
        fallback_text: Texto de fallback para chips não-Meta
        conversa_id: ID da conversa (opcional)

    Returns:
        OutboundResult com outcome.
    """
    now = datetime.now(timezone.utc)

    # 0. DEV allowlist
    pode_enviar_dev, reason_dev = _verificar_dev_allowlist(telefone)
    if not pode_enviar_dev:
        return OutboundResult(
            success=False,
            outcome=SendOutcome.BLOCKED_DEV_ALLOWLIST,
            outcome_reason_code=reason_dev,
            outcome_at=now,
            blocked=True,
            deduped=False,
        )

    # 1. Dedup (usa hash do fallback_text)
    content_hash = hashlib.sha256(fallback_text.encode()).hexdigest()[:16]
    ctx = OutboundContext(
        cliente_id=telefone,
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        conversation_id=conversa_id,
        is_proactive=False,
    )

    pode_enviar, dedupe_key, motivo = await verificar_e_reservar(
        cliente_id=telefone,
        method="interactive",
        conversation_id=conversa_id,
        content_hash=content_hash,
    )

    if not pode_enviar:
        return OutboundResult(
            success=False,
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code=f"content_hash_window:{motivo}",
            outcome_at=now,
            blocked=False,
            deduped=True,
            dedupe_key=dedupe_key,
        )

    # 2. Guardrails
    guardrail_result = await check_outbound_guardrails(ctx)
    if guardrail_result.is_blocked:
        try:
            outcome = map_guardrail_to_outcome(guardrail_result.reason_code)
        except ValueError:
            outcome = SendOutcome.BLOCKED_OPTED_OUT
        return OutboundResult(
            success=False,
            outcome=outcome,
            outcome_reason_code=guardrail_result.reason_code,
            outcome_at=now,
            blocked=True,
            deduped=False,
            dedupe_key=dedupe_key,
        )

    # 3. Enviar via multi-chip
    result = await _enviar_interactive_via_multi_chip(
        telefone=telefone,
        interactive_payload=interactive_payload,
        fallback_text=fallback_text,
        ctx=ctx,
    )

    if result.get("fallback"):
        await marcar_falha(dedupe_key, "no_capacity")
        return OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_NO_CAPACITY,
            outcome_reason_code="no_capacity:chips_no_limite",
            outcome_at=now,
            blocked=False,
            deduped=False,
            dedupe_key=dedupe_key,
            error="Sem chip disponível",
        )

    if result.get("success"):
        await marcar_enviado(dedupe_key)
        response = result.get("response", {})
        return OutboundResult(
            success=True,
            outcome=SendOutcome.SENT,
            outcome_reason_code="ok",
            outcome_at=now,
            blocked=False,
            deduped=False,
            provider_message_id=response.get("key", {}).get("id") if response else None,
            dedupe_key=dedupe_key,
            chip_id=response.get("chip_id") if response else None,
        )

    await marcar_falha(dedupe_key, result.get("error", "unknown"))
    return OutboundResult(
        success=False,
        outcome=SendOutcome.FAILED_PROVIDER_ERROR,
        outcome_reason_code=result.get("error", "unknown"),
        outcome_at=now,
        blocked=False,
        deduped=False,
        dedupe_key=dedupe_key,
        error=result.get("error"),
    )


async def _enviar_interactive_via_multi_chip(
    telefone: str,
    interactive_payload: dict,
    fallback_text: str,
    ctx: OutboundContext,
) -> dict:
    """
    Envia interactive via multi-chip.

    Se chip Meta + na janela: send_interactive
    Se chip Meta + fora da janela: send_text(fallback_text)
    Se chip não-Meta: send_text(fallback_text)
    """
    from app.services.chips.selector import chip_selector
    from app.services.whatsapp_providers import get_provider

    chip = await chip_selector.selecionar_chip(
        tipo_mensagem="resposta",
        conversa_id=ctx.conversation_id,
        telefone_destino=telefone,
    )

    if not chip:
        return {"fallback": True}

    provider = get_provider(chip)

    # Tentar interactive apenas para chips Meta na janela
    if chip.get("provider") == "meta":
        from app.services.meta.window_tracker import window_tracker

        na_janela = await window_tracker.esta_na_janela(chip["id"], telefone)

        if na_janela:
            result = await provider.send_interactive(telefone, interactive_payload)
        else:
            # Fora da janela: enviar fallback como texto
            result = await provider.send_text(telefone, fallback_text)
    else:
        # Chip não-Meta: enviar fallback como texto
        result = await provider.send_text(telefone, fallback_text)

    if result.success:
        response = {
            "key": {"id": result.message_id},
            "provider": result.provider,
            "chip_id": chip["id"],
            "chip_telefone": chip.get("telefone"),
        }
        return {"success": True, "response": response, "fallback": False}

    return {"success": False, "error": result.error, "fallback": False}
