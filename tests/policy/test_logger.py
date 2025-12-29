"""
Testes para policy logger.

Sprint 15 - Policy Engine
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.services.policy.types import (
    DoctorState,
    PolicyDecision,
    PermissionState,
    LifecycleStage,
    ObjectionSeverity,
    TemperatureBand,
    TemperatureTrend,
    RiskTolerance,
    PrimaryAction,
    Tone,
)
from app.services.policy.logger import (
    log_policy_decision,
    log_policy_effect,
    _serialize_doctor_state_input,
    _compute_snapshot_hash,
)
from app.services.policy.version import POLICY_VERSION


class TestSerializeDoctorState:
    """Testes para serialização do doctor_state."""

    def test_serializes_minimal_fields(self):
        """Serializa campos essenciais."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.7,
        )
        result = _serialize_doctor_state_input(state)

        assert result["cliente_id"] == "test-123"
        assert result["permission_state"] == "active"
        assert result["temperature"] == 0.7

    def test_serializes_objection(self):
        """Serializa objeção quando presente."""
        state = DoctorState(
            cliente_id="test-123",
            active_objection="preco",
            objection_severity=ObjectionSeverity.MEDIUM,
        )
        result = _serialize_doctor_state_input(state)

        assert result["active_objection"] == "preco"
        assert result["objection_severity"] == "medium"

    def test_serializes_none_objection(self):
        """Serializa None para objeção ausente."""
        state = DoctorState(cliente_id="test-123")
        result = _serialize_doctor_state_input(state)

        assert result["active_objection"] is None
        assert result["objection_severity"] is None

    def test_serializes_dates(self):
        """Serializa datas em ISO format."""
        now = datetime.now(timezone.utc)
        state = DoctorState(
            cliente_id="test-123",
            last_inbound_at=now,
            cooling_off_until=now,
        )
        result = _serialize_doctor_state_input(state)

        assert result["last_inbound_at"] == now.isoformat()
        assert result["cooling_off_until"] == now.isoformat()


class TestSnapshotHash:
    """Testes para snapshot_hash."""

    def test_hash_is_deterministic(self):
        """Mesmo input gera mesmo hash."""
        state_input = {
            "cliente_id": "test-123",
            "permission_state": "active",
            "temperature": 0.5,
        }
        hash1 = _compute_snapshot_hash(state_input)
        hash2 = _compute_snapshot_hash(state_input)
        assert hash1 == hash2

    def test_hash_differs_for_different_input(self):
        """Inputs diferentes geram hashes diferentes."""
        state1 = {"cliente_id": "test-123", "temperature": 0.5}
        state2 = {"cliente_id": "test-123", "temperature": 0.6}
        hash1 = _compute_snapshot_hash(state1)
        hash2 = _compute_snapshot_hash(state2)
        assert hash1 != hash2

    def test_hash_is_16_chars(self):
        """Hash tem 16 caracteres."""
        state_input = {"cliente_id": "test-123"}
        hash_val = _compute_snapshot_hash(state_input)
        assert len(hash_val) == 16


class TestLogPolicyDecision:
    """Testes para log_policy_decision."""

    @patch("app.services.policy.logger.logger")
    def test_logs_info_with_json(self, mock_logger):
        """Loga decisão em formato JSON."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
            temperature=0.5,
        )
        decision = PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["respond"],
            forbidden_actions=[],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text="",
            reasoning="test reasoning",
            rule_id="rule_default",
        )

        decision_id = log_policy_decision(
            state=state,
            decision=decision,
            conversation_id="conv-456",
            interaction_id="int-789",
        )

        # Verifica que retorna decision_id
        assert decision_id is not None
        assert len(decision_id) == 36  # UUID format

        # Verifica que info foi chamado
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]

        assert "POLICY_DECISION:" in call_args
        # Extrai JSON
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert log_data["event"] == "policy_decision"
        assert log_data["policy_version"] == POLICY_VERSION
        assert log_data["cliente_id"] == "test-123"
        assert log_data["conversation_id"] == "conv-456"
        assert log_data["interaction_id"] == "int-789"
        assert log_data["rule_matched"] == "rule_default"
        assert log_data["primary_action"] == "followup"

    @patch("app.services.policy.logger.logger")
    def test_has_event_id_and_decision_id(self, mock_logger):
        """Cada log tem event_id e policy_decision_id únicos."""
        state = DoctorState(cliente_id="test-123")
        decision = PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=[],
            forbidden_actions=[],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text="",
            reasoning="",
            rule_id="test",
        )

        decision_id = log_policy_decision(state=state, decision=decision)

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert "event_id" in log_data
        assert "policy_decision_id" in log_data
        assert log_data["policy_decision_id"] == decision_id
        assert len(log_data["event_id"]) == 36

    @patch("app.services.policy.logger.logger")
    def test_has_snapshot_hash(self, mock_logger):
        """Log inclui snapshot_hash do state."""
        state = DoctorState(cliente_id="test-123", temperature=0.5)
        decision = PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=[],
            forbidden_actions=[],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text="",
            reasoning="",
            rule_id="test",
        )

        log_policy_decision(state=state, decision=decision)

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert "snapshot_hash" in log_data
        assert len(log_data["snapshot_hash"]) == 16

    @patch("app.services.policy.logger.logger")
    def test_forbid_all_separates_from_list(self, mock_logger):
        """forbid_all é separado de forbidden_actions (Sprint 16 Fix)."""
        state = DoctorState(cliente_id="test-123")
        # Sprint 16 Fix: usar forbid_all=True em vez de "*" na lista
        decision = PolicyDecision(
            primary_action=PrimaryAction.HANDOFF,
            allowed_actions=[],
            forbidden_actions=["pressure", "negotiate"],
            forbid_all=True,
            tone=Tone.CRISE,
            requires_human=True,
            constraints_text="",
            reasoning="grave",
            rule_id="rule_grave",
        )

        log_policy_decision(state=state, decision=decision)

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert log_data["forbid_all"] is True
        assert "*" not in log_data["forbidden_actions"]
        assert "pressure" in log_data["forbidden_actions"]
        assert "negotiate" in log_data["forbidden_actions"]

    @patch("app.services.policy.logger.logger")
    def test_forbid_all_false_when_no_wildcard(self, mock_logger):
        """forbid_all é False quando não há *."""
        state = DoctorState(cliente_id="test-123")
        decision = PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=["respond"],
            forbidden_actions=["offer"],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text="",
            reasoning="",
            rule_id="test",
        )

        log_policy_decision(state=state, decision=decision)

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert log_data["forbid_all"] is False
        assert log_data["forbidden_actions"] == ["offer"]

    @patch("app.services.policy.logger.logger")
    def test_logs_warning_for_handoff(self, mock_logger):
        """Loga warning quando requer handoff."""
        state = DoctorState(
            cliente_id="test-123",
            permission_state=PermissionState.ACTIVE,
            active_objection="ameaca",
            objection_severity=ObjectionSeverity.GRAVE,
        )
        decision = PolicyDecision(
            primary_action=PrimaryAction.HANDOFF,
            allowed_actions=[],
            forbidden_actions=[],
            forbid_all=True,
            tone=Tone.CRISE,
            requires_human=True,
            constraints_text="",
            reasoning="grave objection",
            rule_id="rule_grave_objection",
        )

        log_policy_decision(state=state, decision=decision)

        # Verifica que warning foi chamado
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "HANDOFF_REQUIRED" in call_args

    @patch("app.services.policy.logger.logger")
    def test_includes_context_params(self, mock_logger):
        """Inclui parâmetros de contexto no log."""
        state = DoctorState(cliente_id="test-123")
        decision = PolicyDecision(
            primary_action=PrimaryAction.DISCOVERY,
            allowed_actions=["respond"],
            forbidden_actions=["offer"],
            tone=Tone.LEVE,
            requires_human=False,
            constraints_text="",
            reasoning="first contact",
            rule_id="rule_new_doctor_first_contact",
        )

        log_policy_decision(
            state=state,
            decision=decision,
            is_first_message=True,
            conversa_status="active",
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert log_data["is_first_message"] is True
        assert log_data["conversa_status"] == "active"


class TestLogPolicyEffect:
    """Testes para log_policy_effect."""

    @patch("app.services.policy.logger.logger")
    def test_logs_message_sent(self, mock_logger):
        """Loga efeito de mensagem enviada."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            policy_decision_id="dec-001",
            rule_matched="rule_default",
            effect="message_sent",
            interaction_id="int-789",
            details={"response_length": 42},
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]

        assert "POLICY_EFFECT:" in call_args
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["event"] == "policy_effect"
        assert log_data["policy_version"] == POLICY_VERSION
        assert log_data["cliente_id"] == "test-123"
        assert log_data["policy_decision_id"] == "dec-001"
        assert log_data["interaction_id"] == "int-789"
        assert log_data["effect"] == "message_sent"
        assert log_data["details"]["response_length"] == 42

    @patch("app.services.policy.logger.logger")
    def test_logs_handoff_triggered(self, mock_logger):
        """Loga efeito de handoff."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            policy_decision_id="dec-002",
            rule_matched="rule_grave_objection",
            effect="handoff_triggered",
            details={"motivo": "ameaça detectada"},
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["effect"] == "handoff_triggered"
        assert log_data["rule_matched"] == "rule_grave_objection"
        assert log_data["policy_decision_id"] == "dec-002"

    @patch("app.services.policy.logger.logger")
    def test_logs_wait_applied(self, mock_logger):
        """Loga efeito de wait."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            policy_decision_id="dec-003",
            rule_matched="rule_opted_out",
            effect="wait_applied",
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["effect"] == "wait_applied"
        assert log_data["details"] == {}

    @patch("app.services.policy.logger.logger")
    def test_logs_error(self, mock_logger):
        """Loga efeito de erro."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            policy_decision_id="dec-004",
            rule_matched="rule_grave_objection",
            effect="error",
            details={"error": "connection timeout", "action": "handoff"},
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["effect"] == "error"
        assert log_data["details"]["error"] == "connection timeout"

    @patch("app.services.policy.logger.logger")
    def test_has_event_id(self, mock_logger):
        """Cada log_policy_effect tem event_id único."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            policy_decision_id="dec-005",
            rule_matched="test",
            effect="message_sent",
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert "event_id" in log_data
        assert len(log_data["event_id"]) == 36


class TestVersionInLogs:
    """Testes para garantir versão em todos os logs."""

    @patch("app.services.policy.logger.logger")
    def test_decision_has_version(self, mock_logger):
        """log_policy_decision inclui versão."""
        state = DoctorState(cliente_id="test-123")
        decision = PolicyDecision(
            primary_action=PrimaryAction.FOLLOWUP,
            allowed_actions=[],
            forbidden_actions=[],
            tone=Tone.DIRETO,
            requires_human=False,
            constraints_text="",
            reasoning="",
            rule_id="test",
        )

        log_policy_decision(state=state, decision=decision)

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_DECISION: ", "")
        log_data = json.loads(json_str)

        assert "policy_version" in log_data
        assert log_data["policy_version"] == POLICY_VERSION

    @patch("app.services.policy.logger.logger")
    def test_effect_has_version(self, mock_logger):
        """log_policy_effect inclui versão."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id=None,
            policy_decision_id="dec-001",
            rule_matched="test",
            effect="message_sent",
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert "policy_version" in log_data
        assert log_data["policy_version"] == POLICY_VERSION
