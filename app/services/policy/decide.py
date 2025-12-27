"""
PolicyDecide - Motor de decisão determinística.

Sprint 15 - Policy Engine
"""
import logging
from datetime import datetime
from typing import Optional

from .types import DoctorState, PolicyDecision
from .rules import (
    RULES_IN_ORDER,
    rule_new_doctor_first_contact,
    rule_default,
)

logger = logging.getLogger(__name__)


class PolicyDecide:
    """
    Motor de decisão determinística.

    Avalia regras em ordem de prioridade e retorna a primeira
    que corresponde ao estado atual.
    """

    def decide(
        self,
        state: DoctorState,
        is_first_message: bool = False,
        conversa_status: str = "active",
        conversa_last_message_at: Optional[datetime] = None,
    ) -> PolicyDecision:
        """
        Aplica regras em ordem e retorna primeira decisão.

        Args:
            state: Estado atual do médico
            is_first_message: Se é primeira mensagem da conversa
            conversa_status: Status da conversa ('active', 'paused', etc)
            conversa_last_message_at: Timestamp da última mensagem na conversa

        Returns:
            PolicyDecision com ação e constraints
        """
        kwargs = {
            "is_first_message": is_first_message,
            "conversa_status": conversa_status,
            "conversa_last_message_at": conversa_last_message_at,
        }

        # Regra especial: primeiro contato com médico novo
        decision = rule_new_doctor_first_contact(state, **kwargs)
        if decision:
            decision.rule_id = "rule_new_doctor_first_contact"
            return decision

        # Demais regras em ordem de prioridade
        for rule_fn in RULES_IN_ORDER:
            try:
                decision = rule_fn(state, **kwargs)
                if decision:
                    decision.rule_id = rule_fn.__name__
                    return decision
            except Exception as e:
                logger.error(f"Erro na regra {rule_fn.__name__}: {e}")
                continue

        # Fallback: regra default (sempre retorna)
        decision = rule_default(state, **kwargs)
        decision.rule_id = "rule_default"
        return decision

    def _log_decision(self, state: DoctorState, decision: PolicyDecision):
        """Loga decisão para auditoria."""
        # Log resumido para INFO
        logger.info(
            f"PolicyDecide: {decision.primary_action.value} "
            f"[{state.cliente_id[:8]}...] "
            f"tone={decision.tone.value} "
            f"reason={decision.reasoning}"
        )

        # Log detalhado para DEBUG
        logger.debug(
            f"PolicyDecide details: "
            f"cliente={state.cliente_id} "
            f"allowed={decision.allowed_actions} "
            f"forbidden={decision.forbidden_actions}"
        )

        if decision.requires_human:
            logger.warning(
                f"HANDOFF REQUIRED: {state.cliente_id} - {decision.reasoning}"
            )


# Instância singleton para uso conveniente
policy_decide = PolicyDecide()


async def get_policy_decision(
    cliente_id: str,
    is_first_message: bool = False,
    conversa_status: str = "active",
    conversa_last_message_at: Optional[datetime] = None,
) -> PolicyDecision:
    """
    Função de conveniência para obter decisão de policy.

    Carrega o estado e aplica as regras.

    Args:
        cliente_id: ID do cliente/médico
        is_first_message: Se é primeira mensagem
        conversa_status: Status da conversa
        conversa_last_message_at: Última mensagem da conversa

    Returns:
        PolicyDecision
    """
    from .repository import load_doctor_state

    state = await load_doctor_state(cliente_id)

    return policy_decide.decide(
        state,
        is_first_message=is_first_message,
        conversa_status=conversa_status,
        conversa_last_message_at=conversa_last_message_at,
    )
