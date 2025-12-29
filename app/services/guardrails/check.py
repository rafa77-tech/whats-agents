"""
Verificação de guardrails para outbound.

Sprint 17 - Ponto único de controle para envios proativos.

Regras (em ordem de precedência):
R-1 - Reply só é válido com inbound_proof (interaction_id + last_inbound recente)
R0  - opted_out é absoluto (exceto bypass humano via Slack COM bypass_reason)
R1  - cooling_off bloqueia proativo
R2  - next_allowed_at bloqueia proativo
R3  - contact_cap_7d bloqueia proativo
R4  - kill switches (campaigns.enabled, safe_mode)

Toda decisão BLOCK ou BYPASS gera business_event para auditoria.
"""
import logging
from datetime import datetime, timezone, timedelta
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

# Configurações
CONTACT_CAP_7D_DEFAULT = 5      # Máximo de contatos em 7 dias
REPLY_WINDOW_MINUTES = 30       # Janela máxima para considerar reply válido
PROVIDER = "evolution"          # Provider atual (para auditoria)


def _has_valid_inbound_proof(ctx: OutboundContext) -> bool:
    """
    Verifica se o contexto tem prova válida de inbound.

    Reply só é válido se:
    1. inbound_interaction_id está presente
    2. last_inbound_at é recente (dentro da janela)
    3. conversation_id está presente

    Sem isso, não é reply legítimo - cai nas regras como proativo.
    """
    if not ctx.inbound_interaction_id:
        return False

    if not ctx.conversation_id:
        return False

    if not ctx.last_inbound_at:
        return False

    # Verificar se last_inbound_at é recente
    try:
        # Parse ISO timestamp
        last_inbound = datetime.fromisoformat(ctx.last_inbound_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - last_inbound

        if delta > timedelta(minutes=REPLY_WINDOW_MINUTES):
            logger.warning(
                f"Inbound muito antigo para reply: {delta.total_seconds()/60:.1f}min "
                f"(max {REPLY_WINDOW_MINUTES}min)"
            )
            return False

        return True

    except (ValueError, TypeError) as e:
        logger.warning(f"last_inbound_at inválido: {ctx.last_inbound_at} - {e}")
        return False


def _is_human_slack_bypass(ctx: OutboundContext) -> bool:
    """
    Verifica se é um bypass humano legítimo via Slack.

    Bypass permitido APENAS quando:
    - actor_type == HUMAN
    - channel == SLACK (não API, não outros)
    - method in {BUTTON, COMMAND, MANUAL}
    - actor_id está presente (quem autorizou)
    """
    return (
        ctx.actor_type == ActorType.HUMAN
        and ctx.channel == OutboundChannel.SLACK  # APENAS Slack
        and ctx.method in {OutboundMethod.BUTTON, OutboundMethod.COMMAND, OutboundMethod.MANUAL}
        and ctx.actor_id is not None  # Quem autorizou é obrigatório
    )


def _validate_event_integrity(
    ctx: OutboundContext,
    result: GuardrailResult,
    is_bypass: bool,
) -> list[str]:
    """
    Valida as 6 regras de integridade do evento.

    Retorna lista de warnings (não bloqueia emissão, mas loga).

    Regras:
    1. bypassed=false ⇒ bypass_reason deve ser null
    2. bypassed=true ⇒ actor_type=human, channel in (slack,api), bypass_reason obrigatório
    3. method=reply ⇒ conversation_id e inbound_interaction_id obrigatórios
    4. Se veio do policy engine, policy_decision_id deve estar preenchido
    5. is_proactive=true ⇒ method != reply
    6. details nunca pode carregar PII
    """
    warnings = []

    # R1: bypassed=false ⇒ bypass_reason null
    if not is_bypass and ctx.bypass_reason:
        warnings.append(f"R1: bypassed=false mas bypass_reason='{ctx.bypass_reason}'")

    # R2: bypassed=true ⇒ human + slack/api + bypass_reason
    if is_bypass:
        if ctx.actor_type != ActorType.HUMAN:
            warnings.append(f"R2: bypassed=true mas actor_type={ctx.actor_type.value}")
        if ctx.channel not in (OutboundChannel.SLACK, OutboundChannel.API):
            warnings.append(f"R2: bypassed=true mas channel={ctx.channel.value}")
        if not ctx.bypass_reason:
            warnings.append("R2: bypassed=true mas bypass_reason vazio")

    # R3: method=reply ⇒ conversation_id + inbound_interaction_id
    if ctx.method == OutboundMethod.REPLY:
        if not ctx.conversation_id:
            warnings.append("R3: method=reply mas conversation_id null")
        if not ctx.inbound_interaction_id:
            warnings.append("R3: method=reply mas inbound_interaction_id null")

    # R4: Se tem decision_id no contexto, deve estar preenchido (não validamos aqui, só log)
    # (Esta regra é mais para auditoria posterior)

    # R5: is_proactive=true ⇒ method != reply
    if ctx.is_proactive and ctx.method == OutboundMethod.REPLY:
        warnings.append("R5: is_proactive=true mas method=reply (contraditório)")

    # R6: details sem PII (validamos no details do result)
    if result.details:
        pii_keys = {"telefone", "texto", "mensagem", "conteudo", "phone", "message"}
        found_pii = set(result.details.keys()) & pii_keys
        if found_pii:
            warnings.append(f"R6: details contém possível PII: {found_pii}")

    return warnings


async def _emit_guardrail_event(
    ctx: OutboundContext,
    result: GuardrailResult,
    event_type: str,
) -> None:
    """
    Emite business_event para bloqueio ou bypass.

    Contrato inviolável - campos top-level:
    - event_type, ts, cliente_id, conversation_id, policy_decision_id, event_props

    event_props sempre contém:
    - provider, channel, method, actor_type, actor_id, is_proactive
    - campaign_id, inbound_interaction_id
    - block_reason, bypassed, bypass_reason, details
    """
    is_bypass = event_type == "outbound_bypass"

    # Validar integridade (log warnings, não bloqueia)
    warnings = _validate_event_integrity(ctx, result, is_bypass)
    for w in warnings:
        logger.warning(f"INTEGRITY_WARNING: {w} cliente={ctx.cliente_id}")

    # Construir dedupe_key: cliente + reason + janela 5min
    ts_bucket = datetime.now(timezone.utc).strftime('%Y%m%d%H%M')[:11]
    dedupe = f"{event_type}:{ctx.cliente_id}:{result.reason_code}:{ts_bucket}"

    event = BusinessEvent(
        event_type=EventType.OUTBOUND_BYPASS if is_bypass else EventType.OUTBOUND_BLOCKED,
        source=EventSource.BACKEND,
        cliente_id=ctx.cliente_id,
        conversation_id=ctx.conversation_id,
        policy_decision_id=ctx.policy_decision_id,
        dedupe_key=dedupe,
        event_props={
            # Rastreio de origem
            "provider": PROVIDER,
            "channel": ctx.channel.value,
            "method": ctx.method.value,
            "actor_type": ctx.actor_type.value,
            "actor_id": ctx.actor_id,
            "is_proactive": ctx.is_proactive,
            # Contexto adicional
            "campaign_id": ctx.campaign_id,
            "inbound_interaction_id": ctx.inbound_interaction_id,
            # Resultado padronizado
            "block_reason": result.reason_code,
            "bypassed": is_bypass,
            "bypass_reason": ctx.bypass_reason if is_bypass else None,
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
    R-1: Reply requer inbound_proof válido
    R0:  opted_out → BLOCK (exceto bypass Slack COM reason)
    R1:  cooling_off ativo → BLOCK proativo
    R2:  next_allowed_at futuro → BLOCK proativo
    R3:  contact_cap_7d excedido → BLOCK proativo
    R4a: campaigns.enabled=false → BLOCK campaigns
    R4b: safe_mode ativo → BLOCK proativo
    """
    state = await load_doctor_state(ctx.cliente_id)
    now = datetime.now(timezone.utc)

    # =========================================================================
    # R-1: Validação de REPLY - deve ter inbound_proof
    # =========================================================================
    # Se method=REPLY mas não tem prova válida de inbound,
    # tratamos como proativo (cai nas regras R0-R4)
    is_valid_reply = False
    if ctx.method == OutboundMethod.REPLY:
        if _has_valid_inbound_proof(ctx):
            is_valid_reply = True
            logger.debug(f"Reply válido para {ctx.cliente_id}: interaction={ctx.inbound_interaction_id}")
        else:
            logger.warning(
                f"Reply sem inbound_proof válido para {ctx.cliente_id}: "
                f"tratando como proativo"
            )

    # Determinar se é realmente proativo
    # Reply válido NÃO é proativo; reply sem prova É proativo
    is_actually_proactive = ctx.is_proactive or (ctx.method == OutboundMethod.REPLY and not is_valid_reply)

    # =========================================================================
    # R0: opted_out é absoluto
    # =========================================================================
    if state and state.permission_state.value == "opted_out":
        # Reply válido PODE responder mesmo com opted_out
        # (médico iniciou contato, podemos responder)
        if is_valid_reply:
            logger.info(f"ALLOW reply para opted_out {ctx.cliente_id} (médico iniciou contato)")
            return GuardrailResult(
                decision=GuardrailDecision.ALLOW,
                reason_code="reply_to_opted_out",
                details={"inbound_interaction_id": ctx.inbound_interaction_id}
            )

        # Bypass humano via Slack COM bypass_reason
        if _is_human_slack_bypass(ctx):
            if not ctx.bypass_reason:
                logger.warning(f"Bypass opted_out negado: bypass_reason obrigatório")
                result = GuardrailResult(
                    decision=GuardrailDecision.BLOCK,
                    reason_code="opted_out_bypass_no_reason",
                    details={"error": "bypass_reason obrigatório para opted_out"}
                )
                await _emit_guardrail_event(ctx, result, "outbound_blocked")
                return result

            result = GuardrailResult(
                decision=GuardrailDecision.ALLOW,
                reason_code="opted_out",
                human_bypass=True,
                details={
                    "bypass_reason": ctx.bypass_reason,
                    "authorized_by": ctx.actor_id,
                }
            )
            await _emit_guardrail_event(ctx, result, "outbound_bypass")
            logger.warning(f"BYPASS opted_out: {ctx.cliente_id} por {ctx.actor_id} motivo='{ctx.bypass_reason}'")
            return result

        # Bloqueia
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="opted_out"
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK opted_out: {ctx.cliente_id}")
        return result

    # =========================================================================
    # Regras R1-R4 só travam proativo
    # =========================================================================
    if not is_actually_proactive:
        return GuardrailResult(
            decision=GuardrailDecision.ALLOW,
            reason_code="reply_valid" if is_valid_reply else "non_proactive"
        )

    # =========================================================================
    # R1: cooling_off bloqueia proativo
    # =========================================================================
    if state and state.permission_state.value == "cooling_off":
        if state.cooling_off_until and now < state.cooling_off_until:
            if _is_human_slack_bypass(ctx):
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

    # =========================================================================
    # R2: next_allowed_at bloqueia proativo
    # =========================================================================
    if state and state.next_allowed_at and now < state.next_allowed_at:
        if _is_human_slack_bypass(ctx):
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

    # =========================================================================
    # R3: contact_cap_7d bloqueia proativo
    # =========================================================================
    contact_cap = CONTACT_CAP_7D_DEFAULT  # TODO: puxar de feature_flags
    if state and state.contact_count_7d >= contact_cap:
        if _is_human_slack_bypass(ctx):
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

    # =========================================================================
    # R4a: kill switch de campanhas
    # =========================================================================
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

    # =========================================================================
    # R4b: safe_mode bloqueia todo proativo
    # =========================================================================
    if await is_safe_mode_active():
        result = GuardrailResult(
            decision=GuardrailDecision.BLOCK,
            reason_code="safe_mode"
        )
        await _emit_guardrail_event(ctx, result, "outbound_blocked")
        logger.info(f"BLOCK safe_mode: {ctx.cliente_id}")
        return result

    # =========================================================================
    # Passou por todos os guardrails
    # =========================================================================
    return GuardrailResult(
        decision=GuardrailDecision.ALLOW,
        reason_code="ok"
    )
