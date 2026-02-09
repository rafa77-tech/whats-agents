"""
Configuracao do pipeline de mensagens.
"""
from .processor import MessageProcessor
from .core import LLMCoreProcessor
from .pre_processors import (
    IngestaoGrupoProcessor,
    ParseMessageProcessor,
    PresenceProcessor,
    LoadEntitiesProcessor,
    ChipMappingProcessor,
    BusinessEventInboundProcessor,
    ChatwootSyncProcessor,
    OptOutProcessor,
    # ForaHorarioProcessor removido - inbound deve ser 24/7 (31/12/2025)
    # Quiet hours só se aplicam a OUTBOUND proativo (campanhas, nudges)
    BotDetectionProcessor,
    MediaProcessor,
    LongMessageProcessor,
    HandoffTriggerProcessor,
    HandoffKeywordProcessor,
    HumanControlProcessor,
)
from .post_processors import (
    ValidateOutputProcessor,
    TimingProcessor,
    SendMessageProcessor,
    SaveInteractionProcessor,
    MetricsProcessor,
)
from .processors.extraction import ExtractionProcessor


def criar_pipeline() -> MessageProcessor:
    """
    Cria e configura o pipeline de mensagens.

    Returns:
        MessageProcessor configurado
    """
    pipeline = MessageProcessor()

    # Pre-processadores (ordem por prioridade)
    pipeline.add_pre_processor(IngestaoGrupoProcessor())     # 5 - ingestão de grupos (não responde)
    pipeline.add_pre_processor(ParseMessageProcessor())      # 10
    pipeline.add_pre_processor(PresenceProcessor())          # 15
    pipeline.add_pre_processor(LoadEntitiesProcessor())      # 20
    pipeline.add_pre_processor(ChipMappingProcessor())       # 21 - Sprint 26 E02: Multi-chip
    pipeline.add_pre_processor(BusinessEventInboundProcessor())  # 22 - Sprint 17 E04
    pipeline.add_pre_processor(ChatwootSyncProcessor())      # 25
    pipeline.add_pre_processor(OptOutProcessor())            # 30
    # ForaHorarioProcessor REMOVIDO (31/12/2025):
    # - Bug: bloqueava TODAS as respostas fora do horário
    # - Fix: Julia responde 24/7 a inbound (médico mandou msg = responde)
    # - Quiet hours aplicam APENAS a outbound proativo (campanhas, nudges, followups)
    pipeline.add_pre_processor(BotDetectionProcessor())      # 35
    pipeline.add_pre_processor(MediaProcessor())             # 40
    pipeline.add_pre_processor(LongMessageProcessor())       # 45
    pipeline.add_pre_processor(HandoffTriggerProcessor())    # 50
    pipeline.add_pre_processor(HandoffKeywordProcessor())   # 55 - Sprint 20: Detector keywords
    pipeline.add_pre_processor(HumanControlProcessor())      # 60

    # Core processor
    pipeline.set_core_processor(LLMCoreProcessor())

    # Pos-processadores (ordem por prioridade)
    pipeline.add_post_processor(ValidateOutputProcessor())   # 5 - valida antes de tudo
    pipeline.add_post_processor(TimingProcessor())           # 10
    pipeline.add_post_processor(SendMessageProcessor())      # 20
    pipeline.add_post_processor(SaveInteractionProcessor())  # 30
    pipeline.add_post_processor(ExtractionProcessor())       # 35 - Sprint 53: extrai dados estruturados
    pipeline.add_post_processor(MetricsProcessor())          # 40

    return pipeline


# Instancia global do pipeline
message_pipeline = criar_pipeline()
