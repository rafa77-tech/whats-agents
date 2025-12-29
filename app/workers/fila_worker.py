"""
Worker para processar fila de mensagens.
"""
import asyncio
import logging
from typing import Optional

from app.services.fila import fila_service
from app.services.rate_limiter import pode_enviar
from app.services.outbound import send_outbound_message, criar_contexto_followup

logger = logging.getLogger(__name__)


async def processar_fila():
    """
    Worker que processa fila de mensagens.

    Roda continuamente, processando uma mensagem por vez
    respeitando rate limiting.
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
                await fila_service.marcar_erro(mensagem["id"], "Telefone não encontrado")
                continue

            # GUARDRAIL: Verificar antes de enviar
            ctx = criar_contexto_followup(
                cliente_id=cliente_id,
                conversation_id=mensagem.get("conversa_id"),
            )
            result = await send_outbound_message(
                telefone=telefone,
                texto=mensagem["conteudo"],
                ctx=ctx,
                simular_digitacao=True,
            )

            if result.blocked:
                logger.info(f"Mensagem {mensagem['id']} bloqueada: {result.block_reason}")
                await fila_service.marcar_erro(mensagem["id"], f"Guardrail: {result.block_reason}")
                continue

            if not result.success:
                await fila_service.marcar_erro(mensagem["id"], result.error)
                continue

            await fila_service.marcar_enviada(mensagem["id"])
            logger.info(f"Mensagem enviada: {mensagem['id']}")

            # Delay entre envios
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no worker: {e}", exc_info=True)
            if mensagem:
                await fila_service.marcar_erro(mensagem["id"], str(e))
            await asyncio.sleep(10)

