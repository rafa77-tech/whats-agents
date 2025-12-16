"""
[DEPRECATED] Modulo de compatibilidade para handoff.

Este arquivo foi reorganizado em:
- app/services/handoff/messages.py
- app/services/handoff/flow.py
- app/services/handoff/repository.py

Use: from app.services.handoff import iniciar_handoff, finalizar_handoff
Sprint 10 - S10.E3.4
"""
import warnings

warnings.warn(
    "handoff.py is deprecated. Use app.services.handoff instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do novo modulo para manter compatibilidade
from app.services.handoff import (
    # Messages
    MENSAGENS_TRANSICAO,
    obter_mensagem_transicao,
    # Flow
    iniciar_handoff,
    finalizar_handoff,
    resolver_handoff,
    # Repository
    listar_handoffs_pendentes,
    obter_metricas_handoff,
    verificar_handoff_ativo,
)

__all__ = [
    "MENSAGENS_TRANSICAO",
    "obter_mensagem_transicao",
    "iniciar_handoff",
    "finalizar_handoff",
    "resolver_handoff",
    "listar_handoffs_pendentes",
    "obter_metricas_handoff",
    "verificar_handoff_ativo",
]
