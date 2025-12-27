"""
Testes para StateUpdate do Policy Engine.

Sprint 15 - Policy Engine
"""
import pytest
from datetime import datetime, timedelta

from app.services.policy.types import (
    DoctorState,
    PermissionState,
    TemperatureTrend,
    LifecycleStage,
    ObjectionSeverity,
)
from app.services.policy.state_update import StateUpdate


class TestOnInboundMessage:
    """Testes para on_inbound_message."""

    def test_temperature_increases_on_response(self):
        """Temperatura aumenta quando médico responde."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi, tudo bem!", None)

        assert updates["temperature"] == 0.6
        assert updates["temperature_trend"] == TemperatureTrend.WARMING.value

    def test_temperature_capped_at_1(self):
        """Temperatura não ultrapassa 1.0."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.95,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi!", None)

        assert updates["temperature"] == 1.0

    def test_none_promoted_to_active(self):
        """Estado 'none' é promovido para 'active' quando médico responde."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi!", None)

        assert updates["permission_state"] == PermissionState.ACTIVE.value

    def test_initial_promoted_to_active(self):
        """Estado 'initial' é promovido para 'active' quando médico responde."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.INITIAL,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi!", None)

        assert updates["permission_state"] == PermissionState.ACTIVE.value

    def test_cooling_off_returns_to_active(self):
        """Médico em cooling_off volta para active se responder."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.COOLING_OFF,
            cooling_off_until=datetime.utcnow() + timedelta(days=5),
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi!", None)

        assert updates["permission_state"] == PermissionState.ACTIVE.value
        assert updates["cooling_off_until"] is None

    def test_novo_promoted_to_engaged(self):
        """Lifecycle 'novo' é promovido para 'engaged' quando médico responde."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(state, "Oi!", None)

        assert updates["lifecycle_stage"] == LifecycleStage.ENGAGED.value


class TestOptOutDetection:
    """Testes para detecção de opt-out."""

    def test_opt_out_is_terminal(self):
        """Opt-out seta opted_out, não cooling_off."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(
            state,
            "não me procure mais",
            {"tem_objecao": True, "tipo": "opt_out", "subtipo": None},
        )

        assert updates["permission_state"] == PermissionState.OPTED_OUT.value
        assert updates["active_objection"] == "opt_out"
        assert updates["objection_severity"] == ObjectionSeverity.GRAVE.value

    def test_opt_out_by_keyword(self):
        """Opt-out detectado por keyword na mensagem."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(
            state,
            "me tire da lista por favor",
            {"tem_objecao": True, "tipo": "comunicacao", "subtipo": None},
        )

        assert updates["permission_state"] == PermissionState.OPTED_OUT.value


class TestGraveObjection:
    """Testes para objeções graves."""

    def test_grave_sets_cooling_off(self):
        """Objeção grave seta cooling_off com prazo."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(
            state,
            "vocês são golpistas, vou denunciar!",
            {"tem_objecao": True, "tipo": "ameaca", "subtipo": None},
        )

        assert updates["permission_state"] == PermissionState.COOLING_OFF.value
        assert updates["cooling_off_until"] is not None
        assert updates["objection_severity"] == ObjectionSeverity.GRAVE.value


class TestObjectionPersistence:
    """Testes para persistência de objeção."""

    def test_objection_not_cleared_automatically(self):
        """Objeção não é limpa sem resolução explícita."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(
            state,
            "ok, entendi",
            None,  # Sem nova objeção
        )

        # NÃO deve ter limpado a objeção
        assert "active_objection" not in updates
        assert "objection_severity" not in updates

    def test_new_objection_overwrites(self):
        """Nova objeção sobrescreve a anterior."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        updater = StateUpdate()
        updates = updater.on_inbound_message(
            state,
            "ainda acho caro demais, e agora desconfio de vocês",
            {"tem_objecao": True, "tipo": "desconfianca", "subtipo": None},
        )

        assert updates["active_objection"] == "desconfianca"


class TestOnOutboundMessage:
    """Testes para on_outbound_message."""

    def test_updates_last_outbound(self):
        """Atualiza last_outbound_at e actor."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            contact_count_7d=5,
        )
        updater = StateUpdate()
        updates = updater.on_outbound_message(state, actor="julia")

        assert "last_outbound_at" in updates
        assert updates["last_outbound_actor"] == "julia"
        assert updates["contact_count_7d"] == 6

    def test_none_promoted_to_initial(self):
        """Estado 'none' vira 'initial' quando Julia envia."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
        )
        updater = StateUpdate()
        updates = updater.on_outbound_message(state, actor="julia")

        assert updates["permission_state"] == PermissionState.INITIAL.value

    def test_novo_to_prospecting(self):
        """Lifecycle 'novo' vira 'prospecting' quando Julia envia."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.NONE,
            lifecycle_stage=LifecycleStage.NOVO,
        )
        updater = StateUpdate()
        updates = updater.on_outbound_message(state, actor="julia")

        assert updates["lifecycle_stage"] == LifecycleStage.PROSPECTING.value


class TestDecayTemperature:
    """Testes para decay_temperature."""

    def test_decay_after_inactivity(self):
        """Decay aplica após dias de inatividade."""
        now = datetime.utcnow()
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
            last_inbound_at=now - timedelta(days=10),
            last_decay_at=None,
        )
        updater = StateUpdate()
        updates = updater.decay_temperature(state, now)

        # 10 dias * 0.05 = 0.5 de decay
        assert updates["temperature"] == 0.0
        assert updates["temperature_trend"] == TemperatureTrend.COOLING.value
        assert "last_decay_at" in updates

    def test_decay_is_idempotent(self):
        """Decay usa last_decay_at para ser idempotente."""
        now = datetime.utcnow()
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
            last_inbound_at=now - timedelta(days=10),
            last_decay_at=now - timedelta(hours=1),  # Decay recente
        )
        updater = StateUpdate()
        updates = updater.decay_temperature(state, now)

        # Não deve decair porque last_decay_at é recente
        assert updates == {}

    def test_no_decay_for_opted_out(self):
        """Não decai temperatura de opted_out."""
        now = datetime.utcnow()
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.OPTED_OUT,
            temperature=0.5,
            last_inbound_at=now - timedelta(days=10),
        )
        updater = StateUpdate()
        updates = updater.decay_temperature(state, now)

        assert updates == {}

    def test_no_decay_if_already_zero(self):
        """Não decai se temperatura já é zero."""
        now = datetime.utcnow()
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.0,
            last_inbound_at=now - timedelta(days=10),
        )
        updater = StateUpdate()
        updates = updater.decay_temperature(state, now)

        assert updates == {}


class TestOnObjectionResolved:
    """Testes para on_objection_resolved."""

    def test_marks_objection_resolved(self):
        """Marca objeção como resolvida."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        updater = StateUpdate()
        updates = updater.on_objection_resolved(state)

        assert "objection_resolved_at" in updates
        # NÃO limpa active_objection (mantém histórico)
        assert "active_objection" not in updates

    def test_no_update_if_no_objection(self):
        """Não atualiza se não há objeção."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
        )
        updater = StateUpdate()
        updates = updater.on_objection_resolved(state)

        assert updates == {}

    def test_no_update_if_already_resolved(self):
        """Não atualiza se já resolvida."""
        state = DoctorState(
            cliente_id="123",
            permission_state=PermissionState.ACTIVE,
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
            objection_resolved_at=datetime.utcnow(),
        )
        updater = StateUpdate()
        updates = updater.on_objection_resolved(state)

        assert updates == {}
