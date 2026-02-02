"""
Processador de mídia (audio, imagem, documento, video).

Sprint 44 T03.3: Módulo separado.
"""
import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class MediaProcessor(PreProcessor):
    """
    Trata mensagens de midia (audio, imagem, documento, video).

    Prioridade: 40
    """
    name = "media"
    priority = 40

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.services.respostas_especiais import (
            obter_resposta_audio,
            obter_resposta_imagem,
            obter_resposta_documento,
            obter_resposta_video
        )

        tipo = context.tipo_mensagem

        if tipo == "texto":
            return ProcessorResult(success=True)

        resposta = None

        if tipo == "audio":
            resposta = obter_resposta_audio()
        elif tipo == "imagem":
            resposta = obter_resposta_imagem(context.mensagem_texto)
        elif tipo == "documento":
            resposta = obter_resposta_documento()
        elif tipo == "video":
            resposta = obter_resposta_video()

        if resposta:
            return ProcessorResult(
                success=True,
                should_continue=False,
                response=resposta,
                metadata={"media_type": tipo}
            )

        return ProcessorResult(success=True)
