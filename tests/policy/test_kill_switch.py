"""
Testes para kill switch no PolicyDecide.

Sprint 16 - Kill Switch Integration
Sprint 16 Fix - Inbound vs Outbound handling
"""
import pytest
from unittest.mock import patch, AsyncMock

from app.services.policy.decide import PolicyDecide
from app.services.policy.types import (
    DoctorState,
    PermissionState,
    PrimaryAction,
    Tone,
)


class TestKillSwitch:
    """Testes para kill switch do Policy Engine."""

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_policy_engine_disabled_inbound(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Kill switch para inbound = handoff para humano."""
        mock_enabled.return_value = False

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state, is_inbound=True)

        assert decision.primary_action == PrimaryAction.HANDOFF
        assert decision.rule_id == "kill_switch_inbound"
        assert decision.forbid_all is True
        assert decision.requires_human is True
        assert "acknowledge" in decision.allowed_actions

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_policy_engine_disabled_outbound(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Kill switch para outbound = wait silencioso."""
        mock_enabled.return_value = False

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state, is_inbound=False)

        assert decision.primary_action == PrimaryAction.WAIT
        assert decision.rule_id == "kill_switch_outbound"
        assert decision.forbid_all is True
        assert decision.requires_human is False

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_safe_mode_wait(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Safe mode com ação wait."""
        mock_enabled.return_value = True
        mock_safe.return_value = True
        mock_action.return_value = "wait"

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.primary_action == PrimaryAction.WAIT
        assert decision.rule_id == "safe_mode_wait"
        assert decision.forbid_all is True
        assert decision.requires_human is False

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_safe_mode_handoff(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Safe mode com ação handoff."""
        mock_enabled.return_value = True
        mock_safe.return_value = True
        mock_action.return_value = "handoff"

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.primary_action == PrimaryAction.HANDOFF
        assert decision.rule_id == "safe_mode_handoff"
        assert decision.forbid_all is True
        assert decision.requires_human is True
        assert decision.tone == Tone.CRISE

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_rule_disabled_skipped(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Regras desabilitadas são puladas."""
        mock_enabled.return_value = True
        mock_safe.return_value = False
        # Desabilitar a regra de primeiro contato
        mock_rule.side_effect = lambda r: r == "rule_new_doctor_first_contact"

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.NONE,  # Normalmente acionaria first_contact
        )
        policy = PolicyDecide()
        decision = await policy.decide(state, is_first_message=True)

        # Não deve ser first_contact porque foi desabilitada
        assert decision.rule_id != "rule_new_doctor_first_contact"

    @pytest.mark.asyncio
    @patch("app.services.policy.decide.is_rule_disabled")
    @patch("app.services.policy.decide.get_safe_mode_action")
    @patch("app.services.policy.decide.is_safe_mode_active")
    @patch("app.services.policy.decide.is_policy_engine_enabled")
    async def test_normal_operation(
        self, mock_enabled, mock_safe, mock_action, mock_rule
    ):
        """Operação normal quando tudo está habilitado."""
        mock_enabled.return_value = True
        mock_safe.return_value = False
        mock_rule.return_value = False

        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        # Deve retornar decisão normal (não kill_switch nem safe_mode)
        assert decision.rule_id not in ["kill_switch", "safe_mode_wait", "safe_mode_handoff"]
        assert decision.primary_action != PrimaryAction.WAIT or decision.rule_id != "kill_switch"
