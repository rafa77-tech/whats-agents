"""
Testes para regras de produção do Policy Engine.

Sprint 15 - Policy Engine
"""
import pytest
from datetime import datetime, timedelta

from app.services.policy.types import (
    DoctorState,
    PermissionState,
    TemperatureTrend,
    TemperatureBand,
    ObjectionSeverity,
    LifecycleStage,
    PrimaryAction,
    Tone,
)
from app.services.policy.rules import (
    rule_opted_out,
    rule_cooling_off,
    rule_grave_objection,
    rule_high_objection,
    rule_medium_objection,
    rule_new_doctor_first_contact,
    rule_silence_reactivation,
    rule_cold_temperature,
    rule_hot_temperature,
    rule_default,
)


class TestRuleOptedOut:
    """Testes para rule_opted_out."""

    def test_opted_out_blocks_all(self):
        """Opt-out bloqueia todas as ações."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.OPTED_OUT,
        )
        decision = rule_opted_out(state)

        assert decision is not None
        assert decision.primary_action == PrimaryAction.WAIT
        assert decision.forbidden_actions == ["*"]
        assert decision.requires_human is False

    def test_active_not_blocked(self):
        """Estado active não é bloqueado por opted_out."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        decision = rule_opted_out(state)

        assert decision is None

    def test_none_not_blocked(self):
        """Estado none não é bloqueado por opted_out."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
        )
        decision = rule_opted_out(state)

        assert decision is None


class TestRuleCoolingOff:
    """Testes para rule_cooling_off."""

    def test_cooling_off_within_period(self):
        """Cooling_off ativo restringe ações."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.COOLING_OFF,
            cooling_off_until=datetime.utcnow() + timedelta(days=3),
        )
        decision = rule_cooling_off(state)

        assert decision is not None
        assert decision.primary_action == PrimaryAction.FOLLOWUP
        assert "offer" in decision.forbidden_actions
        assert decision.tone == Tone.CAUTELOSO

    def test_cooling_off_expired_not_triggered(self):
        """Cooling_off expirado não dispara regra."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.COOLING_OFF,
            cooling_off_until=datetime.utcnow() - timedelta(days=1),
        )
        decision = rule_cooling_off(state)

        assert decision is None

    def test_active_not_triggered(self):
        """Estado active não dispara cooling_off."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        decision = rule_cooling_off(state)

        assert decision is None


class TestRuleGraveObjection:
    """Testes para rule_grave_objection."""

    def test_grave_objection_requires_human(self):
        """Objeção grave aciona handoff."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        decision = rule_grave_objection(state)

        assert decision is not None
        assert decision.requires_human is True
        assert decision.primary_action == PrimaryAction.HANDOFF
        assert decision.tone == Tone.CRISE

    def test_grave_resolved_not_triggered(self):
        """Objeção grave resolvida não dispara."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
            objection_resolved_at=datetime.utcnow(),
        )
        decision = rule_grave_objection(state)

        assert decision is None

    def test_medium_objection_not_triggered(self):
        """Objeção medium não dispara handoff."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        decision = rule_grave_objection(state)

        assert decision is None


class TestRuleHighObjection:
    """Testes para rule_high_objection."""

    def test_high_objection_is_cautious(self):
        """Objeção high ativa tom cauteloso."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="desconfianca",
            objection_severity=ObjectionSeverity.HIGH,
        )
        decision = rule_high_objection(state)

        assert decision is not None
        assert decision.tone == Tone.CAUTELOSO
        assert decision.requires_human is False
        assert "offer" in decision.forbidden_actions


class TestRuleMediumObjection:
    """Testes para rule_medium_objection."""

    def test_medium_objection_allows_negotiation(self):
        """Objeção medium permite negociação."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        decision = rule_medium_objection(state)

        assert decision is not None
        assert decision.tone == Tone.DIRETO
        assert "negotiate" in decision.allowed_actions
        assert "pressure" in decision.forbidden_actions


class TestRuleNewDoctorFirstContact:
    """Testes para rule_new_doctor_first_contact."""

    def test_new_doctor_first_message_discovery(self):
        """Primeiro contato com médico novo é discovery."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        decision = rule_new_doctor_first_contact(
            state,
            is_first_message=True,
            conversa_status="active",
        )

        assert decision is not None
        assert decision.primary_action == PrimaryAction.DISCOVERY
        assert decision.tone == Tone.LEVE
        assert "offer_shift" in decision.forbidden_actions
        assert "ask_docs" in decision.forbidden_actions

    def test_not_first_message_not_triggered(self):
        """Segunda mensagem não dispara discovery."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        decision = rule_new_doctor_first_contact(
            state,
            is_first_message=False,
            conversa_status="active",
        )

        assert decision is None

    def test_not_novo_not_triggered(self):
        """Médico engaged não dispara discovery."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            lifecycle_stage=LifecycleStage.ENGAGED,
        )
        decision = rule_new_doctor_first_contact(
            state,
            is_first_message=True,
            conversa_status="active",
        )

        assert decision is None


class TestRuleSilenceReactivation:
    """Testes para rule_silence_reactivation."""

    def test_silence_7d_triggers_reactivation(self):
        """7 dias de silêncio + temperatura ok = reativação."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
            last_outbound_at=datetime.utcnow() - timedelta(days=10),
            last_inbound_at=datetime.utcnow() - timedelta(days=15),
        )
        decision = rule_silence_reactivation(
            state,
            conversa_status="active",
        )

        assert decision is not None
        assert decision.primary_action == PrimaryAction.REACTIVATION
        assert decision.tone == Tone.LEVE

    def test_cold_temperature_not_triggered(self):
        """Temperatura fria não dispara reativação."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.2,  # < 0.3
            last_outbound_at=datetime.utcnow() - timedelta(days=10),
        )
        decision = rule_silence_reactivation(
            state,
            conversa_status="active",
        )

        assert decision is None

    def test_recent_activity_not_triggered(self):
        """Atividade recente não dispara reativação."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
            last_outbound_at=datetime.utcnow() - timedelta(days=2),
        )
        decision = rule_silence_reactivation(
            state,
            conversa_status="active",
        )

        assert decision is None


class TestRuleDefault:
    """Testes para rule_default."""

    def test_default_is_conservative_for_none(self):
        """Default não permite offer para estado none."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
        )
        decision = rule_default(state)

        assert decision is not None
        assert "offer" in decision.forbidden_actions
        assert decision.primary_action == PrimaryAction.FOLLOWUP

    def test_default_is_conservative_for_initial(self):
        """Default não permite offer para estado initial."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.INITIAL,
        )
        decision = rule_default(state)

        assert decision is not None
        assert "offer" in decision.forbidden_actions

    def test_active_allows_respond(self):
        """Estado active permite respond e ask."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        decision = rule_default(state)

        assert decision is not None
        assert "respond" in decision.allowed_actions
        assert "ask" in decision.allowed_actions

    def test_tone_matches_temperature(self):
        """Tom varia com temperatura."""
        # Frio = cauteloso
        cold_state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.2,
        )
        cold_decision = rule_default(cold_state)
        assert cold_decision.tone == Tone.CAUTELOSO

        # Morno = direto
        warm_state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        warm_decision = rule_default(warm_state)
        assert warm_decision.tone == Tone.DIRETO

        # Quente = leve
        hot_state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.8,
        )
        hot_decision = rule_default(hot_state)
        assert hot_decision.tone == Tone.LEVE
