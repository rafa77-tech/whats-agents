"""
Services de handoff IA <-> Humano.

Sprint 10 - S10.E3.4
"""
from .messages import (
    MENSAGENS_TRANSICAO,
    obter_mensagem_transicao,
)

from .flow import (
    iniciar_handoff,
    finalizar_handoff,
    resolver_handoff,
)

from .repository import (
    listar_handoffs_pendentes,
    obter_metricas_handoff,
    verificar_handoff_ativo,
)


__all__ = [
    # Messages
    "MENSAGENS_TRANSICAO",
    "obter_mensagem_transicao",
    # Flow
    "iniciar_handoff",
    "finalizar_handoff",
    "resolver_handoff",
    # Repository
    "listar_handoffs_pendentes",
    "obter_metricas_handoff",
    "verificar_handoff_ativo",
]
