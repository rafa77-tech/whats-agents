"""
Processador de opt-out.

Sprint 44 T03.3: Módulo separado.
"""

import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.optout import detectar_optout, processar_optout, get_mensagem_optout

logger = logging.getLogger(__name__)


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
        sucesso = await processar_optout(cliente_id=context.medico["id"], telefone=context.telefone)

        if sucesso:
            # Usar template dinamico do banco
            mensagem_optout = await get_mensagem_optout()
            return ProcessorResult(
                success=True,
                should_continue=False,  # Para o pipeline
                response=mensagem_optout,
                metadata={"optout": True},
            )

        return ProcessorResult(success=True)
