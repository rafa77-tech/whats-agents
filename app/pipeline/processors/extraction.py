"""
ExtractionProcessor - Extrai dados apos cada turno de conversa.

Sprint 53: Discovery Intelligence Pipeline.

Executa APOS SaveInteractionProcessor (priority 30).
Fault-tolerant: erros nao interrompem o pipeline.
"""

import logging
import os

from app.core.tasks import safe_create_task
from app.pipeline.base import PostProcessor, ProcessorContext, ProcessorResult
from app.services.extraction import (
    extrair_dados_conversa,
    ExtractionContext,
    salvar_insight,
    salvar_memorias_extraidas,
    atualizar_dados_cliente,
)

logger = logging.getLogger(__name__)

# Feature flag
EXTRACTION_ENABLED = os.getenv("EXTRACTION_ENABLED", "true").lower() == "true"
AUTO_UPDATE_THRESHOLD = float(os.getenv("EXTRACTION_AUTO_UPDATE_THRESHOLD", "0.7"))


class ExtractionProcessor(PostProcessor):
    """
    Extrai dados estruturados de cada turno de conversa.

    Priority: 35 (apos save:30, antes de metrics:40)

    Executa em background para nao atrasar a resposta.
    Falhas sao logadas mas nao interrompem o pipeline.
    """

    name = "extraction"
    priority = 35

    def should_run(self, context: ProcessorContext) -> bool:
        """So roda se ha mensagem do medico, resposta da Julia e medico identificado."""
        if not EXTRACTION_ENABLED:
            return False

        return bool(context.mensagem_texto and context.medico and context.conversa)

    async def process(self, context: ProcessorContext, response: str) -> ProcessorResult:
        """
        Extrai dados e persiste em background.

        Falhas sao logadas mas nao interrompem o pipeline.
        """
        # Se nao tem resposta, nada a fazer
        if not response:
            return ProcessorResult(success=True, response=response)

        # Executar em background para nao atrasar resposta
        safe_create_task(
            self._extrair_e_persistir(context, response), name=f"extraction_{context.telefone[-4:]}"
        )

        return ProcessorResult(success=True, response=response)

    async def _extrair_e_persistir(self, context: ProcessorContext, response: str) -> None:
        """Task em background para extracao e persistencia."""
        try:
            # 1. Montar contexto
            extraction_context = ExtractionContext(
                mensagem_medico=context.mensagem_texto,
                resposta_julia=response,
                nome_medico=context.medico.get("primeiro_nome", "Medico"),
                especialidade_cadastrada=context.medico.get("especialidade"),
                regiao_cadastrada=context.medico.get("cidade"),
                campanha_id=context.metadata.get("campanha_id"),
                tipo_campanha=context.metadata.get("tipo_campanha"),
                conversa_id=context.conversa.get("id"),
                cliente_id=context.medico.get("id"),
            )

            # 2. Extrair
            extraction = await extrair_dados_conversa(extraction_context)

            # 3. Salvar em conversation_insights
            await salvar_insight(
                conversation_id=context.conversa.get("id"),
                interaction_id=context.metadata.get("inbound_interaction_id"),
                campaign_id=context.metadata.get("campanha_id"),
                cliente_id=context.medico.get("id"),
                extraction=extraction,
            )

            # 4. Salvar memorias RAG (preferencias e restricoes)
            if extraction.preferencias or extraction.restricoes:
                await salvar_memorias_extraidas(
                    cliente_id=context.medico.get("id"),
                    extraction=extraction,
                    conversa_id=context.conversa.get("id"),
                )

            # 5. Atualizar dados do cliente se alta confianca
            if extraction.dados_corrigidos and extraction.confianca >= AUTO_UPDATE_THRESHOLD:
                await atualizar_dados_cliente(
                    cliente_id=context.medico.get("id"),
                    dados=extraction.dados_corrigidos,
                    confianca=extraction.confianca,
                )
                logger.info(
                    f"[Extraction] Dados do cliente atualizados: "
                    f"{list(extraction.dados_corrigidos.keys())}"
                )

            logger.info(
                f"[Extraction] Concluido: interesse={extraction.interesse.value}, "
                f"score={extraction.interesse_score:.2f}, "
                f"proximo_passo={extraction.proximo_passo.value}"
            )

        except Exception as e:
            # NUNCA deixar erro escapar - pipeline deve continuar
            logger.error(
                f"[Extraction] Erro (nao-bloqueante): {e}",
                exc_info=True,
                extra={
                    "cliente_id": context.medico.get("id") if context.medico else None,
                    "conversa_id": context.conversa.get("id") if context.conversa else None,
                },
            )
