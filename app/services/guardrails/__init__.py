"""
Guardrails para controle de outbound.

Sprint 17 - Ponto único de controle para envios proativos.
"""
from .types import (
    OutboundChannel,
    OutboundMethod,
    ActorType,
    OutboundContext,
    GuardrailDecision,
    GuardrailResult,
)
from .check import check_outbound_guardrails

__all__ = [
    "OutboundChannel",
    "OutboundMethod",
    "ActorType",
    "OutboundContext",
    "GuardrailDecision",
    "GuardrailResult",
    "check_outbound_guardrails",
]
