"""
Processador de presença (online, digitando).

Sprint 44 T03.3: Módulo separado.
"""

import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.whatsapp import evolution, mostrar_online

logger = logging.getLogger(__name__)


class PresenceProcessor(PreProcessor):
    """
    Envia presenca (online, digitando) e marca como lida.

    Prioridade: 15 (logo apos parse)
    """

    name = "presence"
    priority = 15

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        # Verificar se é mensagem Z-API (não usa Evolution para presença)
        provider = context.mensagem_raw.get("_provider")
        if provider == "zapi":
            logger.debug("[Presence] Mensagem Z-API - pulando presença Evolution")
            return ProcessorResult(success=True)

        try:
            # Usar remote_jid original para marcar como lida (pode ser LID ou JID normal)
            remote_jid = context.metadata.get("remote_jid") or context.telefone
            await evolution.marcar_como_lida(remote_jid, context.message_id)

            # Mostrar online usando telefone
            await mostrar_online(context.telefone)

        except Exception as e:
            logger.warning(f"Erro ao enviar presenca: {e}")
            # Nao para o pipeline por isso

        return ProcessorResult(success=True)
