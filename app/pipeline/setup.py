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
    BusinessEventInboundProcessor,
    ChatwootSyncProcessor,
    OptOutProcessor,
    ForaHorarioProcessor,
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
    pipeline.add_pre_processor(BusinessEventInboundProcessor())  # 22 - Sprint 17 E04
    pipeline.add_pre_processor(ChatwootSyncProcessor())      # 25
    pipeline.add_pre_processor(OptOutProcessor())            # 30
    pipeline.add_pre_processor(ForaHorarioProcessor())       # 32 - Sprint 22: ACK fora do horário
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
    pipeline.add_post_processor(MetricsProcessor())          # 40

    return pipeline


# Instancia global do pipeline
message_pipeline = criar_pipeline()
