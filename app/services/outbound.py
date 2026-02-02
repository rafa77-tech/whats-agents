"""
Ponto único de envio de mensagens outbound.

Sprint 17 - Todas as mensagens outbound DEVEM passar por aqui.
Sprint 18.1 - C1: Deduplicação de mensagens outbound.
Sprint 23 E01 - Outcome detalhado com enum padronizado.
Sprint 24 E03 - Centralização da finalização (try/finally).
Sprint 18 Auditoria - R-2: DEV allowlist (fail-closed).
Sprint 26 E02 - Integracao com ChipSelector para multi-chip.

Este módulo é o wrapper que:
1. Verifica DEV allowlist (R-2) - PRIMEIRO, antes de tudo
2. Verifica deduplicação (evita duplicatas em retry/timeout)
3. Verifica guardrails antes de enviar
4. Seleciona chip via ChipSelector (se MULTI_CHIP_ENABLED)
5. Chama provider do chip selecionado
6. Emite eventos de auditoria
7. Finalização centralizada (last_touch, atribuição)
8. Retorna outcome detalhado para rastreamento

IMPORTANTE: Nenhum outro código deve chamar evolution.enviar_mensagem() diretamente.
Use sempre send_outbound_message() deste módulo.
"""
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.core.config import settings
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
from app.services.guardrails.error_classifier import classify_provider_error

logger = logging.getLogger(__name__)


# =============================================================================
# MULTI-CHIP CONFIG (Sprint 26 E02)
# =============================================================================

def _is_multi_chip_enabled() -> bool:
    """Verifica se multi-chip esta habilitado."""
    return getattr(settings, "MULTI_CHIP_ENABLED", False)


def _determinar_tipo_mensagem(ctx: "OutboundContext") -> str:
    """
    Determina o tipo de mensagem baseado no contexto.

    Returns:
        'prospeccao', 'followup', ou 'resposta'
    """
    # Resposta: quando eh reply a uma mensagem recebida
    if ctx.method == OutboundMethod.REPLY:
        return "resposta"

    # Prospeccao: campanha proativa para contato frio
    if ctx.method == OutboundMethod.CAMPAIGN and ctx.is_proactive:
        return "prospeccao"

    # Followup: acompanhamento de conversa existente
    if ctx.method in (OutboundMethod.FOLLOWUP, OutboundMethod.REACTIVATION):
        return "followup"

    # Default: resposta (mais permissivo)
    return "resposta"


async def _enviar_via_multi_chip(
    telefone: str,
    texto: str,
    ctx: "OutboundContext",
    simular_digitacao: bool = False,
    tempo_digitacao: float = None,
    chips_excluidos: Optional[list] = None,
) -> dict:
    """
    Envia mensagem usando o sistema multi-chip.

    Sprint 26 E02: Seleciona melhor chip e envia via provider.

    Args:
        telefone: Numero do destinatario
        texto: Texto da mensagem
        ctx: Contexto do envio
        simular_digitacao: Se deve simular digitacao
        tempo_digitacao: Tempo de digitacao
        chips_excluidos: Lista de chip IDs a excluir da seleção (ex: campanha)

    Returns:
        Dict com resultado do envio
    """
    from app.services.chips.selector import chip_selector
    from app.services.chips.sender import enviar_via_chip

    tipo_mensagem = _determinar_tipo_mensagem(ctx)

    # Selecionar chip (excluindo chips da campanha se configurado)
    chip = await chip_selector.selecionar_chip(
        tipo_mensagem=tipo_mensagem,
        conversa_id=ctx.conversation_id,
        telefone_destino=telefone,
        excluir_chips=chips_excluidos,
    )

    if not chip:
        logger.warning(
            f"[MultiChip] Nenhum chip disponivel para {tipo_mensagem}, "
            f"fallback para Evolution"
        )
        return {"fallback": True}

    # Simular digitacao se necessario
    if simular_digitacao:
        from app.services.whatsapp_providers import get_provider
        import asyncio

        provider = get_provider(chip)
        tempo = tempo_digitacao or 1.5

        # Enviar presence "composing"
        try:
            # Evolution API: /chat/presence/{instance}
            if chip.get("provider") == "evolution":
                import httpx
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"{provider.base_url}/chat/presence/{provider.instance_name}",
                        headers=provider.headers,
                        json={
                            "number": telefone,
                            "delay": int(tempo * 1000),
                            "presence": "composing",
                        }
                    )
        except Exception as e:
            logger.debug(f"[MultiChip] Erro ao enviar presence: {e}")

        await asyncio.sleep(tempo)

    # Enviar mensagem
    result = await enviar_via_chip(chip, telefone, texto)

    # Registrar envio para metricas
    if result.success and ctx.conversation_id:
        try:
            await chip_selector.registrar_envio(
                chip_id=chip["id"],
                conversa_id=ctx.conversation_id,
                tipo_mensagem=tipo_mensagem,
                telefone_destino=telefone,
            )
        except Exception as e:
            logger.warning(f"[MultiChip] Erro ao registrar envio: {e}")

    # Converter para formato esperado pelo outbound
    response = None
    if result.success:
        response = {
            "key": {"id": result.message_id},
            "provider": result.provider,
            "chip_id": chip["id"],
            "chip_telefone": chip.get("telefone"),
        }

    return {
        "success": result.success,
        "response": response,
        "error": result.error,
        "fallback": False,
    }


def _verificar_dev_allowlist(telefone: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se o número está na allowlist de DEV.

    R-2: DEV allowlist (fail-closed)

    Esta verificação é INESCAPÁVEL e roda ANTES de qualquer outro guardrail.
    NÃO tem bypass humano - DEV nunca pode enviar para fora da allowlist.

    Comportamento:
    - PROD (APP_ENV=production): sempre permitido, retorna (True, None)
    - DEV com allowlist VAZIA: bloqueia TUDO, retorna (False, "dev_allowlist_empty")
    - DEV com número NA allowlist: permitido, retorna (True, None)
    - DEV com número FORA da allowlist: bloqueia, retorna (False, "dev_allowlist")

    Args:
        telefone: Número de destino (5511999999999)

    Returns:
        Tuple (pode_enviar, reason_code)
    """
    # Em produção, não verifica
    if settings.is_production:
        return (True, None)

    # Normalizar telefone (só dígitos)
    telefone_normalizado = "".join(filter(str.isdigit, telefone))

    # Obter allowlist
    allowlist = settings.outbound_allowlist_numbers

    # Allowlist vazia em DEV = fail-closed (bloqueia TUDO)
    if not allowlist:
        logger.warning(
            f"[DEV GUARDRAIL] BLOCKED: OUTBOUND_ALLOWLIST vazia em DEV. "
            f"Destino: {telefone_normalizado[:8]}... bloqueado."
        )
        return (False, "dev_allowlist_empty")

    # Verificar se número está na allowlist
    if telefone_normalizado not in allowlist:
        logger.warning(
            f"[DEV GUARDRAIL] BLOCKED: {telefone_normalizado[:8]}... "
            f"não está na allowlist. Permitidos: {len(allowlist)} números."
        )
        return (False, "dev_allowlist")

    logger.debug(
        f"[DEV GUARDRAIL] ALLOWED: {telefone_normalizado[:8]}... está na allowlist."
    )
    return (True, None)


def _gerar_content_hash(texto: str) -> str:
    """Gera hash do conteúdo para deduplicação."""
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


async def _atualizar_last_touch(
    cliente_id: str,
    method: str,
    campaign_id: Optional[str] = None,
) -> None:
    """
    Atualiza campos last_touch_* no doctor_state.

    Sprint 24 E03: Centralização do tracking de último touch.
    Usado pelo guardrail campaign_cooldown (E04).

    Args:
        cliente_id: ID do cliente
        method: Método do envio (campaign, followup, reply, etc)
        campaign_id: ID da campanha (se aplicável)
    """
    from app.services.supabase import supabase

    try:
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "last_touch_at": now,
            "last_touch_method": method,
        }

        # campaign_id só é setado para method=campaign
        if campaign_id:
            update_data["last_touch_campaign_id"] = campaign_id
        else:
            # Limpar campaign_id se não for campanha
            update_data["last_touch_campaign_id"] = None

        supabase.table("doctor_state").upsert(
            {"cliente_id": cliente_id, **update_data},
            on_conflict="cliente_id",
        ).execute()

        logger.debug(
            f"Last touch atualizado: {cliente_id[:8]}... "
            f"method={method}, campaign_id={campaign_id}"
        )

    except Exception as e:
        # Não falha o envio se não conseguir atualizar
        logger.error(f"Erro ao atualizar last_touch: {e}")


async def _finalizar_envio(
    ctx: "OutboundContext",
    outcome: "SendOutcome",
    dedupe_key: Optional[str] = None,
    provider_message_id: Optional[str] = None,
) -> None:
    """
    Finalização centralizada de envio outbound.

    Sprint 24 E03: Garante que todas as ações de finalização
    sejam executadas, independente do outcome.

    Ações executadas:
    - Atualizar last_touch_* no doctor_state (só para SENT/BYPASS)
    - Registrar campaign_touch para atribuição (só para SENT/BYPASS com campaign_id)

    Args:
        ctx: Contexto do envio
        outcome: Resultado do envio (SENT, BLOCKED_*, DEDUPED, FAILED_*)
        dedupe_key: Chave de deduplicação usada
        provider_message_id: ID da mensagem no provedor
    """
    try:
        # Só atualiza last_touch para envios bem-sucedidos
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

            # Registrar envio no histórico de campanhas (legado)
            if ctx.campaign_id:
                from app.services.campaign_cooldown import registrar_envio_campanha
                await registrar_envio_campanha(
                    cliente_id=ctx.cliente_id,
                    campaign_id=int(ctx.campaign_id),
                    campaign_type=method,
                )

            logger.debug(
                f"Finalização completa: {ctx.cliente_id[:8]}... "
                f"outcome={outcome.value}, method={method}"
            )

    except Exception as e:
        # Não falha o retorno se finalização falhar
        logger.error(f"Erro na finalização de envio: {e}")


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
    chip_id: Optional[str] = None  # Sprint 41: ID do chip que enviou

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
    chips_excluidos: Optional[list] = None,
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
        chips_excluidos: Lista de chip IDs a excluir da seleção (ex: campanha)

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

    # 0. Verificar DEV allowlist PRIMEIRO (R-2: fail-closed)
    # Esta verificação é INESCAPÁVEL - DEV nunca pode enviar para fora da allowlist
    pode_enviar_dev, reason_dev = _verificar_dev_allowlist(telefone)
    if not pode_enviar_dev:
        logger.warning(
            f"[DEV GUARDRAIL] Outbound bloqueado para {telefone[:8]}...: {reason_dev}",
            extra={
                "event": "outbound_blocked_dev_allowlist",
                "reason_code": reason_dev,
                "cliente_id": ctx.cliente_id,
                "app_env": settings.APP_ENV,
            }
        )
        return OutboundResult(
            success=False,
            outcome=SendOutcome.BLOCKED_DEV_ALLOWLIST,
            outcome_reason_code=reason_dev,
            outcome_at=now,
            blocked=True,
            deduped=False,
        )

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

    # 3. Enviar via Multi-Chip ou Evolution API (fallback)
    # Sprint 24 E03: Usar try/finally para garantir finalização
    # Sprint 26 E02: Multi-chip com selecao inteligente
    result: Optional[OutboundResult] = None
    provider_message_id: Optional[str] = None
    response = None
    used_multi_chip = False

    try:
        # Sprint 26 E02: Tentar multi-chip se habilitado
        if _is_multi_chip_enabled():
            try:
                multi_result = await _enviar_via_multi_chip(
                    telefone=telefone,
                    texto=texto,
                    ctx=ctx,
                    simular_digitacao=simular_digitacao,
                    tempo_digitacao=tempo_digitacao,
                    chips_excluidos=chips_excluidos,
                )

                if not multi_result.get("fallback"):
                    used_multi_chip = True
                    if multi_result.get("success"):
                        response = multi_result.get("response")
                    else:
                        # Erro no multi-chip, propagar
                        raise Exception(multi_result.get("error", "Erro no multi-chip"))

            except Exception as e:
                logger.warning(
                    f"[MultiChip] Erro, fallback para Evolution: {e}",
                    extra={"error": str(e), "telefone_prefix": telefone[:8]}
                )
                used_multi_chip = False

        # Fallback: Evolution API legado (instancia fixa)
        if not used_multi_chip:
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
        chip_id = None
        if response and isinstance(response, dict):
            # Evolution API retorna key.id como message id
            key = response.get("key", {})
            provider_message_id = key.get("id") if isinstance(key, dict) else None
            # Sprint 41: Extrair chip_id se disponível (multi-chip)
            chip_id = response.get("chip_id")

        result = OutboundResult(
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
            chip_id=chip_id,  # Sprint 41
        )

    except RateLimitError as e:
        logger.warning(f"Rate limit ao enviar para {telefone[:8]}...: {e}")
        await marcar_falha(dedupe_key, f"rate_limit: {e}")
        result = OutboundResult(
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
        result = OutboundResult(
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
        # Classificar erro para diagnóstico operacional
        classified = classify_provider_error(e)
        logger.error(
            f"Erro ao enviar para {telefone[:8]}...: {classified.provider_error_code} - {e}",
            extra={
                "outcome": classified.outcome.value,
                "provider_error_code": classified.provider_error_code,
            }
        )
        await marcar_falha(dedupe_key, f"{classified.provider_error_code}:{str(e)[:150]}")
        result = OutboundResult(
            success=False,
            outcome=classified.outcome,
            outcome_reason_code=f"{classified.provider_error_code}:{classified.provider_error_raw[:80]}",
            outcome_at=now,
            blocked=False,
            deduped=False,
            dedupe_key=dedupe_key,
            error=str(e),
        )

    finally:
        # Sprint 24 E03: Finalização centralizada
        # Garante que last_touch e atribuição sejam atualizados
        if result:
            await _finalizar_envio(
                ctx=ctx,
                outcome=result.outcome,
                dedupe_key=dedupe_key,
                provider_message_id=provider_message_id,
            )

    return result


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
