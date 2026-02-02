"""
Pre-processadores do pipeline.

Sprint 44 T03.3: Reorganizado em módulos separados.
Este arquivo mantém compatibilidade com imports existentes.

Estrutura modular em: app/pipeline/processors/
"""

# Re-export de todos os processadores para backwards compatibility
from .processors import (
    IngestaoGrupoProcessor,
    ParseMessageProcessor,
    PresenceProcessor,
    LoadEntitiesProcessor,
    ChipMappingProcessor,
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

__all__ = [
    "IngestaoGrupoProcessor",
    "ParseMessageProcessor",
    "PresenceProcessor",
    "LoadEntitiesProcessor",
    "ChipMappingProcessor",
    "BusinessEventInboundProcessor",
    "ChatwootSyncProcessor",
    "OptOutProcessor",
    "ForaHorarioProcessor",
    "BotDetectionProcessor",
    "MediaProcessor",
    "LongMessageProcessor",
    "HandoffTriggerProcessor",
    "HandoffKeywordProcessor",
    "HumanControlProcessor",
]
