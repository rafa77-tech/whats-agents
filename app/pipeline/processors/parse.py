"""
Processador de parsing de mensagens.

Sprint 44 T03.3: Módulo separado.
"""
import logging
from typing import Optional

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.parser import parsear_mensagem, deve_processar

logger = logging.getLogger(__name__)


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
            motivo = "mensagem ignorada (propria/grupo/status)"
            # Se é LID sem telefone resolvido, informar motivo específico
            if mensagem.is_lid and not mensagem.telefone:
                motivo = "LID sem remoteJidAlt - sem numero real"
                logger.warning(f"LID detectado sem telefone: jid={mensagem.remote_jid}, pushName={mensagem.nome_contato}")
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para silenciosamente
                metadata={"motivo": motivo}
            )

        # Resolver telefone via Chatwoot se necessário (LID sem telefone)
        telefone = mensagem.telefone
        if mensagem.is_lid and not telefone and mensagem.chatwoot_conversation_id:
            telefone = await self._resolver_telefone_via_chatwoot(mensagem.chatwoot_conversation_id)
            if telefone:
                logger.info(f"Telefone resolvido via Chatwoot para LID: {telefone[:6]}...")
            else:
                logger.warning(f"Nao foi possivel resolver telefone para LID via Chatwoot")
                return ProcessorResult(
                    success=True,
                    should_continue=False,
                    metadata={"motivo": "LID sem telefone - Chatwoot nao retornou phone"}
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

    async def _resolver_telefone_via_chatwoot(self, conversation_id: int) -> Optional[str]:
        """Resolve telefone usando API do Chatwoot."""
        try:
            from app.services.chatwoot import chatwoot_service
            return await chatwoot_service.buscar_telefone_por_conversation_id(conversation_id)
        except Exception as e:
            logger.error(f"Erro ao resolver telefone via Chatwoot: {e}")
            return None
