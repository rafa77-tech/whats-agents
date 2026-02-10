"""
Processador de eventos de negócio (inbound).

Sprint 44 T03.3: Módulo separado.
"""

import logging

from app.core.tasks import safe_create_task
from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class BusinessEventInboundProcessor(PreProcessor):
    """
    Emite evento doctor_inbound e detecta recusas para tracking de funil.

    Sprint 17 - E04, E05

    Prioridade: 22 (logo apos load entities)
    """

    name = "business_event_inbound"
    priority = 22

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.services.business_events import (
            emit_event,
            should_emit_event,
            BusinessEvent,
            EventType,
            EventSource,
            processar_possivel_recusa,
        )

        cliente_id = context.medico.get("id")
        if not cliente_id:
            return ProcessorResult(success=True)

        # Verificar rollout
        should_emit = await should_emit_event(cliente_id, "doctor_inbound")
        if not should_emit:
            return ProcessorResult(success=True)

        # Emitir evento em background (nao bloqueia)
        safe_create_task(
            emit_event(
                BusinessEvent(
                    event_type=EventType.DOCTOR_INBOUND,
                    source=EventSource.PIPELINE,
                    cliente_id=cliente_id,
                    conversation_id=context.conversa.get("id"),
                    event_props={
                        "message_type": context.tipo_mensagem or "text",
                        "has_media": context.tipo_mensagem not in ("texto", "text", None),
                        "message_length": len(context.mensagem_texto or ""),
                    },
                )
            ),
            name="emit_doctor_inbound",
        )

        # E05: Detectar possível recusa de oferta (em background)
        if context.mensagem_texto:
            safe_create_task(
                processar_possivel_recusa(
                    cliente_id=cliente_id,
                    mensagem=context.mensagem_texto,
                    conversation_id=context.conversa.get("id"),
                ),
                name="processar_possivel_recusa",
            )

        logger.debug(f"doctor_inbound emitido para cliente {cliente_id[:8]}")
        return ProcessorResult(success=True)
