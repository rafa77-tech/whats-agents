"""
Processador de sincronização Chatwoot.

Sprint 44 T03.3: Módulo separado.
"""
import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class ChatwootSyncProcessor(PreProcessor):
    """
    Sincroniza IDs do Chatwoot se nao existir.

    Prioridade: 25 (apos load entities)
    """
    name = "chatwoot_sync"
    priority = 25

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if context.conversa.get("chatwoot_conversation_id"):
            return ProcessorResult(success=True)

        from app.services.chatwoot import sincronizar_ids_chatwoot

        try:
            ids = await sincronizar_ids_chatwoot(
                context.medico["id"],
                context.telefone
            )
            if ids.get("chatwoot_conversation_id"):
                context.conversa["chatwoot_conversation_id"] = str(ids["chatwoot_conversation_id"])
                logger.info(f"Chatwoot ID sincronizado: {ids['chatwoot_conversation_id']}")
        except Exception as e:
            logger.warning(f"Erro ao sincronizar Chatwoot ID: {e}")

        return ProcessorResult(success=True)
