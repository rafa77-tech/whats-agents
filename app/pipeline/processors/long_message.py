"""
Processador de mensagens longas.

Sprint 44 T03.3: Módulo separado.
"""
import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class LongMessageProcessor(PreProcessor):
    """
    Trata mensagens muito longas (trunca ou pede resumo).

    Prioridade: 45 (apos media)
    """
    name = "long_message"
    priority = 45

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        from app.services.mensagem import tratar_mensagem_longa, RESPOSTA_MENSAGEM_LONGA

        texto_processado, acao = tratar_mensagem_longa(context.mensagem_texto)

        if acao == "pedir_resumo":
            logger.warning(
                f"Mensagem muito longa ({len(context.mensagem_texto)} chars), pedindo resumo"
            )
            return ProcessorResult(
                success=True,
                should_continue=False,
                response=RESPOSTA_MENSAGEM_LONGA,
                metadata={"long_message": True, "original_length": len(context.mensagem_texto)}
            )

        if acao == "truncada":
            logger.warning(
                f"Mensagem truncada de {len(context.mensagem_texto)} para {len(texto_processado)} chars"
            )
            context.mensagem_texto = texto_processado
            context.metadata["message_truncated"] = True

        return ProcessorResult(success=True)
