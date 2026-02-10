"""
Pipeline de processamento de mensagens.

Permite adicionar pre e pos processadores de forma modular.
"""

from .processor import MessageProcessor, ProcessorResult
from .base import PreProcessor, PostProcessor, ProcessorContext

__all__ = [
    "MessageProcessor",
    "ProcessorResult",
    "ProcessorContext",
    "PreProcessor",
    "PostProcessor",
]
