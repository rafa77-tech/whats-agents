"""
Envio de respostas da Julia com timing humanizado.

Sprint 58 - Epic 2: Extraido de app/services/agente.py
"""

import asyncio
import random
import logging
from typing import Optional

from app.core.tasks import safe_create_task
from app.services.outbound import send_outbound_message, OutboundResult
from app.services.guardrails import OutboundContext
from app.services.mensagem import quebrar_mensagem

logger = logging.getLogger(__name__)


async def _emitir_fallback_event(telefone: str, function_name: str) -> None:
    """
    Emite evento quando fallback legado é usado.

    Sprint 18.1 P0: Fallback barulhento para auditoria.
    """
    try:
        from app.services.business_events import (
            emit_event,
            BusinessEvent,
            EventType,
            EventSource,
        )

        # Criar evento de fallback
        await emit_event(
            BusinessEvent(
                event_type=EventType.OUTBOUND_FALLBACK,
                source=EventSource.BACKEND,
                cliente_id=None,  # Não temos o ID no fallback legado
                event_props={
                    "function": function_name,
                    "telefone_prefix": telefone[:8] if telefone else "unknown",
                    "warning": "Fallback legado usado - migrar para OutboundContext",
                },
            )
        )
        logger.debug(f"outbound_fallback emitido para {function_name}")
    except Exception as e:
        # Se EventType.OUTBOUND_FALLBACK não existir, apenas log
        logger.warning(f"Erro ao emitir outbound_fallback (não crítico): {e}")


async def enviar_mensagens_sequencia(
    telefone: str,
    mensagens: list[str],
    ctx: Optional[OutboundContext] = None,
) -> list[OutboundResult]:
    """
    Envia sequência de mensagens com timing natural.

    Entre mensagens:
    - Delay curto (1-3s) para continuação
    - Delay médio (3-5s) para novo pensamento

    Args:
        telefone: Número do destinatário
        mensagens: Lista de mensagens a enviar
        ctx: Contexto do guardrail (obrigatório para novos usos)

    Returns:
        Lista de resultados do envio (OutboundResult se ctx, dict se legado)

    Sprint 18.1 P0: Agora usa send_outbound_message quando ctx fornecido.
    """
    if ctx is None:
        # BARULHENTO: Log estruturado + evento
        logger.warning(
            "GUARDRAIL_BYPASS: enviar_mensagens_sequencia chamado sem ctx",
            extra={
                "event": "outbound_fallback_used",
                "telefone_prefix": telefone[:8] if telefone else "unknown",
                "mensagens_count": len(mensagens),
            },
        )
        # Emitir evento para auditoria
        safe_create_task(
            _emitir_fallback_event(telefone, "enviar_mensagens_sequencia"),
            name="fallback_event_sequencia",
        )

    resultados = []

    for i, msg in enumerate(mensagens):
        # Calcular delay entre mensagens (Sprint 29: reduzido para agilidade)
        if i > 0:
            # Se começa com minúscula, é continuação (delay curto)
            if msg and msg[0].islower():
                delay = random.uniform(0.5, 1.5)  # Reduzido de 1-3s
            else:
                delay = random.uniform(1, 2)  # Reduzido de 3-5s

            await asyncio.sleep(delay)

        # Enviar com guardrail (se ctx) ou legado
        if ctx:
            resultado = await send_outbound_message(
                telefone=telefone,
                texto=msg,
                ctx=ctx,
                simular_digitacao=True,
            )
            if resultado.blocked or not resultado.success:
                logger.warning(f"Mensagem bloqueada/falhou na sequência: {resultado}")
                resultados.append(resultado)
                break  # Para sequência se bloqueado
        else:
            # Fallback legado - TODO: remover quando todos call sites migrarem
            from app.services.whatsapp import enviar_com_digitacao

            resultado = await enviar_com_digitacao(telefone=telefone, texto=msg)
        resultados.append(resultado)

    return resultados


async def enviar_resposta(
    telefone: str,
    resposta: str,
    ctx: Optional[OutboundContext] = None,
) -> OutboundResult:
    """
    Envia resposta com timing humanizado.
    Quebra mensagens longas em sequência se necessário.

    Args:
        telefone: Número do destinatário
        resposta: Texto da resposta
        ctx: Contexto do guardrail (obrigatório para novos usos)

    Returns:
        Resultado do envio (OutboundResult se ctx, dict se legado)

    Sprint 18.1 P0: Agora usa send_outbound_message quando ctx fornecido.
    """
    if ctx is None:
        # BARULHENTO: Log estruturado + evento
        logger.warning(
            "GUARDRAIL_BYPASS: enviar_resposta chamado sem ctx",
            extra={
                "event": "outbound_fallback_used",
                "telefone_prefix": telefone[:8] if telefone else "unknown",
                "resposta_length": len(resposta) if resposta else 0,
            },
        )
        # Emitir evento para auditoria
        safe_create_task(
            _emitir_fallback_event(telefone, "enviar_resposta"), name="fallback_event_resposta"
        )

    # Quebrar resposta se necessário
    mensagens = quebrar_mensagem(resposta)

    if len(mensagens) == 1:
        if ctx:
            return await send_outbound_message(
                telefone=telefone,
                texto=resposta,
                ctx=ctx,
                simular_digitacao=True,
            )
        else:
            # Fallback legado
            from app.services.whatsapp import enviar_com_digitacao

            return await enviar_com_digitacao(telefone, resposta)
    else:
        resultados = await enviar_mensagens_sequencia(telefone, mensagens, ctx)
        return resultados[0] if resultados else OutboundResult(success=False, error="Sem resultado")
