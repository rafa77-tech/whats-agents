"""
Ponto unico de envio de mensagens outbound.

Sprint 58 E04 - Extraido de outbound.py monolitico.

Sprint 17 - Todas as mensagens outbound DEVEM passar por aqui.
Sprint 18.1 - C1: Deduplicacao de mensagens outbound.
Sprint 23 E01 - Outcome detalhado com enum padronizado.
Sprint 24 E03 - Centralizacao da finalizacao (try/finally).
Sprint 18 Auditoria - R-2: DEV allowlist (fail-closed).
Sprint 26 E02 - Integracao com ChipSelector para multi-chip.

Este modulo e o wrapper que:
1. Verifica DEV allowlist (R-2) - PRIMEIRO, antes de tudo
2. Verifica deduplicacao (evita duplicatas em retry/timeout)
3. Verifica guardrails antes de enviar
4. Seleciona chip via ChipSelector (se MULTI_CHIP_ENABLED)
5. Chama provider do chip selecionado
6. Emite eventos de auditoria
7. Finalizacao centralizada (last_touch, atribuicao)
8. Retorna outcome detalhado para rastreamento

IMPORTANTE: Nenhum outro codigo deve chamar evolution.enviar_mensagem() diretamente.
Use sempre send_outbound_message() deste modulo.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.guardrails import (
    OutboundContext,
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

from app.services.outbound.types import OutboundResult
from app.services.outbound.dev_guardrails import _verificar_dev_allowlist
from app.services.outbound.finalization import _finalizar_envio
from app.services.outbound.multi_chip import (
    _is_multi_chip_enabled,
    _enviar_via_multi_chip,
)

logger = logging.getLogger(__name__)


def _gerar_content_hash(texto: str) -> str:
    """Gera hash do conteudo para deduplicacao."""
    return hashlib.sha256(texto.encode()).hexdigest()[:16]


async def send_outbound_message(
    telefone: str,
    texto: str,
    ctx: OutboundContext,
    simular_digitacao: bool = False,
    tempo_digitacao: Optional[float] = None,
    chips_excluidos: Optional[list] = None,
) -> OutboundResult:
    """
    Envia mensagem outbound com verificacao de guardrails.

    Este e o UNICO ponto de entrada para enviar mensagens via WhatsApp.
    Todas as campanhas, followups, reativacoes e respostas devem usar esta funcao.

    Sprint 23 E01: Ordem de verificacao alterada:
    1. Deduplicacao ANTES de guardrails (DEDUPED != BLOCKED)
    2. Guardrails
    3. Envio via Evolution API
    4. Retorno de outcome detalhado

    Args:
        telefone: Numero do destinatario (5511999999999)
        texto: Texto da mensagem
        ctx: Contexto completo do envio (obrigatorio)
        simular_digitacao: Se True, mostra "digitando" antes de enviar
        tempo_digitacao: Tempo de digitacao em segundos (opcional)
        chips_excluidos: Lista de chip IDs a excluir da selecao (ex: campanha)

    Returns:
        OutboundResult com outcome detalhado (SENT, BLOCKED_*, DEDUPED, FAILED_*)
    """
    now = datetime.now(timezone.utc)

    # 0. Verificar DEV allowlist PRIMEIRO (R-2: fail-closed)
    # Esta verificacao e INESCAPAVEL - DEV nunca pode enviar para fora da allowlist
    pode_enviar_dev, reason_dev = _verificar_dev_allowlist(telefone)
    if not pode_enviar_dev:
        logger.warning(
            f"[DEV GUARDRAIL] Outbound bloqueado para {telefone[:8]}...: {reason_dev}",
            extra={
                "event": "outbound_blocked_dev_allowlist",
                "reason_code": reason_dev,
                "cliente_id": ctx.cliente_id,
                "app_env": settings.APP_ENV,
            },
        )
        return OutboundResult(
            success=False,
            outcome=SendOutcome.BLOCKED_DEV_ALLOWLIST,
            outcome_reason_code=reason_dev,
            outcome_at=now,
            blocked=True,
            deduped=False,
        )

    # 1. Verificar deduplicacao ANTES de guardrails (Sprint 23 E01)
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
            },
        )
        return OutboundResult(
            success=False,
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code=f"content_hash_window:{motivo}",
            outcome_at=now,
            blocked=False,  # NAO e bloqueio
            deduped=True,  # E deduplicacao
            dedupe_key=dedupe_key,
        )

    # 2. Verificar guardrails
    guardrail_result = await check_outbound_guardrails(ctx)

    if guardrail_result.is_blocked:
        logger.info(f"Outbound bloqueado para {telefone[:8]}...: {guardrail_result.reason_code}")
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
    # Sprint 24 E03: Usar try/finally para garantir finalizacao
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
                else:
                    # Sem chip disponivel -> retornar NO_CAPACITY sem fallback
                    await marcar_falha(dedupe_key, "no_capacity")
                    result = OutboundResult(
                        success=False,
                        outcome=SendOutcome.FAILED_NO_CAPACITY,
                        outcome_reason_code="no_capacity:chips_no_limite",
                        outcome_at=now,
                        blocked=False,
                        deduped=False,
                        dedupe_key=dedupe_key,
                        error="Sem chip disponivel (todos no limite)",
                    )
                    used_multi_chip = True  # Impede fallback para Evolution

            except Exception as e:
                logger.warning(
                    f"[MultiChip] Erro, fallback para Evolution: {e}",
                    extra={"error": str(e), "telefone_prefix": telefone[:8]},
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

        # Se result ja foi setado (ex: no_capacity), pular caminho de sucesso
        if result is None:
            # Marcar dedupe como enviado com sucesso
            await marcar_enviado(dedupe_key)

            # Extrair provider_message_id da resposta
            chip_id = None
            if response and isinstance(response, dict):
                # Evolution API retorna key.id como message id
                key = response.get("key", {})
                provider_message_id = key.get("id") if isinstance(key, dict) else None
                # Sprint 41: Extrair chip_id se disponivel (multi-chip)
                chip_id = response.get("chip_id")

            result = OutboundResult(
                success=True,
                outcome=SendOutcome.BYPASS if guardrail_result.human_bypass else SendOutcome.SENT,
                outcome_reason_code="ok"
                if not guardrail_result.human_bypass
                else guardrail_result.reason_code,
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
            error=f"Evolution API indisponivel: {e}",
        )

    except Exception as e:
        # Classificar erro para diagnostico operacional
        classified = classify_provider_error(e)
        logger.error(
            f"Erro ao enviar para {telefone[:8]}...: {classified.provider_error_code} - {e}",
            extra={
                "outcome": classified.outcome.value,
                "provider_error_code": classified.provider_error_code,
            },
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
        # Sprint 24 E03: Finalizacao centralizada
        # Garante que last_touch e atribuicao sejam atualizados
        if result:
            await _finalizar_envio(
                ctx=ctx,
                outcome=result.outcome,
                dedupe_key=dedupe_key,
                provider_message_id=provider_message_id,
            )

    return result
