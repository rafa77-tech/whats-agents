"""
Guardrails para controle de outbound.

Sprint 17 - Ponto único de controle para envios proativos.
Sprint 23 E01 - SendOutcome enum para rastreamento detalhado.
"""
from .types import (
    OutboundChannel,
    OutboundMethod,
    ActorType,
    OutboundContext,
    GuardrailDecision,
    GuardrailResult,
    SendOutcome,
    map_guardrail_to_outcome,
)
from .check import check_outbound_guardrails

__all__ = [
    "OutboundChannel",
    "OutboundMethod",
    "ActorType",
    "OutboundContext",
    "GuardrailDecision",
    "GuardrailResult",
    "SendOutcome",
    "map_guardrail_to_outcome",
    "check_outbound_guardrails",
]
