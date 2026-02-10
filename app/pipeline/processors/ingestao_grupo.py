"""
Processador de ingestão de mensagens de grupo.

Sprint 44 T03.3: Módulo separado.
"""

import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.parser import parsear_mensagem, is_grupo

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
                        "mensagem_id": str(mensagem_id) if mensagem_id else None,
                    },
                )
        except Exception as e:
            logger.error(f"Erro na ingestão de grupo: {e}", exc_info=True)

        return ProcessorResult(
            success=True, should_continue=False, metadata={"motivo": "mensagem_grupo_erro_ingestao"}
        )
