"""
Processador principal de mensagens.
"""

import logging

from .base import ProcessorContext, ProcessorResult, PreProcessor, PostProcessor

logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Orquestra o pipeline de processamento de mensagens.

    Uso:
        processor = MessageProcessor()
        processor.add_pre_processor(OptOutProcessor())
        processor.add_pre_processor(MediaProcessor())
        processor.add_post_processor(ValidateOutputProcessor())
        processor.add_post_processor(SendMessageProcessor())

        result = await processor.process(mensagem)
    """

    def __init__(self):
        self.pre_processors: list[PreProcessor] = []
        self.post_processors: list[PostProcessor] = []
        self._core_processor = None

    def add_pre_processor(self, processor: PreProcessor) -> "MessageProcessor":
        """Adiciona pre-processador e reordena por prioridade."""
        self.pre_processors.append(processor)
        self.pre_processors.sort(key=lambda p: p.priority)
        return self

    def add_post_processor(self, processor: PostProcessor) -> "MessageProcessor":
        """Adiciona pos-processador e reordena por prioridade."""
        self.post_processors.append(processor)
        self.post_processors.sort(key=lambda p: p.priority)
        return self

    def set_core_processor(self, processor) -> "MessageProcessor":
        """Define o processador core (LLM)."""
        self._core_processor = processor
        return self

    async def _run_post_processors_on_early_exit(
        self, context: ProcessorContext, response: str
    ) -> ProcessorResult:
        """
        Roda pos-processadores necessarios quando pipeline para cedo.

        Usado quando um pre-processador retorna resposta (opt-out, media, etc).
        Roda apenas: SendMessage, SaveInteraction.
        """
        logger.debug("Rodando pos-processadores para saida antecipada")

        for processor in self.post_processors:
            # Pular processadores nao essenciais
            if processor.name in ["timing", "metrics"]:
                continue

            if not processor.should_run(context):
                continue

            logger.debug(f"Rodando pos (early exit): {processor.name}")
            result = await processor.process(context, response)

            if not result.success:
                logger.warning(f"Pos-processor {processor.name} falhou: {result.error}")
                continue

            if result.response:
                response = result.response

        return ProcessorResult(success=True, response=response, should_continue=False)

    async def process(self, mensagem_raw: dict) -> ProcessorResult:
        """
        Processa mensagem pelo pipeline completo.

        Args:
            mensagem_raw: Payload da mensagem (webhook)

        Returns:
            ProcessorResult final
        """
        # Criar contexto inicial
        context = ProcessorContext(mensagem_raw=mensagem_raw)

        # Capturar tempo de inicio para metricas
        import time

        context.metadata["tempo_inicio"] = mensagem_raw.get("_tempo_inicio", time.time())

        try:
            # FASE 1: Pre-processadores
            logger.debug(f"Iniciando {len(self.pre_processors)} pre-processadores")

            for processor in self.pre_processors:
                if not processor.should_run(context):
                    logger.debug(f"Pulando {processor.name}")
                    continue

                logger.debug(f"Rodando pre: {processor.name}")
                result = await processor.process(context)

                if not result.success:
                    logger.warning(f"Pre-processor {processor.name} falhou: {result.error}")
                    return result

                if not result.should_continue:
                    logger.info(f"Pipeline interrompido por {processor.name}")
                    # Se tem resposta, rodar pos-processadores de envio
                    if result.response:
                        return await self._run_post_processors_on_early_exit(
                            context, result.response
                        )
                    return result

            # FASE 2: Processador core (LLM)
            if self._core_processor is None:
                logger.error("Core processor nao configurado")
                return ProcessorResult(success=False, error="Core processor nao configurado")

            logger.debug("Rodando core processor")
            core_result = await self._core_processor.process(context)

            if not core_result.success:
                logger.error(f"Core processor falhou: {core_result.error}")
                return core_result

            response = core_result.response or ""

            # FASE 3: Pos-processadores
            logger.debug(f"Iniciando {len(self.post_processors)} pos-processadores")

            for processor in self.post_processors:
                if not processor.should_run(context):
                    logger.debug(f"Pulando {processor.name}")
                    continue

                logger.debug(f"Rodando pos: {processor.name}")
                result = await processor.process(context, response)

                if not result.success:
                    logger.warning(f"Pos-processor {processor.name} falhou: {result.error}")
                    # Pos-processors podem falhar sem parar tudo
                    continue

                # Atualizar resposta se modificada
                if result.response:
                    response = result.response

            # Sucesso
            return ProcessorResult(success=True, response=response)

        except Exception as e:
            logger.error(f"Erro no pipeline: {e}", exc_info=True)
            return ProcessorResult(success=False, error=str(e))
