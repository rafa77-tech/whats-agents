"""
Structured Logging para Mode Router.

Sprint 29 - Conversation Mode

Cada decisão é registrada para auditoria e debugging.
Este é o "black box recorder" da Julia.
Quando der ruim, explica em 30 segundos.
"""

import logging
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from app.core.timezone import agora_utc
from .capabilities import CAPABILITIES_BY_MODE

logger = logging.getLogger(__name__)


@dataclass
class ModeDecisionLog:
    """Registro estruturado de decisão do Mode Router."""

    timestamp: datetime
    conversa_id: str
    current_mode: str
    detected_intent: str
    intent_confidence: float
    proposed_mode: Optional[str]
    validator_decision: str  # APPLY, PENDING, CONFIRM, CANCEL, REJECT
    transition_reason: str
    capabilities_version: str  # Hash do CAPABILITIES_BY_MODE

    def to_dict(self) -> dict:
        """Converte para dict serializável."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


def get_capabilities_version() -> str:
    """Gera hash do CAPABILITIES_BY_MODE para versionamento."""
    config_str = str(CAPABILITIES_BY_MODE)
    return hashlib.md5(config_str.encode()).hexdigest()[:8]


def log_mode_decision(
    conversa_id: str,
    current_mode: str,
    detected_intent: str,
    intent_confidence: float,
    proposed_mode: Optional[str],
    validator_decision: str,
    transition_reason: str,
) -> ModeDecisionLog:
    """
    Registra decisão do Mode Router.

    Este log é o "black box recorder" da Julia.
    Quando der ruim, explica em 30 segundos.

    Args:
        conversa_id: ID da conversa
        current_mode: Modo atual
        detected_intent: Intent detectado
        intent_confidence: Confiança do intent
        proposed_mode: Modo proposto (ou None)
        validator_decision: Decisão (APPLY, PENDING, CONFIRM, CANCEL, REJECT)
        transition_reason: Motivo da decisão

    Returns:
        ModeDecisionLog com registro completo
    """
    log_entry = ModeDecisionLog(
        timestamp=agora_utc(),
        conversa_id=conversa_id,
        current_mode=current_mode,
        detected_intent=detected_intent,
        intent_confidence=intent_confidence,
        proposed_mode=proposed_mode,
        validator_decision=validator_decision,
        transition_reason=transition_reason,
        capabilities_version=get_capabilities_version(),
    )

    # Log estruturado
    logger.info(f"MODE_DECISION: {json.dumps(log_entry.to_dict())}")

    return log_entry


def log_violation_attempt(
    conversa_id: str,
    mode: str,
    violation_type: str,  # "tool" ou "claim"
    attempted: str,
) -> None:
    """
    Registra tentativa de violação de capabilities.

    Útil para ajustar prompt ou matriz quando violação é frequente.

    Args:
        conversa_id: ID da conversa
        mode: Modo atual
        violation_type: Tipo de violação ("tool" ou "claim")
        attempted: O que foi tentado
    """
    logger.warning(
        f"VIOLATION_ATTEMPT: conversa={conversa_id} mode={mode} "
        f"type={violation_type} attempted={attempted}"
    )


def log_transition_applied(
    conversa_id: str,
    from_mode: str,
    to_mode: str,
    trigger: str,
    evidence: str,
) -> None:
    """
    Registra transição de modo aplicada.

    Args:
        conversa_id: ID da conversa
        from_mode: Modo anterior
        to_mode: Modo novo
        trigger: O que disparou a transição
        evidence: Evidência da transição
    """
    logger.info(
        f"MODE_TRANSITION: conversa={conversa_id} "
        f"{from_mode} → {to_mode} "
        f"trigger={trigger} evidence='{evidence}'"
    )


def log_pending_created(
    conversa_id: str,
    current_mode: str,
    pending_mode: str,
) -> None:
    """
    Registra criação de pending_transition.

    Args:
        conversa_id: ID da conversa
        current_mode: Modo atual
        pending_mode: Modo aguardando confirmação
    """
    logger.info(
        f"PENDING_CREATED: conversa={conversa_id} "
        f"current={current_mode} pending={pending_mode} "
        f"(aguardando micro-confirmação)"
    )


def log_pending_resolved(
    conversa_id: str,
    pending_mode: str,
    confirmed: bool,
    reason: str,
) -> None:
    """
    Registra resolução de pending_transition.

    Args:
        conversa_id: ID da conversa
        pending_mode: Modo que estava pendente
        confirmed: Se foi confirmado ou cancelado
        reason: Motivo da resolução
    """
    status = "CONFIRMED" if confirmed else "CANCELLED"
    logger.info(
        f"PENDING_{status}: conversa={conversa_id} pending={pending_mode} reason='{reason}'"
    )
