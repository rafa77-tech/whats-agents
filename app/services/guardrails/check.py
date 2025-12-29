"""
Verificação de guardrails para outbound.

Sprint 17 - Ponto único de controle para envios proativos.

Regras (em ordem de precedência):
R0 - opted_out é absoluto (exceto bypass humano via Slack/API)
R1 - cooling_off bloqueia proativo
R2 - next_allowed_at bloqueia proativo
R3 - contact_cap_7d bloqueia proativo
R4 - kill switches (campaigns.enabled, safe_mode)

Toda decisão BLOCK ou BYPASS gera business_event para auditoria.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.policy.repository import load_doctor_state
from app.services.policy.flags import get_campaigns_flags, is_safe_mode_active
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event

from .types import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    GuardrailDecision,
    GuardrailResult,
)

logger = logging.getLogger(__name__)

# Default: 5 contatos em 7 dias
# TODO: mover para feature_flags.guardrails.contact_cap_7d
CONTACT_CAP_7D_DEFAULT = 5


def _is_human_slack_override(ctx: OutboundContext) -> bool:
    """
    Verifica se é um override humano via Slack/API.

    Bypass permitido apenas quando:
    - actor_type == HUMAN
    - channel in {SLACK, API}
    - method in {BUTTON, COMMAND, MANUAL}
    """
    return (
        ctx.actor_type == ActorType.HUMAN
        and ctx.channel in {OutboundChannel.SLACK, OutboundChannel.API}
        and ctx.method in {OutboundMethod.BUTTON, OutboundMethod.COMMAND, OutboundMethod.MANUAL}
    )


async def _emit_guardrail_event(
    ctx: OutboundContext,
    result: GuardrailResult,
    event_type: str,
) -> None:
    """
    Emite business_event para bloqueio ou bypass.

    Args:
        ctx: Contexto do envio
        result: Resultado do guardrail
        event_type: "outbound_blocked" ou "outbound_bypass"
    """
    # Construir dedupe_key para idempotência
    dedupe = f"{event_type}:{ctx.cliente_id}:{result.reason_code}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"

    event = BusinessEvent(
        event_type=EventType.OUTBOUND_BLOCKED if event_type == "outbound_blocked" else EventType.OUTBOUND_BYPASS,
        source=EventSource.BACKEND,
        cliente_id=ctx.cliente_id,
        conversation_id=ctx.conversation_id,
        dedupe_key=dedupe,
        event_props={
            "channel": ctx.channel.value,
            "method": ctx.method.value,
            "actor_type": ctx.actor_type.value,
            "actor_id": ctx.actor_id,
            "is_proactive": ctx.is_proactive,
            "campaign_id": ctx.campaign_id,
            "policy_decision_id": ctx.policy_decision_id,
            "block_reason": result.reason_code,
            "human_bypass": result.human_bypass,
            "details": result.details or {},
        },
    )

    await emit_event(event)


async def check_outbound_guardrails(ctx: OutboundContext) -> GuardrailResult:
    """
    Verifica guardrails para envio outbound.

    Este é o ponto único de controle que DEVE ser chamado antes de
    qualquer envio via Evolution API.

    Args:
        ctx: Contexto completo do envio

    Returns:
        GuardrailResult com decisão ALLOW ou BLOCK

    Regras aplicadas (em ordem):
    1. opted_out → BLOCK (exceto human override)
    2. cooling_off ativo → BLOCK proativo (exceto human override)
    3. next_allowed_at futuro → BLOCK proativo (exceto human override)
    4. contact_cap_7d excedido → BLOCK proativo (exceto human override)
    5. campaigns.enabled=false → BLOCK campaigns
    6. safe_mode ativo → BLOCK proativo
    """
    state = await load_doctor_state(ctx.cliente_id)
    now = datetime.now(timezone.utc)

    # R0: opted_out é absoluto
    if state and state.permission_state.value == "opted_out":
        if _is_human_slack_override(ctx):
            result = GuardrailResult(
                decision=GuardrailDecision.ALLOW,
                reason_code="opted_out",
                human_bypass=True,
                details={"warning": "Bypass humano em opted_out"}
            )
            await _emit_guardrail_event(ctx, result, "outbound_bypass")
            logger.warning(f"BYPASS opted_out: {ctx.cliente_id} por {ctx.actor_id}")
            return result

        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="opted_out"
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK opted_out: {ctx.cliente_id}")
        return result

    # Regras R1-R4 só travam proativo
    if not ctx.is_proactive:
        return GuardrailResult(
            decision=GuardrailDecision.ALLOW,
            reason_code="non_proactive"
        )

    # R1: cooling_off bloqueia proativo
    if state and state.permission_state.value == "cooling_off":
        if state.cooling_off_until and now < state.cooling_off_until:
            if _is_human_slack_override(ctx):
                result = GuardrailResult(
                    decision=GuardrailDecision.ALLOW,
                    reason_code="cooling_off",
                    human_bypass=True,
                    details={"until": state.cooling_off_until.isoformat()}
                )
                await _emit_guardrail_event(ctx, result, "outbound_bypass")
                logger.warning(f"BYPASS cooling_off: {ctx.cliente_id} por {ctx.actor_id}")
                return result

            result = GuardrailResult(
                decision=GuardrailDecision.BLOCK,
                reason_code="cooling_off",
                details={"until": state.cooling_off_until.isoformat()}
            )
            await _emit_guardrail_event(ctx, result, "outbound_blocked")
            logger.info(f"BLOCK cooling_off: {ctx.cliente_id} até {state.cooling_off_until}")
            return result

    # R2: next_allowed_at bloqueia proativo
    if state and state.next_allowed_at and now < state.next_allowed_at:
        if _is_human_slack_override(ctx):
            result = GuardrailResult(
                decision=GuardrailDecision.ALLOW,
                reason_code="next_allowed_at",
                human_bypass=True,
                details={"next_allowed_at": state.next_allowed_at.isoformat()}
            )
            await _emit_guardrail_event(ctx, result, "outbound_bypass")
            logger.warning(f"BYPASS next_allowed_at: {ctx.cliente_id} por {ctx.actor_id}")
            return result

        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="next_allowed_at",
            details={"next_allowed_at": state.next_allowed_at.isoformat()}
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK next_allowed_at: {ctx.cliente_id} até {state.next_allowed_at}")
        return result

    # R3: contact_cap_7d bloqueia proativo
    contact_cap = CONTACT_CAP_7D_DEFAULT  # TODO: puxar de feature_flags
    if state and state.contact_count_7d >= contact_cap:
        if _is_human_slack_override(ctx):
            result = GuardrailResult(
                decision=GuardrailDecision.ALLOW,
                reason_code="contact_cap",
                human_bypass=True,
                details={"cap": contact_cap, "count": state.contact_count_7d}
            )
            await _emit_guardrail_event(ctx, result, "outbound_bypass")
            logger.warning(f"BYPASS contact_cap: {ctx.cliente_id} por {ctx.actor_id}")
            return result

        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="contact_cap",
            details={"cap": contact_cap, "count": state.contact_count_7d}
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK contact_cap: {ctx.cliente_id} ({state.contact_count_7d}/{contact_cap})")
        return result

    # R4a: kill switch de campanhas
    if ctx.method == OutboundMethod.CAMPAIGN:
        campaigns_flags = await get_campaigns_flags()
        if not campaigns_flags.enabled:
            result = GuardrailResult(
                decision=GuardrailDecision.BLOCK,
                reason_code="campaigns_disabled"
            )
            await _emit_guardrail_event(ctx, result, "outbound_blocked")
            logger.info(f"BLOCK campaigns_disabled: {ctx.cliente_id}")
            return result

    # R4b: safe_mode bloqueia todo proativo
    if await is_safe_mode_active():
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="safe_mode"
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK safe_mode: {ctx.cliente_id}")
        return result

    # Passou por todos os guardrails
    return GuardrailResult(
        decision=GuardrailDecision.ALLOW,
        reason_code="ok"
    )
