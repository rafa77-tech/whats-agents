"""
Processador de carregamento de entidades (médico, conversa).

Sprint 44 T03.3: Módulo separado.
"""
import logging

from ..base import PreProcessor, ProcessorContext, ProcessorResult
from app.services.medico import buscar_ou_criar_medico
from app.services.conversa import buscar_ou_criar_conversa

logger = logging.getLogger(__name__)


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
