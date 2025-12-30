"""
Pre-processadores do pipeline.
"""
import logging
from typing import Optional

from .base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.parser import parsear_mensagem, deve_processar, is_grupo
from app.services.medico import buscar_ou_criar_medico
from app.services.conversa import buscar_ou_criar_conversa
from app.services.optout import detectar_optout, processar_optout, MENSAGEM_CONFIRMACAO_OPTOUT
from app.services.handoff_detector import detectar_trigger_handoff
from app.services.whatsapp import evolution, mostrar_online

logger = logging.getLogger(__name__)


class IngestaoGrupoProcessor(PreProcessor):
    """
    Processa mensagens de grupo para ingestão.

    Salva a mensagem para processamento posterior mas
    NÃO permite que o pipeline continue (Julia não responde em grupos).

    Prioridade: 5 (antes do ParseMessageProcessor)
    """
    name = "ingestao_grupo"
    priority = 5

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        data = context.mensagem_raw

        # Verificar se é grupo
        remote_jid = data.get("key", {}).get("remoteJid", "")
        if not is_grupo(remote_jid):
            # Não é grupo, continuar pipeline normal
            return ProcessorResult(success=True, should_continue=True)

        # É grupo - ingerir e parar pipeline
        try:
            from app.services.grupos.ingestor import ingerir_mensagem_grupo

            mensagem = parsear_mensagem(data)

            if mensagem:
                mensagem_id = await ingerir_mensagem_grupo(mensagem, data)
                logger.debug(f"Mensagem de grupo ingerida: {mensagem_id}")
                return ProcessorResult(
                    success=True,
                    should_continue=False,  # NÃO continua (não responde)
                    metadata={
                        "motivo": "mensagem_grupo_ingerida",
                        "mensagem_id": str(mensagem_id) if mensagem_id else None
                    }
                )
        except Exception as e:
            logger.error(f"Erro na ingestão de grupo: {e}", exc_info=True)

        return ProcessorResult(
            success=True,
            should_continue=False,
            metadata={"motivo": "mensagem_grupo_erro_ingestao"}
        )


class ParseMessageProcessor(PreProcessor):
    """
    Parseia mensagem do webhook da Evolution.

    Prioridade: 10 (roda primeiro)
    """
    name = "parse_message"
    priority = 10

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        mensagem = parsear_mensagem(context.mensagem_raw)

        if not mensagem:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Mensagem nao pode ser parseada"
            )

        # Verificar se deve processar
        if not deve_processar(mensagem):
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para silenciosamente
                metadata={"motivo": "mensagem ignorada (propria/grupo/status)"}
            )

        # Se é LID, tentar resolver para número real
        telefone = mensagem.telefone
        if mensagem.is_lid and mensagem.nome_contato:
            logger.info(f"Tentando resolver LID para '{mensagem.nome_contato}'")
            telefone_resolvido = await evolution.resolver_lid_para_telefone(mensagem.nome_contato)
            if telefone_resolvido:
                telefone = telefone_resolvido
                logger.info(f"LID resolvido com sucesso: {telefone}")
            else:
                # Fallback: buscar no banco de dados pelo nome
                logger.info(f"Tentando fallback: buscar cliente por nome '{mensagem.nome_contato}'")
                from app.services.supabase import supabase
                primeiro_nome = mensagem.nome_contato.split()[0] if mensagem.nome_contato else ""
                if primeiro_nome:
                    result = supabase.table("clientes").select("telefone").ilike("primeiro_nome", primeiro_nome).limit(1).execute()
                    if result.data and result.data[0].get("telefone"):
                        telefone = result.data[0]["telefone"].replace("+", "")
                        logger.info(f"LID resolvido via banco de dados: {telefone}")
                    else:
                        logger.warning(f"Nao foi possivel resolver LID para '{mensagem.nome_contato}'")
                        return ProcessorResult(
                            success=True,
                            should_continue=False,
                            metadata={"motivo": "LID nao resolvido - sem numero real"}
                        )
                else:
                    logger.warning(f"Nao foi possivel resolver LID para '{mensagem.nome_contato}'")
                    return ProcessorResult(
                        success=True,
                        should_continue=False,
                        metadata={"motivo": "LID nao resolvido - sem numero real"}
                    )

        # Popular contexto
        context.mensagem_texto = mensagem.texto or ""
        context.telefone = telefone
        context.message_id = mensagem.message_id
        context.tipo_mensagem = mensagem.tipo
        context.metadata["nome_contato"] = mensagem.nome_contato
        context.metadata["remote_jid"] = mensagem.remote_jid  # Guardar JID original

        # Guardar IDs do Chatwoot para sincronizacao
        if mensagem.chatwoot_conversation_id:
            context.metadata["chatwoot_conversation_id"] = mensagem.chatwoot_conversation_id
        if mensagem.chatwoot_inbox_id:
            context.metadata["chatwoot_inbox_id"] = mensagem.chatwoot_inbox_id

        return ProcessorResult(success=True)


class PresenceProcessor(PreProcessor):
    """
    Envia presenca (online, digitando) e marca como lida.

    Prioridade: 15 (logo apos parse)
    """
    name = "presence"
    priority = 15

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        try:
            # Marcar como lida
            await evolution.marcar_como_lida(
                context.telefone,
                context.message_id
            )

            # Mostrar online
            await mostrar_online(context.telefone)

        except Exception as e:
            logger.warning(f"Erro ao enviar presenca: {e}")
            # Nao para o pipeline por isso

        return ProcessorResult(success=True)


class LoadEntitiesProcessor(PreProcessor):
    """
    Carrega medico e conversa do banco.

    Prioridade: 20
    """
    name = "load_entities"
    priority = 20

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        # Buscar/criar medico
        medico = await buscar_ou_criar_medico(
            telefone=context.telefone,
            nome_whatsapp=context.metadata.get("nome_contato")
        )

        if not medico:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Erro ao buscar/criar medico"
            )

        context.medico = medico

        # Buscar/criar conversa
        conversa = await buscar_ou_criar_conversa(cliente_id=medico["id"])

        if not conversa:
            return ProcessorResult(
                success=False,
                should_continue=False,
                error="Erro ao buscar/criar conversa"
            )

        context.conversa = conversa

        return ProcessorResult(success=True)


class BusinessEventInboundProcessor(PreProcessor):
    """
    Emite evento doctor_inbound e detecta recusas para tracking de funil.

    Sprint 17 - E04, E05

    Prioridade: 22 (logo apos load entities)
    """
    name = "business_event_inbound"
    priority = 22

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        import asyncio
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
        asyncio.create_task(
            emit_event(BusinessEvent(
                event_type=EventType.DOCTOR_INBOUND,
                source=EventSource.PIPELINE,
                cliente_id=cliente_id,
                conversation_id=context.conversa.get("id"),
                event_props={
                    "message_type": context.tipo_mensagem or "text",
                    "has_media": context.tipo_mensagem not in ("texto", "text", None),
                    "message_length": len(context.mensagem_texto or ""),
                },
            ))
        )

        # E05: Detectar possível recusa de oferta (em background)
        if context.mensagem_texto:
            asyncio.create_task(
                processar_possivel_recusa(
                    cliente_id=cliente_id,
                    mensagem=context.mensagem_texto,
                    conversation_id=context.conversa.get("id"),
                )
            )

        logger.debug(f"doctor_inbound emitido para cliente {cliente_id[:8]}")
        return ProcessorResult(success=True)


class OptOutProcessor(PreProcessor):
    """
    Detecta e processa pedidos de opt-out.

    Prioridade: 30
    """
    name = "optout"
    priority = 30

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        is_optout, _ = detectar_optout(context.mensagem_texto)

        if not is_optout:
            return ProcessorResult(success=True)

        logger.info(f"Opt-out detectado para {context.telefone[:8]}...")

        # Processar opt-out
        sucesso = await processar_optout(
            cliente_id=context.medico["id"],
            telefone=context.telefone
        )

        if sucesso:
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para o pipeline
                response=MENSAGEM_CONFIRMACAO_OPTOUT,
                metadata={"optout": True}
            )

        return ProcessorResult(success=True)


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


class HandoffTriggerProcessor(PreProcessor):
    """
    Detecta triggers de handoff para humano.

    Prioridade: 50
    """
    name = "handoff_trigger"
    priority = 50

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        trigger = detectar_trigger_handoff(context.mensagem_texto)

        if not trigger:
            return ProcessorResult(success=True)

        logger.info(f"Trigger de handoff detectado: {trigger['tipo']}")

        from app.services.handoff import iniciar_handoff

        await iniciar_handoff(
            conversa_id=context.conversa["id"],
            cliente_id=context.medico["id"],
            motivo=trigger["motivo"],
            trigger_type=trigger["tipo"]
        )

        return ProcessorResult(
            success=True,
            should_continue=False,  # Nao gera resposta automatica
            metadata={"handoff_trigger": trigger["tipo"]}
        )


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
        import asyncio
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

        asyncio.create_task(
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
            ))
        )

        logger.debug(f"Evento {event_type.value} emitido para {cliente_id[:8]}")


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
                trecho=deteccao["trecho"]
            )
            context.metadata["bot_detected"] = True
            # Nao bloqueia processamento, apenas registra

        return ProcessorResult(success=True)


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


class HandoffKeywordProcessor(PreProcessor):
    """
    Detecta keywords de confirmacao de handoff.

    Divulgadores podem responder via WhatsApp com keywords como
    "confirmado" ou "nao fechou" ao inves de clicar no link.

    Prioridade: 55 (entre HandoffTriggerProcessor e HumanControlProcessor)

    Sprint 20 - E06.
    """
    name = "handoff_keyword"
    priority = 55

    # Keywords de confirmacao (case insensitive)
    KEYWORDS_CONFIRMED = [
        r"\bconfirmado\b",
        r"\bfechou\b",
        r"\bfechado\b",
        r"\bconfirmo\b",
        r"\bok\s*,?\s*fechou\b",
        r"\bfechamos\b",
        r"\bcontrato\s+fechado\b",
        r"\bpode\s+confirmar\b",
        r"\btudo\s+certo\b",
    ]

    KEYWORDS_NOT_CONFIRMED = [
        r"\bnao\s+fechou\b",
        r"\bn[aã]o\s+fechou\b",
        r"\bnao\s+deu\b",
        r"\bn[aã]o\s+deu\b",
        r"\bdesistiu\b",
        r"\bcancelou\b",
        r"\bnao\s+vai\s+dar\b",
        r"\bn[aã]o\s+vai\s+dar\b",
        r"\bperdeu\b",
        r"\bnao\s+confirmou\b",
        r"\bn[aã]o\s+confirmou\b",
        r"\bnao\s+rolou\b",
        r"\bn[aã]o\s+rolou\b",
    ]

    async def process(self, context: ProcessorContext) -> ProcessorResult:
        import re
        from app.services.external_handoff.repository import buscar_handoff_pendente_por_telefone
        from app.services.external_handoff.confirmacao import processar_confirmacao
        from app.services.business_events import emit_event, EventType, EventSource, BusinessEvent

        # Pular se nao for mensagem de texto
        if not context.mensagem_texto:
            return ProcessorResult(success=True)

        telefone = context.telefone
        mensagem = context.mensagem_texto.lower()

        # Buscar handoff pendente para este telefone
        handoff = await buscar_handoff_pendente_por_telefone(telefone)

        if not handoff:
            # Nao e divulgador com handoff pendente
            return ProcessorResult(success=True)

        logger.info(f"Telefone {telefone[-4:]} tem handoff pendente: {handoff['id'][:8]}")

        # Detectar keyword
        action = self._detectar_keyword(mensagem)

        if not action:
            # Nao detectou keyword, deixar Julia responder normalmente
            logger.debug(f"Nenhuma keyword detectada na mensagem do divulgador")
            return ProcessorResult(success=True)

        logger.info(f"Keyword detectada: action={action}")

        # Processar confirmacao
        try:
            resultado = await processar_confirmacao(
                handoff=handoff,
                action=action,
                confirmed_by="keyword",
            )

            # Emitir evento especifico de keyword
            event = BusinessEvent(
                event_type=EventType.HANDOFF_CONFIRM_CLICKED,
                source=EventSource.BACKEND,
                event_props={
                    "handoff_id": handoff["id"],
                    "action": action,
                    "via": "keyword",
                    "mensagem_original": context.mensagem_texto[:100],
                },
                dedupe_key=f"handoff_keyword:{handoff['id']}:{action}",
            )
            await emit_event(event)

            # Gerar resposta de agradecimento
            resposta = self._gerar_resposta_agradecimento(action)

            logger.info(f"Handoff {handoff['id'][:8]} processado via keyword: {action}")

            return ProcessorResult(
                success=True,
                should_continue=False,  # Nao continua para o agente
                response=resposta,
                metadata={
                    "handoff_keyword": True,
                    "handoff_id": handoff["id"],
                    "action": action,
                }
            )

        except Exception as e:
            logger.error(f"Erro ao processar keyword de handoff: {e}")
            # Deixar Julia responder normalmente
            return ProcessorResult(success=True)

    def _detectar_keyword(self, mensagem: str) -> Optional[str]:
        """Detecta keyword na mensagem."""
        import re

        # Verificar NOT_CONFIRMED primeiro (mais especifico)
        for pattern in self.KEYWORDS_NOT_CONFIRMED:
            if re.search(pattern, mensagem, re.IGNORECASE):
                return "not_confirmed"

        # Verificar CONFIRMED
        for pattern in self.KEYWORDS_CONFIRMED:
            if re.search(pattern, mensagem, re.IGNORECASE):
                return "confirmed"

        return None

    def _gerar_resposta_agradecimento(self, action: str) -> str:
        """Gera resposta de agradecimento para o divulgador."""
        if action == "confirmed":
            return (
                "Anotado! Obrigada pela confirmacao.\n\n"
                "Ja atualizei aqui no sistema. Qualquer coisa me avisa!"
            )
        else:
            return (
                "Entendido! Ja atualizei aqui.\n\n"
                "Obrigada por avisar. Se surgir outra oportunidade, te procuro!"
            )


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
                    message_type="incoming"
                )
            except Exception as e:
                logger.warning(f"Erro ao sincronizar com Chatwoot: {e}")

        return ProcessorResult(
            success=True,
            should_continue=False,
            metadata={"human_control": True}
        )
