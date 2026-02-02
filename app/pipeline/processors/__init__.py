"""
Pre-processadores do pipeline - Estrutura modular.

Sprint 44 T03.3: Separação de pre_processors.py em módulos individuais.

Este módulo exporta todos os pre-processadores para manter
compatibilidade com imports existentes.
"""

from .ingestao_grupo import IngestaoGrupoProcessor
from .parse import ParseMessageProcessor
from .presence import PresenceProcessor
from .entities import LoadEntitiesProcessor
from .chip_mapping import ChipMappingProcessor
from .business_events import BusinessEventInboundProcessor
from .chatwoot import ChatwootSyncProcessor
from .optout import OptOutProcessor
from .fora_horario import ForaHorarioProcessor
from .bot_detection import BotDetectionProcessor
from .media import MediaProcessor
from .long_message import LongMessageProcessor
from .handoff import HandoffTriggerProcessor, HandoffKeywordProcessor
from .human_control import HumanControlProcessor

__all__ = [
    # Ordem por prioridade
    "IngestaoGrupoProcessor",      # 5
    "ParseMessageProcessor",        # 10
    "PresenceProcessor",            # 15
    "LoadEntitiesProcessor",        # 20
    "ChipMappingProcessor",         # 21
    "BusinessEventInboundProcessor", # 22
    "ChatwootSyncProcessor",        # 25
    "OptOutProcessor",              # 30
    "ForaHorarioProcessor",         # 32
    "BotDetectionProcessor",        # 35
    "MediaProcessor",               # 40
    "LongMessageProcessor",         # 45
    "HandoffTriggerProcessor",      # 50
    "HandoffKeywordProcessor",      # 55
    "HumanControlProcessor",        # 60
]
