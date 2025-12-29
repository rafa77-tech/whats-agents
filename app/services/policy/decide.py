"""
PolicyDecide - Motor de decisão determinística.

Sprint 15 - Policy Engine
Sprint 16 - Kill Switch e Safe Mode
"""
import logging
from datetime import datetime
from typing import Optional

from .types import DoctorState, PolicyDecision, PrimaryAction, Tone
from .rules import (
    RULES_IN_ORDER,
    rule_new_doctor_first_contact,
    rule_default,
)
from .flags import (
    is_policy_engine_enabled,
    is_safe_mode_active,
    get_safe_mode_action,
    is_rule_disabled,
)

logger = logging.getLogger(__name__)


class PolicyDecide:
    """
    Motor de decisão determinística.

    Avalia regras em ordem de prioridade e retorna a primeira
    que corresponde ao estado atual.

    Sprint 16: Integração com kill switch e safe mode.
    """

    async def decide(
        self,
        state: DoctorState,
        is_first_message: bool = False,
        conversa_status: str = "active",
        conversa_last_message_at: Optional[datetime] = None,
        is_inbound: bool = True,
        flags_override: Optional[dict] = None,
    ) -> PolicyDecision:
        """
        Aplica regras em ordem e retorna primeira decisão.

        Sprint 16: Verifica flags antes de aplicar regras.

        Args:
            state: Estado atual do médico
            is_first_message: Se é primeira mensagem da conversa
            conversa_status: Status da conversa ('active', 'paused', etc)
            conversa_last_message_at: Timestamp da última mensagem na conversa
            is_inbound: Se é mensagem recebida do médico (True) ou campanha (False)
            flags_override: Override de flags para replay determinístico

        Returns:
            PolicyDecision com ação e constraints
        """
        # Sprint 16 Fix: Usar flags_override se fornecido (para replay)
        if flags_override:
            policy_enabled = flags_override.get("policy_engine_enabled", True)
            safe_mode = flags_override.get("safe_mode_active", False)
            safe_action = flags_override.get("safe_mode_action", "wait")
            disabled_rules = flags_override.get("disabled_rules", [])
        else:
            policy_enabled = await is_policy_engine_enabled()
            safe_mode = await is_safe_mode_active()
            safe_action = await get_safe_mode_action() if safe_mode else "wait"
            disabled_rules = None  # Será verificado por regra

        # Sprint 16: Kill switch - desabilita policy engine
        # Fix: Inbound = handoff educado, Outbound = wait silencioso
        if not policy_enabled:
            logger.warning(f"Policy Engine desabilitado via kill switch (is_inbound={is_inbound})")
            if is_inbound:
                # Mensagem do médico: criar handoff para humano atender
                return PolicyDecision(
                    primary_action=PrimaryAction.HANDOFF,
                    allowed_actions=["acknowledge"],
                    forbidden_actions=[],
                    forbid_all=True,
                    tone=Tone.CAUTELOSO,
                    requires_human=True,
                    constraints_text="[MANUTENÇÃO] Sistema temporariamente indisponível. Encaminhando para atendimento.",
                    reasoning="kill_switch active, inbound → handoff to human",
                    rule_id="kill_switch_inbound",
                )
            else:
                # Campanha/outbound: silencioso, não enviar nada
                return PolicyDecision(
                    primary_action=PrimaryAction.WAIT,
                    allowed_actions=[],
                    forbidden_actions=[],
                    forbid_all=True,
                    tone=Tone.DIRETO,
                    requires_human=False,
                    constraints_text="[SISTEMA PAUSADO - Campanhas suspensas]",
                    reasoning="kill_switch active, outbound → wait silently",
                    rule_id="kill_switch_outbound",
                )

        # Sprint 16: Safe mode - ação de emergência
        if safe_mode:
            logger.warning(f"Safe mode ativo: {safe_action}")

            if safe_action == "handoff":
                return PolicyDecision(
                    primary_action=PrimaryAction.HANDOFF,
                    allowed_actions=[],
                    forbidden_actions=[],
                    forbid_all=True,
                    tone=Tone.CRISE,
                    requires_human=True,
                    constraints_text="[SAFE MODE - Transferir para humano]",
                    reasoning="safe_mode enabled with handoff action",
                    rule_id="safe_mode_handoff",
                )
            else:  # "wait" (default)
                return PolicyDecision(
                    primary_action=PrimaryAction.WAIT,
                    allowed_actions=[],
                    forbidden_actions=[],
                    forbid_all=True,
                    tone=Tone.DIRETO,
                    requires_human=False,
                    constraints_text="[SAFE MODE - Não responder]",
                    reasoning="safe_mode enabled with wait action",
                    rule_id="safe_mode_wait",
                )

        kwargs = {
            "is_first_message": is_first_message,
            "conversa_status": conversa_status,
            "conversa_last_message_at": conversa_last_message_at,
        }

        # Helper para verificar regra desabilitada (com suporte a override)
        async def _is_disabled(rule_name: str) -> bool:
            if disabled_rules is not None:
                return rule_name in disabled_rules
            return await is_rule_disabled(rule_name)

        # Regra especial: primeiro contato com médico novo
        rule_name = "rule_new_doctor_first_contact"
        if not await _is_disabled(rule_name):
            decision = rule_new_doctor_first_contact(state, **kwargs)
            if decision:
                decision.rule_id = rule_name
                return decision
        else:
            logger.debug(f"Regra {rule_name} desabilitada")

        # Demais regras em ordem de prioridade
        for rule_fn in RULES_IN_ORDER:
            rule_name = rule_fn.__name__
            try:
                # Sprint 16: Verificar se regra está desabilitada
                if await _is_disabled(rule_name):
                    logger.debug(f"Regra {rule_name} desabilitada")
                    continue

                decision = rule_fn(state, **kwargs)
                if decision:
                    decision.rule_id = rule_name
                    return decision
            except Exception as e:
                logger.error(f"Erro na regra {rule_name}: {e}")
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

    # Sprint 16: decide agora é async
    return await policy_decide.decide(
        state,
        is_first_message=is_first_message,
        conversa_status=conversa_status,
        conversa_last_message_at=conversa_last_message_at,
    )
