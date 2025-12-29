"""
Pos-processadores do pipeline.

Sprint 16: Integração com policy_events via update_effect_interaction_id.
"""
import asyncio
import logging
import time

from .base import PostProcessor, ProcessorContext, ProcessorResult
from app.services.timing import calcular_delay_resposta
from app.services.agente import enviar_resposta
from app.services.interacao import salvar_interacao
from app.services.metricas import metricas_service
from app.services.whatsapp import mostrar_digitando
from app.services.validacao_output import validar_e_corrigir, output_validator
from app.services.policy.events_repository import update_effect_interaction_id
from app.services.outbound import criar_contexto_reply
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ValidateOutputProcessor(PostProcessor):
    """
    Valida resposta antes de enviar.

    Detecta e bloqueia:
    - Revelacao de que Julia e IA
    - Formatos proibidos (bullets, markdown)
    - Linguagem robotica/corporativa

    Prioridade: 5 (roda ANTES de todos)
    """
    name = "validate_output"
    priority = 5

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        # Validar e tentar corrigir
        resposta_validada, foi_modificado = await validar_e_corrigir(response)

        if foi_modificado:
            if resposta_validada:
                logger.info("Resposta foi corrigida pela validacao")
                context.metadata["resposta_corrigida"] = True
                context.metadata["resposta_original"] = response
            else:
                # Resposta bloqueada (revelacao critica de IA)
                logger.critical(
                    f"Resposta BLOQUEADA! Revelaria IA. "
                    f"Original: {response[:100]}..."
                )
                context.metadata["resposta_bloqueada"] = True
                context.metadata["resposta_original"] = response
                # Retorna vazio - nao envia nada
                return ProcessorResult(
                    success=True,
                    response="",
                    metadata={"blocked": True}
                )

        return ProcessorResult(success=True, response=resposta_validada)


class TimingProcessor(PostProcessor):
    """
    Aplica delay humanizado antes de enviar.

    Prioridade: 10 (roda primeiro)
    """
    name = "timing"
    priority = 10

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        # Calcular delay
        delay = calcular_delay_resposta(context.mensagem_texto)
        tempo_inicio = context.metadata.get("tempo_inicio", time.time())
        tempo_processamento = time.time() - tempo_inicio
        delay_restante = max(0, delay - tempo_processamento)

        logger.debug(
            f"Delay: {delay:.1f}s, processamento: {tempo_processamento:.1f}s, "
            f"restante: {delay_restante:.1f}s"
        )

        # Aguardar e mostrar digitando (com tratamento de erro)
        try:
            if delay_restante > 5:
                await asyncio.sleep(delay_restante - 5)
                await mostrar_digitando(context.telefone)
                await asyncio.sleep(5)
            elif delay_restante > 0:
                await asyncio.sleep(delay_restante)
                await mostrar_digitando(context.telefone)
        except Exception as e:
            # Erro no mostrar_digitando nao deve parar o pipeline
            logger.warning(f"Erro ao mostrar digitando (nao critico): {e}")

        return ProcessorResult(success=True, response=response)


class SendMessageProcessor(PostProcessor):
    """
    Envia mensagem via WhatsApp.

    Sprint 18.1 P0: Usa guardrails wrapper com contexto de REPLY.

    Prioridade: 20
    """
    name = "send_message"
    priority = 20

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        if not response:
            return ProcessorResult(success=True, response=response)

        # Sprint 18.1 P0: Salvar interação de entrada ANTES para ter inbound_proof
        inbound_interaction_id = None
        if not context.metadata.get("entrada_salva") and context.conversa and context.medico:
            try:
                interacao_entrada = await salvar_interacao(
                    conversa_id=context.conversa["id"],
                    cliente_id=context.medico["id"],
                    tipo="entrada",
                    conteudo=context.mensagem_texto or "[midia]",
                    autor_tipo="medico",
                    message_id=context.message_id
                )
                context.metadata["entrada_salva"] = True
                inbound_interaction_id = interacao_entrada.get("id") if interacao_entrada else None
            except Exception as e:
                logger.warning(f"Erro ao salvar interação de entrada: {e}")

        # Sprint 18.1 P0: Criar contexto de REPLY com prova de inbound
        ctx = None
        if context.medico and context.conversa:
            ctx = criar_contexto_reply(
                cliente_id=context.medico["id"],
                conversation_id=context.conversa["id"],
                inbound_interaction_id=inbound_interaction_id,
                last_inbound_at=datetime.now(timezone.utc).isoformat(),
                policy_decision_id=context.metadata.get("policy_decision_id"),
            )

        resultado = await enviar_resposta(
            telefone=context.telefone,
            resposta=response,
            ctx=ctx,
        )

        # Sprint 18.1: OutboundResult handling
        if hasattr(resultado, 'blocked') and resultado.blocked:
            logger.warning(f"Mensagem bloqueada por guardrail: {resultado.block_reason}")
            return ProcessorResult(
                success=False,
                error=f"Guardrail bloqueou: {resultado.block_reason}"
            )

        if hasattr(resultado, 'success') and not resultado.success:
            logger.error(f"Falha ao enviar mensagem: {resultado.error}")
            return ProcessorResult(
                success=False,
                error=resultado.error or "Falha ao enviar mensagem"
            )

        # Sucesso
        context.metadata["message_sent"] = True
        if hasattr(resultado, 'evolution_response') and resultado.evolution_response:
            context.metadata["sent_message_id"] = resultado.evolution_response.get("key", {}).get("id")
        elif isinstance(resultado, dict):
            # Fallback para dict legado
            context.metadata["sent_message_id"] = resultado.get("key", {}).get("id")

        logger.info(f"Mensagem enviada para {context.telefone[:8]}...")

        # Sprint 17 - E04: Emitir doctor_outbound
        await self._emitir_outbound_event(context, response)

        return ProcessorResult(success=True, response=response)

    async def _emitir_outbound_event(
        self,
        context: ProcessorContext,
        response: str
    ) -> None:
        """Emite evento doctor_outbound se no rollout."""
        from app.services.business_events import (
            emit_event,
            should_emit_event,
            BusinessEvent,
            EventType,
            EventSource,
        )

        cliente_id = context.medico.get("id") if context.medico else None
        if not cliente_id:
            return

        # Verificar rollout
        should_emit = await should_emit_event(cliente_id, "doctor_outbound")
        if not should_emit:
            return

        # Emitir evento em background
        asyncio.create_task(
            emit_event(BusinessEvent(
                event_type=EventType.DOCTOR_OUTBOUND,
                source=EventSource.PIPELINE,
                cliente_id=cliente_id,
                conversation_id=context.conversa.get("id") if context.conversa else None,
                event_props={
                    "message_length": len(response),
                },
            ))
        )

        logger.debug(f"doctor_outbound emitido para cliente {cliente_id[:8]}")


class SaveInteractionProcessor(PostProcessor):
    """
    Salva interacoes no banco.

    Prioridade: 30
    """
    name = "save_interaction"
    priority = 30

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        try:
            # Salvar interacao de entrada (se ainda nao salvou)
            if not context.metadata.get("entrada_salva"):
                await salvar_interacao(
                    conversa_id=context.conversa["id"],
                    cliente_id=context.medico["id"],
                    tipo="entrada",
                    conteudo=context.mensagem_texto or "[midia]",
                    autor_tipo="medico",
                    message_id=context.message_id
                )
                context.metadata["entrada_salva"] = True

            # Salvar interacao de saida (se enviou)
            if response and context.metadata.get("message_sent"):
                interacao = await salvar_interacao(
                    conversa_id=context.conversa["id"],
                    cliente_id=context.medico["id"],
                    tipo="saida",
                    conteudo=response,
                    autor_tipo="julia",
                    message_id=context.metadata.get("sent_message_id")
                )

                # Sprint 16 - E08: Atualizar policy_event com interaction_id
                policy_decision_id = context.metadata.get("policy_decision_id")
                if interacao and policy_decision_id:
                    interaction_id = interacao.get("id")
                    if interaction_id:
                        await update_effect_interaction_id(
                            policy_decision_id=policy_decision_id,
                            effect_type="message_sent",
                            interaction_id=interaction_id,
                        )
                        logger.debug(f"Policy effect atualizado com interaction_id: {interaction_id}")

            logger.debug("Interacoes salvas")

        except Exception as e:
            logger.error(f"Erro ao salvar interacoes: {e}")
            # Nao para o pipeline por isso

        return ProcessorResult(success=True, response=response)


class ChatwootResponseProcessor(PostProcessor):
    """
    Sincroniza mensagens com Chatwoot quando ha formato LID.

    A integracao automatica Evolution-Chatwoot pode ter bugs com LID format,
    entao enviamos diretamente para garantir que as mensagens aparecam
    corretamente (usuario como incoming, Julia como outgoing).

    Prioridade: 25 (logo apos SendMessage)
    """
    name = "chatwoot_response"
    priority = 25

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        # So sincroniza se tiver ID da conversa do Chatwoot
        chatwoot_conversation_id = context.metadata.get("chatwoot_conversation_id")
        if not chatwoot_conversation_id:
            return ProcessorResult(success=True, response=response)

        try:
            from app.services.chatwoot import chatwoot_service

            # 1. Enviar mensagem do usuario como incoming (se ainda nao foi sincronizada)
            if context.mensagem_texto and not context.metadata.get("chatwoot_incoming_sent"):
                await chatwoot_service.enviar_mensagem(
                    conversation_id=chatwoot_conversation_id,
                    content=context.mensagem_texto,
                    message_type="incoming"
                )
                context.metadata["chatwoot_incoming_sent"] = True
                logger.info(f"Mensagem do usuario sincronizada com Chatwoot conversa {chatwoot_conversation_id}")

            # 2. Enviar resposta da Julia como outgoing (se mensagem foi enviada)
            if response and context.metadata.get("message_sent"):
                await chatwoot_service.enviar_mensagem(
                    conversation_id=chatwoot_conversation_id,
                    content=response,
                    message_type="outgoing"
                )
                logger.info(f"Resposta sincronizada com Chatwoot conversa {chatwoot_conversation_id}")

        except Exception as e:
            # Erro na sincronizacao nao deve parar o pipeline
            logger.warning(f"Erro ao sincronizar com Chatwoot (nao critico): {e}")

        return ProcessorResult(success=True, response=response)


class MetricsProcessor(PostProcessor):
    """
    Registra metricas da conversa.

    Prioridade: 40
    """
    name = "metrics"
    priority = 40

    async def process(
        self,
        context: ProcessorContext,
        response: str
    ) -> ProcessorResult:
        try:
            tempo_inicio = context.metadata.get("tempo_inicio", time.time())
            tempo_resposta = time.time() - tempo_inicio

            # Registrar mensagem do medico
            await metricas_service.registrar_mensagem(
                conversa_id=context.conversa["id"],
                origem="medico"
            )

            # Registrar resposta da Julia
            if response:
                await metricas_service.registrar_mensagem(
                    conversa_id=context.conversa["id"],
                    origem="ai",
                    tempo_resposta_segundos=tempo_resposta
                )

        except Exception as e:
            logger.warning(f"Erro ao registrar metricas: {e}")

        return ProcessorResult(success=True, response=response)
