"""
Ponto único de envio de mensagens outbound.

Sprint 17 - Todas as mensagens outbound DEVEM passar por aqui.
Sprint 18.1 - C1: Deduplicação de mensagens outbound.
Sprint 23 E01 - Outcome detalhado com enum padronizado.

Este módulo é o wrapper que:
1. Verifica deduplicação (evita duplicatas em retry/timeout)
2. Verifica guardrails antes de enviar
3. Chama Evolution API se permitido
4. Emite eventos de auditoria
5. Retorna outcome detalhado para rastreamento

IMPORTANTE: Nenhum outro código deve chamar evolution.enviar_mensagem() diretamente.
Use sempre send_outbound_message() deste módulo.
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.services.guardrails import (
    OutboundContext,
    OutboundChannel,
    OutboundMethod,
    ActorType,
    GuardrailResult,
    SendOutcome,
    map_guardrail_to_outcome,
    check_outbound_guardrails,
)
from app.services.whatsapp import (
    evolution,
    RateLimitError,
    enviar_com_digitacao,
)
from app.services.circuit_breaker import CircuitOpenError
from app.services.outbound_dedupe import (
    verificar_e_reservar,
    marcar_enviado,
    marcar_falha,
)

logger = logging.getLogger(__name__)


def _gerar_content_hash(texto: str) -> str:
    """Gera hash do conteúdo para deduplicação."""
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


@dataclass
class OutboundResult:
    """
    Resultado do envio outbound.

    Sprint 23 E01 - Campos padronizados para rastreamento completo.

    Attributes:
        success: True se mensagem foi enviada com sucesso
        outcome: Enum com resultado detalhado (SENT, BLOCKED_*, DEDUPED, FAILED_*)
        outcome_reason_code: Codigo detalhado do motivo
        outcome_at: Timestamp de quando o outcome foi determinado
        blocked: True APENAS para guardrails (BLOCKED_*)
        deduped: True para deduplicacao (DEDUPED)
        human_bypass: True quando liberou por override humano
        provider_message_id: ID da mensagem no Evolution API quando SENT
        dedupe_key: Chave de deduplicacao usada
        error: Mensagem de erro quando FAILED_*
        evolution_response: Resposta completa do Evolution API
    """
    success: bool
    outcome: SendOutcome
    outcome_reason_code: Optional[str] = None
    outcome_at: Optional[datetime] = None
    blocked: bool = False  # True APENAS para guardrails
    deduped: bool = False  # True para deduplicacao (NAO e blocked)
    human_bypass: bool = False
    provider_message_id: Optional[str] = None
    dedupe_key: Optional[str] = None
    error: Optional[str] = None
    evolution_response: Optional[dict] = None

    # Alias para compatibilidade (deprecated)
    @property
    def block_reason(self) -> Optional[str]:
        """Alias para outcome_reason_code (deprecated)."""
        return self.outcome_reason_code


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

    Sprint 23 E01: Ordem de verificacao alterada:
    1. Deduplicacao ANTES de guardrails (DEDUPED != BLOCKED)
    2. Guardrails
    3. Envio via Evolution API
    4. Retorno de outcome detalhado

    Args:
        telefone: Número do destinatário (5511999999999)
        texto: Texto da mensagem
        ctx: Contexto completo do envio (obrigatório)
        simular_digitacao: Se True, mostra "digitando" antes de enviar
        tempo_digitacao: Tempo de digitação em segundos (opcional)

    Returns:
        OutboundResult com outcome detalhado (SENT, BLOCKED_*, DEDUPED, FAILED_*)

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
        if result.outcome.is_blocked:
            logger.info(f"Bloqueado: {result.outcome_reason_code}")
        elif result.outcome.is_deduped:
            logger.info(f"Deduplicado: {result.outcome_reason_code}")
        ```
    """
    now = datetime.now(timezone.utc)

    # 1. Verificar deduplicação ANTES de guardrails (Sprint 23 E01)
    # Deduplicacao NAO e bloqueio por permissao - e protecao anti-spam
    content_hash = _gerar_content_hash(texto)
    pode_enviar, dedupe_key, motivo = await verificar_e_reservar(
        cliente_id=ctx.cliente_id,
        method=ctx.method.value if ctx.method else "manual",
        conversation_id=ctx.conversation_id,
        content_hash=content_hash,
    )

    if not pode_enviar:
        logger.info(
            f"Outbound deduped para {telefone[:8]}...: {motivo}",
            extra={
                "event": "outbound_deduped",
                "dedupe_key": dedupe_key,
                "cliente_id": ctx.cliente_id,
                "method": ctx.method.value if ctx.method else "manual",
            }
        )
        return OutboundResult(
            success=False,
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code=f"content_hash_window:{motivo}",
            outcome_at=now,
            blocked=False,  # NAO e bloqueio
            deduped=True,   # E deduplicacao
            dedupe_key=dedupe_key,
        )

    # 2. Verificar guardrails
    guardrail_result = await check_outbound_guardrails(ctx)

    if guardrail_result.is_blocked:
        logger.info(
            f"Outbound bloqueado para {telefone[:8]}...: "
            f"{guardrail_result.reason_code}"
        )
        try:
            outcome = map_guardrail_to_outcome(guardrail_result.reason_code)
        except ValueError:
            outcome = SendOutcome.BLOCKED_OPTED_OUT  # fallback seguro
            logger.warning(f"reason_code nao mapeado: {guardrail_result.reason_code}")

        return OutboundResult(
            success=False,
            outcome=outcome,
            outcome_reason_code=guardrail_result.reason_code,
            outcome_at=now,
            blocked=True,
            deduped=False,
            dedupe_key=dedupe_key,
        )

    # Log de bypass (se houver)
    if guardrail_result.human_bypass:
        logger.warning(
            f"Outbound com bypass humano para {telefone[:8]}...: "
            f"{guardrail_result.reason_code} por {ctx.actor_id}"
        )

    # 3. Enviar via Evolution API
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

        # Marcar dedupe como enviado com sucesso
        await marcar_enviado(dedupe_key)

        # Extrair provider_message_id da resposta
        provider_message_id = None
        if response and isinstance(response, dict):
            # Evolution API retorna key.id como message id
            key = response.get("key", {})
            provider_message_id = key.get("id") if isinstance(key, dict) else None

        # Sprint 23 E02: Registrar touch de campanha para atribuição
        if ctx.campaign_id and ctx.conversation_id:
            from app.services.campaign_attribution import registrar_campaign_touch
            await registrar_campaign_touch(
                conversation_id=ctx.conversation_id,
                campaign_id=int(ctx.campaign_id),
                touch_type=ctx.method.value if ctx.method else "campaign",
                cliente_id=ctx.cliente_id,
            )

        return OutboundResult(
            success=True,
            outcome=SendOutcome.BYPASS if guardrail_result.human_bypass else SendOutcome.SENT,
            outcome_reason_code="ok" if not guardrail_result.human_bypass else guardrail_result.reason_code,
            outcome_at=now,
            blocked=False,
            deduped=False,
            human_bypass=guardrail_result.human_bypass,
            provider_message_id=provider_message_id,
            dedupe_key=dedupe_key,
            evolution_response=response,
        )

    except RateLimitError as e:
        logger.warning(f"Rate limit ao enviar para {telefone[:8]}...: {e}")
        await marcar_falha(dedupe_key, f"rate_limit: {e}")
        return OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_RATE_LIMIT,
            outcome_reason_code=f"rate_limit:{str(e)[:100]}",
            outcome_at=now,
            blocked=False,
            deduped=False,
            dedupe_key=dedupe_key,
            error=str(e),
        )

    except CircuitOpenError as e:
        logger.error(f"Circuit open ao enviar para {telefone[:8]}...: {e}")
        await marcar_falha(dedupe_key, f"circuit_open: {e}")
        return OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_CIRCUIT_OPEN,
            outcome_reason_code=f"circuit_open:{str(e)[:100]}",
            outcome_at=now,
            blocked=False,
            deduped=False,
            dedupe_key=dedupe_key,
            error=f"Evolution API indisponível: {e}",
        )

    except Exception as e:
        logger.error(f"Erro ao enviar para {telefone[:8]}...: {e}")
        await marcar_falha(dedupe_key, str(e)[:200])
        return OutboundResult(
            success=False,
            outcome=SendOutcome.FAILED_PROVIDER,
            outcome_reason_code=f"provider_error:{str(e)[:100]}",
            outcome_at=now,
            blocked=False,
            deduped=False,
            dedupe_key=dedupe_key,
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
