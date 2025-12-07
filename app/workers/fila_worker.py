"""
Worker para processar fila de mensagens.
"""
import asyncio
import logging
from typing import Optional

from app.services.fila import fila_service
from app.services.whatsapp import enviar_com_digitacao
from app.services.rate_limiter import pode_enviar

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

            await enviar_com_digitacao(
                telefone=telefone,
                texto=mensagem["conteudo"]
            )

            await fila_service.marcar_enviada(mensagem["id"])
            logger.info(f"Mensagem enviada: {mensagem['id']}")

            # Delay entre envios
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no worker: {e}", exc_info=True)
            if mensagem:
                await fila_service.marcar_erro(mensagem["id"], str(e))
            await asyncio.sleep(10)

