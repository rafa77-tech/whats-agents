"""
Testes para PolicyDecide.

Sprint 15 - Policy Engine
Sprint 16 - Updated for async decide with flags
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from app.services.policy.types import (
    DoctorState,
    PermissionState,
    LifecycleStage,
    ObjectionSeverity,
    PrimaryAction,
    Tone,
)
from app.services.policy.decide import PolicyDecide


# Fixture para mockar flags (desabilitar kill switch/safe mode nos testes)
@pytest.fixture(autouse=True)
def mock_flags():
    """Desabilita flags por padrão nos testes."""
    with patch("app.services.policy.decide.is_policy_engine_enabled", return_value=True), \
         patch("app.services.policy.decide.is_safe_mode_active", return_value=False), \
         patch("app.services.policy.decide.is_rule_disabled", return_value=False):
        yield


class TestPolicyDecideOrder:
    """Testes para ordem de avaliação das regras."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_opted_out_first(self):
        """Opted_out tem prioridade sobre tudo."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.OPTED_OUT,
            # Mesmo com objeção grave
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        # Opted_out ganha, não handoff
        assert decision.primary_action == PrimaryAction.WAIT
        assert decision.requires_human is False

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_grave_objection_before_default(self):
        """Objeção grave tem prioridade sobre default."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.primary_action == PrimaryAction.HANDOFF
        assert decision.requires_human is True

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_new_doctor_before_default(self):
        """Primeiro contato tem prioridade sobre default."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        policy = PolicyDecide()
        decision = await policy.decide(
            state,
            is_first_message=True,
            conversa_status="active",
        )

        assert decision.primary_action == PrimaryAction.DISCOVERY


class TestPolicyDecideHandoff:
    """Testes para cenários de handoff."""

    @pytest.mark.asyncio
    async def test_grave_objection_handoff(self):
        """Objeção grave aciona handoff."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.requires_human is True
        assert decision.primary_action == PrimaryAction.HANDOFF
        assert decision.tone == Tone.CRISE

    @pytest.mark.asyncio
    async def test_high_objection_no_handoff(self):
        """Objeção HIGH não aciona handoff (só cautela)."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="desconfianca",
            objection_severity=ObjectionSeverity.HIGH,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.requires_human is False
        assert decision.tone == Tone.CAUTELOSO


class TestPolicyDecideWait:
    """Testes para cenários de WAIT (não responder)."""

    @pytest.mark.asyncio
    async def test_opted_out_wait(self):
        """Opted_out = WAIT."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.OPTED_OUT,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert decision.primary_action == PrimaryAction.WAIT
        assert decision.forbid_all is True


class TestPolicyDecideConstraints:
    """Testes para constraints gerados."""

    @pytest.mark.asyncio
    async def test_grave_objection_constraints(self):
        """Objeção grave tem constraints de crise."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "CRÍTICA" in decision.constraints_text or "SITUAÇÃO" in decision.constraints_text
        assert "NÃO tente resolver sozinha" in decision.constraints_text

    @pytest.mark.asyncio
    async def test_new_doctor_constraints(self):
        """Primeiro contato tem constraints de discovery."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        policy = PolicyDecide()
        decision = await policy.decide(
            state,
            is_first_message=True,
            conversa_status="active",
        )

        assert "PRIMEIRO CONTATO" in decision.constraints_text
        assert "NÃO ofereça vagas" in decision.constraints_text

    @pytest.mark.asyncio
    async def test_cooling_off_constraints(self):
        """Cooling_off tem constraints de pausa."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.COOLING_OFF,
            cooling_off_until=datetime.utcnow() + timedelta(days=3),
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "PAUSA" in decision.constraints_text
        assert "NÃO inicie contato proativo" in decision.constraints_text


class TestPolicyDecideReasoning:
    """Testes para reasoning (logs)."""

    @pytest.mark.asyncio
    async def test_reasoning_includes_state(self):
        """Reasoning inclui informações do estado."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,  # Médio para cair em default
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "permission=active" in decision.reasoning
        assert "temp=0.5" in decision.reasoning

    @pytest.mark.asyncio
    async def test_reasoning_includes_objection(self):
        """Reasoning inclui informações da objeção."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "preco" in decision.reasoning or "medium" in decision.reasoning


class TestPolicyDecideAllowedActions:
    """Testes para ações permitidas/proibidas."""

    @pytest.mark.asyncio
    async def test_active_allows_respond(self):
        """Estado active permite respond."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "respond" in decision.allowed_actions

    @pytest.mark.asyncio
    async def test_initial_forbids_offer(self):
        """Estado initial proíbe offer."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.INITIAL,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "offer" in decision.forbidden_actions

    @pytest.mark.asyncio
    async def test_grave_objection_forbids_pressure(self):
        """Objeção grave proíbe pressure e negotiate."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "pressure" in decision.forbidden_actions
        assert "negotiate" in decision.forbidden_actions

    @pytest.mark.asyncio
    async def test_hot_temperature_allows_offer(self):
        """Temperatura quente sem objeção permite offer."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.8,
        )
        policy = PolicyDecide()
        decision = await policy.decide(state)

        assert "offer" in decision.allowed_actions
        assert decision.primary_action == PrimaryAction.OFFER
