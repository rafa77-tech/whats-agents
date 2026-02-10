"""
Core processor - geracao de resposta via LLM.

Sprint 16: Propaga policy_decision_id para post-processors.
"""

import logging

from .base import ProcessorContext, ProcessorResult
from app.services.agente import processar_mensagem_completo

logger = logging.getLogger(__name__)


class LLMCoreProcessor:
    """
    Processador core que chama o LLM para gerar resposta.

    Sprint 16: Agora propaga policy_decision_id via context.metadata.
    """

    name = "llm_core"

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """
        Gera resposta usando o agente Julia.
        """
        try:
            resultado = await processar_mensagem_completo(
                mensagem_texto=context.mensagem_texto,
                medico=context.medico,
                conversa=context.conversa,
                vagas=None,  # TODO: buscar vagas relevantes
            )

            # Sprint 16: Propagar policy_decision_id para post-processors
            if resultado and resultado.policy_decision_id:
                context.metadata["policy_decision_id"] = resultado.policy_decision_id
                context.metadata["rule_matched"] = resultado.rule_matched

            if not resultado or not resultado.resposta:
                logger.warning("Julia nao gerou resposta")
                return ProcessorResult(success=True, response=None, metadata={"no_response": True})

            return ProcessorResult(success=True, response=resultado.resposta)

        except Exception as e:
            logger.error(f"Erro no core processor: {e}", exc_info=True)
            return ProcessorResult(success=False, error=str(e))
