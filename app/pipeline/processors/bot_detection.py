"""
Processador de detecção de bot.

Sprint 44 T03.3: Módulo separado.
"""

import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class BotDetectionProcessor(PreProcessor):
    """
    Detecta se medico menciona que Julia e um bot.

    Prioridade: 35 (apos optout, antes de media)
    """

    name = "bot_detection"
    priority = 35

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        from app.services.deteccao_bot import detectar_mencao_bot, registrar_deteccao_bot

        deteccao = detectar_mencao_bot(context.mensagem_texto)

        if deteccao["detectado"]:
            logger.warning(f"Deteccao de bot: '{deteccao['trecho']}'")
            await registrar_deteccao_bot(
                cliente_id=context.medico["id"],
                conversa_id=context.conversa["id"],
                mensagem=context.mensagem_texto,
                padrao=deteccao["padrao"],
                trecho=deteccao["trecho"],
            )
            context.metadata["bot_detected"] = True
            # Nao bloqueia processamento, apenas registra

        return ProcessorResult(success=True)
