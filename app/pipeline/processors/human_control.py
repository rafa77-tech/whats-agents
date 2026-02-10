"""
Processador de controle humano.

Sprint 44 T03.3: Módulo separado.
"""

import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class HumanControlProcessor(PreProcessor):
    """
    Verifica se conversa esta sob controle humano.

    Prioridade: 60
    """

    name = "human_control"
    priority = 60

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if context.conversa.get("controlled_by") == "ai":
            return ProcessorResult(success=True)

        logger.info("Conversa sob controle humano, nao gerando resposta")

        # Sincronizar com Chatwoot para gestor ver
        from app.services.chatwoot import chatwoot_service

        if context.conversa.get("chatwoot_conversation_id") and chatwoot_service.configurado:
            try:
                await chatwoot_service.enviar_mensagem(
                    conversation_id=context.conversa["chatwoot_conversation_id"],
                    content=context.mensagem_texto or "[midia]",
                    message_type="incoming",
                )
            except Exception as e:
                logger.warning(f"Erro ao sincronizar com Chatwoot: {e}")

        return ProcessorResult(
            success=True, should_continue=False, metadata={"human_control": True}
        )
