"""
Worker para processar fila de mensagens.

Sprint 23 E01 - Registra outcome detalhado para cada envio.
"""
import asyncio
import logging
from typing import Optional

from app.services.fila import fila_service
from app.services.rate_limiter import pode_enviar
from app.services.outbound import send_outbound_message, criar_contexto_followup, criar_contexto_campanha
from app.services.guardrails import SendOutcome

logger = logging.getLogger(__name__)


async def processar_fila():
    """
    Worker que processa fila de mensagens.

    Roda continuamente, processando uma mensagem por vez
    respeitando rate limiting.

    Sprint 23 E01: Registra outcome detalhado em fila_mensagens.
    """
    logger.info("Worker de fila iniciado")

    while True:
        mensagem: Optional[dict] = None
        try:
            # Obter próxima mensagem
            mensagem = await fila_service.obter_proxima()

            if not mensagem:
                # Fila vazia, aguardar
                await asyncio.sleep(5)
                continue

            # Verificar rate limiting
            cliente_id = mensagem.get("cliente_id")
            if cliente_id and not await pode_enviar(cliente_id):
                # Reagendar para depois
                await fila_service.marcar_erro(
                    mensagem["id"],
                    "Rate limit atingido"
                )
                await asyncio.sleep(10)
                continue

            # Enviar mensagem
            cliente = mensagem.get("clientes", {})
            telefone = cliente.get("telefone")

            if not telefone:
                logger.error(f"Mensagem {mensagem['id']} sem telefone")
                # Registrar outcome de validacao
                await fila_service.registrar_outcome(
                    mensagem_id=mensagem["id"],
                    outcome=SendOutcome.FAILED_VALIDATION,
                    outcome_reason_code="telefone_nao_encontrado",
                )
                continue

            # Criar contexto apropriado baseado no tipo e metadata
            metadata = mensagem.get("metadata", {})
            campaign_id = metadata.get("campanha_id")

            if campaign_id:
                # Envio de campanha
                ctx = criar_contexto_campanha(
                    cliente_id=cliente_id,
                    campaign_id=campaign_id,
                    conversation_id=mensagem.get("conversa_id"),
                )
            else:
                # Followup ou outro tipo
                ctx = criar_contexto_followup(
                    cliente_id=cliente_id,
                    conversation_id=mensagem.get("conversa_id"),
                )

            # Enviar mensagem (inclui guardrails e deduplicacao)
            result = await send_outbound_message(
                telefone=telefone,
                texto=mensagem["conteudo"],
                ctx=ctx,
                simular_digitacao=True,
            )

            # Registrar outcome detalhado (Sprint 23 E01)
            await fila_service.registrar_outcome(
                mensagem_id=mensagem["id"],
                outcome=result.outcome,
                outcome_reason_code=result.outcome_reason_code,
                provider_message_id=result.provider_message_id,
            )

            if result.outcome.is_success:
                logger.info(
                    f"Mensagem enviada: {mensagem['id']} "
                    f"(provider_id={result.provider_message_id})"
                )
            elif result.outcome.is_blocked:
                logger.info(
                    f"Mensagem {mensagem['id']} bloqueada: "
                    f"{result.outcome.value} - {result.outcome_reason_code}"
                )
            elif result.outcome.is_deduped:
                logger.info(
                    f"Mensagem {mensagem['id']} deduplicada: "
                    f"{result.outcome_reason_code}"
                )
            else:
                logger.warning(
                    f"Mensagem {mensagem['id']} falhou: "
                    f"{result.outcome.value} - {result.error}"
                )

            # Delay entre envios
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no worker: {e}", exc_info=True)
            if mensagem:
                # Registrar outcome de erro generico
                await fila_service.registrar_outcome(
                    mensagem_id=mensagem["id"],
                    outcome=SendOutcome.FAILED_PROVIDER,
                    outcome_reason_code=f"worker_exception:{str(e)[:100]}",
                )
            await asyncio.sleep(10)

