"""
Logger estruturado para Policy Engine.

Sprint 15 - Policy Engine
Requisitos:
- Cada decisão logada com policy_version
- Cada decisão logada com rule_matched
- Cada decisão logada com doctor_state_input mínimo
- Estrutura JSON para análise posterior
"""
import json
import logging
from datetime import datetime
from typing import Optional

from .types import DoctorState, PolicyDecision
from .version import POLICY_VERSION

logger = logging.getLogger(__name__)


def _serialize_doctor_state_input(state: DoctorState) -> dict:
    """
    Serializa campos mínimos do DoctorState para reprodutibilidade.

    Campos incluídos são os essenciais para replay da decisão.
    """
    return {
        "cliente_id": state.cliente_id,
        "permission_state": state.permission_state.value,
        "temperature": state.temperature,
        "temperature_band": state.temperature_band.value,
        "temperature_trend": state.temperature_trend.value,
        "lifecycle_stage": state.lifecycle_stage.value,
        "risk_tolerance": state.risk_tolerance.value,
        "active_objection": state.active_objection,
        "objection_severity": state.objection_severity.value if state.objection_severity else None,
        "contact_count_7d": state.contact_count_7d,
        "cooling_off_until": state.cooling_off_until.isoformat() if state.cooling_off_until else None,
        "last_inbound_at": state.last_inbound_at.isoformat() if state.last_inbound_at else None,
        "last_outbound_at": state.last_outbound_at.isoformat() if state.last_outbound_at else None,
    }


def log_policy_decision(
    state: DoctorState,
    decision: PolicyDecision,
    conversation_id: Optional[str] = None,
    message_id: Optional[str] = None,
    is_first_message: bool = False,
    conversa_status: str = "active",
) -> None:
    """
    Loga decisão de policy em formato estruturado.

    Este log é a trilha de auditoria principal do Policy Engine.
    Permite:
    - Rastrear qual regra disparou
    - Reproduzir decisões com doctor_state_input
    - Versionar mudanças na policy
    - Debugar comportamentos inesperados

    Args:
        state: Estado do médico usado na decisão
        decision: Decisão tomada pelo PolicyDecide
        conversation_id: ID da conversa (opcional)
        message_id: ID da mensagem que triggerou (opcional)
        is_first_message: Se é primeira mensagem da conversa
        conversa_status: Status da conversa
    """
    log_event = {
        "event": "policy_decision",
        "ts": datetime.utcnow().isoformat(),
        "policy_version": POLICY_VERSION,
        # Identificadores
        "cliente_id": state.cliente_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        # Decisão
        "rule_matched": decision.rule_id,
        "primary_action": decision.primary_action.value,
        "tone": decision.tone.value,
        "requires_human": decision.requires_human,
        "allowed_actions": decision.allowed_actions,
        "forbidden_actions": decision.forbidden_actions,
        # Contexto da chamada
        "is_first_message": is_first_message,
        "conversa_status": conversa_status,
        # Estado de entrada (para replay)
        "doctor_state_input": _serialize_doctor_state_input(state),
        # Reasoning (para debug)
        "reasoning": decision.reasoning,
    }

    # Log em formato JSON estruturado
    logger.info(
        f"POLICY_DECISION: {json.dumps(log_event, ensure_ascii=False)}"
    )

    # Log resumido para console (human-readable)
    logger.debug(
        f"Policy: {decision.rule_id} → {decision.primary_action.value} "
        f"[{state.cliente_id[:8]}...] tone={decision.tone.value}"
    )

    # Warning para handoff
    if decision.requires_human:
        logger.warning(
            f"HANDOFF_REQUIRED: cliente={state.cliente_id} "
            f"rule={decision.rule_id} reason={decision.reasoning}"
        )


def log_policy_effect(
    cliente_id: str,
    conversation_id: Optional[str],
    message_id: Optional[str],
    rule_matched: str,
    effect: str,
    details: Optional[dict] = None,
) -> None:
    """
    Loga efeito pós-envio da policy.

    Registra o que aconteceu após a decisão:
    - message_sent: mensagem enviada com sucesso
    - handoff_triggered: handoff iniciado
    - wait_applied: decisão de esperar
    - error: erro no envio

    Args:
        cliente_id: ID do cliente
        conversation_id: ID da conversa
        message_id: ID da mensagem
        rule_matched: Regra que gerou a decisão original
        effect: Tipo de efeito (message_sent, handoff_triggered, wait_applied, error)
        details: Detalhes adicionais (opcional)
    """
    log_event = {
        "event": "policy_effect",
        "ts": datetime.utcnow().isoformat(),
        "policy_version": POLICY_VERSION,
        "cliente_id": cliente_id,
        "conversation_id": conversation_id,
        "message_id": message_id,
        "rule_matched": rule_matched,
        "effect": effect,
        "details": details or {},
    }

    logger.info(
        f"POLICY_EFFECT: {json.dumps(log_event, ensure_ascii=False)}"
    )
