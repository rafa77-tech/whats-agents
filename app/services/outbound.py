"""
Ponto único de envio de mensagens outbound.

Sprint 17 - Todas as mensagens outbound DEVEM passar por aqui.

Este módulo é o wrapper que:
1. Verifica guardrails antes de enviar
2. Chama Evolution API se permitido
3. Emite eventos de auditoria

IMPORTANTE: Nenhum outro código deve chamar evolution.enviar_mensagem() diretamente.
Use sempre send_outbound_message() deste módulo.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    GuardrailResult,
    check_outbound_guardrails,
)
from app.services.whatsapp import (
    evolution,
    RateLimitError,
    enviar_com_digitacao,
)
from app.services.circuit_breaker import CircuitOpenError

logger = logging.getLogger(__name__)


@dataclass
class OutboundResult:
    """Resultado do envio outbound."""
    success: bool
    blocked: bool = False
    block_reason: Optional[str] = None
    human_bypass: bool = False
    error: Optional[str] = None
    evolution_response: Optional[dict] = None


async def send_outbound_message(
    telefone: str,
    texto: str,
    ctx: OutboundContext,
    simular_digitacao: bool = False,
    tempo_digitacao: Optional[float] = None,
) -> OutboundResult:
    """
    Envia mensagem outbound com verificação de guardrails.

    Este é o ÚNICO ponto de entrada para enviar mensagens via WhatsApp.
    Todas as campanhas, followups, reativações e respostas devem usar esta função.

    Args:
        telefone: Número do destinatário (5511999999999)
        texto: Texto da mensagem
        ctx: Contexto completo do envio (obrigatório)
        simular_digitacao: Se True, mostra "digitando" antes de enviar
        tempo_digitacao: Tempo de digitação em segundos (opcional)

    Returns:
        OutboundResult com status do envio

    Exemplo de uso:
        ```python
        ctx = OutboundContext(
            cliente_id=medico_id,
            actor_type=ActorType.SYSTEM,
            channel=OutboundChannel.JOB,
            method=OutboundMethod.CAMPAIGN,
            is_proactive=True,
            campaign_id=campanha_id,
        )
        result = await send_outbound_message(telefone, texto, ctx)
        if result.blocked:
            logger.info(f"Bloqueado: {result.block_reason}")
        ```
    """
    # 1. Verificar guardrails
    guardrail_result = await check_outbound_guardrails(ctx)

    if guardrail_result.is_blocked:
        logger.info(
            f"Outbound bloqueado para {telefone[:8]}...: "
            f"{guardrail_result.reason_code}"
        )
        return OutboundResult(
            success=False,
            blocked=True,
            block_reason=guardrail_result.reason_code,
        )

    # Log de bypass (se houver)
    if guardrail_result.human_bypass:
        logger.warning(
            f"Outbound com bypass humano para {telefone[:8]}...: "
            f"{guardrail_result.reason_code} por {ctx.actor_id}"
        )

    # 2. Enviar via Evolution API
    try:
        if simular_digitacao:
            response = await enviar_com_digitacao(
                telefone=telefone,
                texto=texto,
                tempo_digitacao=tempo_digitacao,
            )
        else:
            # Verificar rate limit apenas para proativo
            response = await evolution.enviar_mensagem(
                telefone=telefone,
                texto=texto,
                verificar_rate_limit=ctx.is_proactive,
            )

        return OutboundResult(
            success=True,
            blocked=False,
            human_bypass=guardrail_result.human_bypass,
            evolution_response=response,
        )

    except RateLimitError as e:
        logger.warning(f"Rate limit ao enviar para {telefone[:8]}...: {e}")
        return OutboundResult(
            success=False,
            blocked=True,
            block_reason="rate_limit",
            error=str(e),
        )

    except CircuitOpenError as e:
        logger.error(f"Circuit open ao enviar para {telefone[:8]}...: {e}")
        return OutboundResult(
            success=False,
            error=f"Evolution API indisponível: {e}",
        )

    except Exception as e:
        logger.error(f"Erro ao enviar para {telefone[:8]}...: {e}")
        return OutboundResult(
            success=False,
            error=str(e),
        )


# Helpers para criar contexto facilmente

def criar_contexto_campanha(
    cliente_id: str,
    campaign_id: str,
    conversation_id: Optional[str] = None,
) -> OutboundContext:
    """Cria contexto para envio de campanha."""
    return OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.SYSTEM,
        channel=OutboundChannel.JOB,
        method=OutboundMethod.CAMPAIGN,
        is_proactive=True,
        campaign_id=campaign_id,
        conversation_id=conversation_id,
    )


def criar_contexto_followup(
    cliente_id: str,
    conversation_id: Optional[str] = None,
    policy_decision_id: Optional[str] = None,
) -> OutboundContext:
    """Cria contexto para followup automático."""
    return OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.FOLLOWUP,
        is_proactive=True,
        conversation_id=conversation_id,
        policy_decision_id=policy_decision_id,
    )


def criar_contexto_reativacao(
    cliente_id: str,
    conversation_id: Optional[str] = None,
) -> OutboundContext:
    """Cria contexto para reativação de médico inativo."""
    return OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REACTIVATION,
        is_proactive=True,
        conversation_id=conversation_id,
    )


def criar_contexto_reply(
    cliente_id: str,
    conversation_id: str,
    inbound_interaction_id: int,
    last_inbound_at: str,
    policy_decision_id: Optional[str] = None,
) -> OutboundContext:
    """
    Cria contexto para resposta a mensagem inbound.

    IMPORTANTE: Reply requer prova de inbound!
    - inbound_interaction_id: ID da interação que originou a resposta
    - last_inbound_at: Timestamp ISO da última mensagem do médico
    - Sem esses campos, guardrail trata como proativo
    """
    return OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.BOT,
        channel=OutboundChannel.WHATSAPP,
        method=OutboundMethod.REPLY,
        is_proactive=False,  # Reply não é proativo
        conversation_id=conversation_id,
        policy_decision_id=policy_decision_id,
        inbound_interaction_id=inbound_interaction_id,
        last_inbound_at=last_inbound_at,
    )


def criar_contexto_manual_slack(
    cliente_id: str,
    actor_id: str,
    bypass_reason: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> OutboundContext:
    """
    Cria contexto para envio manual via Slack.

    IMPORTANTE para opted_out:
    - bypass_reason é OBRIGATÓRIO para contactar médico opted_out
    - Sem bypass_reason, guardrail bloqueia mesmo com humano
    """
    return OutboundContext(
        cliente_id=cliente_id,
        actor_type=ActorType.HUMAN,
        channel=OutboundChannel.SLACK,
        method=OutboundMethod.COMMAND,
        is_proactive=True,
        actor_id=actor_id,
        conversation_id=conversation_id,
        bypass_reason=bypass_reason,
    )
