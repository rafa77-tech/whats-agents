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
