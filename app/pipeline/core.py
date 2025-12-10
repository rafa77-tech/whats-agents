"""
Core processor - geracao de resposta via LLM.
"""
import logging

from .base import ProcessorContext, ProcessorResult
from app.services.agente import processar_mensagem_completo

logger = logging.getLogger(__name__)


class LLMCoreProcessor:
    """
    Processador core que chama o LLM para gerar resposta.
    """

    name = "llm_core"

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """
        Gera resposta usando o agente Julia.
        """
        try:
            resposta = await processar_mensagem_completo(
                mensagem_texto=context.mensagem_texto,
                medico=context.medico,
                conversa=context.conversa,
                vagas=None  # TODO: buscar vagas relevantes
            )

            if not resposta:
                logger.warning("Julia nao gerou resposta")
                return ProcessorResult(
                    success=True,
                    response=None,
                    metadata={"no_response": True}
                )

            return ProcessorResult(
                success=True,
                response=resposta
            )

        except Exception as e:
            logger.error(f"Erro no core processor: {e}", exc_info=True)
            return ProcessorResult(
                success=False,
                error=str(e)
            )
