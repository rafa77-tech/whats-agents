"""
Testes para policy logger.

Sprint 15 - Policy Engine
"""
import json
import pytest
from datetime import datetime
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
        now = datetime.utcnow()
        state = DoctorState(
            cliente_id="test-123",
            last_inbound_at=now,
            cooling_off_until=now,
        )
        result = _serialize_doctor_state_input(state)

        assert result["last_inbound_at"] == now.isoformat()
        assert result["cooling_off_until"] == now.isoformat()


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

        log_policy_decision(
            state=state,
            decision=decision,
            conversation_id="conv-456",
            message_id="msg-789",
        )

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
        assert log_data["rule_matched"] == "rule_default"
        assert log_data["primary_action"] == "followup"

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
            forbidden_actions=["*"],
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
            message_id="msg-789",
            rule_matched="rule_default",
            effect="message_sent",
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
        assert log_data["effect"] == "message_sent"
        assert log_data["details"]["response_length"] == 42

    @patch("app.services.policy.logger.logger")
    def test_logs_handoff_triggered(self, mock_logger):
        """Loga efeito de handoff."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            message_id=None,
            rule_matched="rule_grave_objection",
            effect="handoff_triggered",
            details={"motivo": "ameaça detectada"},
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["effect"] == "handoff_triggered"
        assert log_data["rule_matched"] == "rule_grave_objection"

    @patch("app.services.policy.logger.logger")
    def test_logs_wait_applied(self, mock_logger):
        """Loga efeito de wait."""
        log_policy_effect(
            cliente_id="test-123",
            conversation_id="conv-456",
            message_id=None,
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
            message_id=None,
            rule_matched="rule_grave_objection",
            effect="error",
            details={"error": "connection timeout", "action": "handoff"},
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert log_data["effect"] == "error"
        assert log_data["details"]["error"] == "connection timeout"


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
            message_id=None,
            rule_matched="test",
            effect="message_sent",
        )

        call_args = mock_logger.info.call_args[0][0]
        json_str = call_args.replace("POLICY_EFFECT: ", "")
        log_data = json.loads(json_str)

        assert "policy_version" in log_data
        assert log_data["policy_version"] == POLICY_VERSION
