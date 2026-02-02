"""
Processador de mensagens fora do horário comercial.

Sprint 44 T03.3: Módulo separado.
"""
import logging
from typing import Optional

from app.core.tasks import safe_create_task
from ..base import PreProcessor, ProcessorContext, ProcessorResult

logger = logging.getLogger(__name__)


class ForaHorarioProcessor(PreProcessor):
    """
    Processa mensagens fora do horário comercial.

    Envia ACK imediato e salva para processamento posterior.
    Bypass do LLM - não gera resposta via Claude.

    Sprint 22 - Responsividade Inteligente

    Prioridade: 32 (após OptOut 30, antes de BotDetection 35)
    """
    name = "fora_horario"
    priority = 32

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        from app.services.fora_horario import (
            eh_horario_comercial,
            processar_mensagem_fora_horario,
            pode_responder_fora_horario,
        )
        from app.services.message_context_classifier import classificar_contexto

        # Se está em horário comercial, continuar pipeline normal
        if eh_horario_comercial():
            return ProcessorResult(success=True)

        # Se conversa está sob controle humano, NÃO enviar ACK
        # Deixar o humano lidar (ele pode estar trabalhando fora do horário)
        if context.conversa and context.conversa.get("controlled_by") == "human":
            logger.info(
                f"Fora do horário mas conversa sob controle humano - sem ACK"
            )
            return ProcessorResult(success=True)  # Continua para HumanControlProcessor

        # Fora do horário - processar
        logger.info(f"Mensagem fora do horário de {context.telefone[-4:]}...")

        # Classificar contexto
        classificacao = await classificar_contexto(mensagem=context.mensagem_texto)

        # Verificar se deve enviar ACK para este tipo de contexto
        if not pode_responder_fora_horario(classificacao):
            logger.debug(f"Tipo {classificacao.tipo} não elegível para ACK fora do horário")
            return ProcessorResult(
                success=True,
                should_continue=False,  # Não continua para LLM
                metadata={"fora_horario": True, "sem_ack": True, "tipo": classificacao.tipo.value}
            )

        # Processar mensagem fora do horário
        cliente_id = context.medico["id"]
        nome = context.medico.get("nome", "").split()[0] if context.medico.get("nome") else ""
        conversa_id = context.conversa.get("id") if context.conversa else None

        resultado = await processar_mensagem_fora_horario(
            cliente_id=cliente_id,
            mensagem=context.mensagem_texto,
            classificacao=classificacao,
            nome_cliente=nome,
            conversa_id=conversa_id,
            contexto={"telefone": context.telefone},
            inbound_message_id=context.message_id  # Para idempotência de webhook retries
        )

        # Se não tem ACK (ceiling atingido), parar sem resposta
        if not resultado.get("ack_mensagem"):
            logger.info(f"ACK ceiling atingido para {context.telefone[-4:]}...")

            # Emitir evento de ACK skipped
            await self._emitir_evento_fora_horario(
                context, classificacao, ack_enviado=False, motivo="ceiling_6h"
            )

            return ProcessorResult(
                success=True,
                should_continue=False,
                metadata={
                    "fora_horario": True,
                    "ack_ceiling": True,
                    "registro_id": resultado.get("registro_id")
                }
            )

        # Emitir evento de ACK enviado
        await self._emitir_evento_fora_horario(
            context, classificacao, ack_enviado=True,
            template_tipo=resultado.get("template_tipo")
        )

        # Retornar ACK como resposta (será enviado pelos post-processors)
        logger.info(f"ACK fora do horário para {context.telefone[-4:]}... (template={resultado.get('template_tipo')})")
        return ProcessorResult(
            success=True,
            should_continue=False,  # Bypass LLM
            response=resultado["ack_mensagem"],
            metadata={
                "fora_horario": True,
                "ack_template": resultado.get("template_tipo"),
                "registro_id": resultado.get("registro_id")
            }
        )

    async def _emitir_evento_fora_horario(
        self,
        context: ProcessorContext,
        classificacao,
        ack_enviado: bool,
        motivo: Optional[str] = None,
        template_tipo: Optional[str] = None
    ) -> None:
        """Emite evento de fora do horário para observabilidade."""
        from app.services.business_events import (
            emit_event,
            BusinessEvent,
            EventType,
            EventSource,
        )

        cliente_id = context.medico.get("id") if context.medico else None
        if not cliente_id:
            return

        event_type = (
            EventType.OUT_OF_HOURS_ACK_SENT if ack_enviado
            else EventType.OUT_OF_HOURS_ACK_SKIPPED
        )

        safe_create_task(
            emit_event(BusinessEvent(
                event_type=event_type,
                source=EventSource.PIPELINE,
                cliente_id=cliente_id,
                conversation_id=context.conversa.get("id") if context.conversa else None,
                event_props={
                    "contexto_tipo": classificacao.tipo.value,
                    "confianca": classificacao.confianca,
                    "template_tipo": template_tipo,
                    "motivo_skip": motivo,
                    "telefone_hash": context.telefone[-4:] if context.telefone else None,
                },
                dedupe_key=f"out_of_hours:{context.message_id}" if context.message_id else None,
            )),
            name="emit_out_of_hours_event"
        )

        logger.debug(f"Evento {event_type.value} emitido para {cliente_id[:8]}")
