"""
Testes para replay offline do Policy Engine.

Sprint 16 - Observability
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

from app.services.policy.replay import (
    ReplayResult,
    _state_from_input,
    _compute_hash,
    replay_decision,
    replay_batch,
)
from app.services.policy.types import (
    PermissionState,
    TemperatureBand,
    TemperatureTrend,
    RiskTolerance,
    LifecycleStage,
    PrimaryAction,
)


class TestStateFromInput:
    """Testes para reconstrução do DoctorState."""

    def test_basic_state(self):
        """Reconstrói estado básico."""
        state_input = {
            "cliente_id": "test-123",
            "permission_state": "active",
            "temperature": 0.7,
            "temperature_band": "hot",
            "temperature_trend": "warming",
            "risk_tolerance": "high",
            "lifecycle_stage": "engaged",
        }

        state = _state_from_input(state_input)

        assert state.cliente_id == "test-123"
        assert state.permission_state == PermissionState.ACTIVE
        assert state.temperature == 0.7
        assert state.temperature_band == TemperatureBand.HOT
        assert state.temperature_trend == TemperatureTrend.WARMING
        assert state.risk_tolerance == RiskTolerance.HIGH
        assert state.lifecycle_stage == LifecycleStage.ENGAGED

    def test_fallback_for_invalid_enums(self):
        """Usa fallbacks para valores inválidos."""
        state_input = {
            "cliente_id": "test-123",
            "permission_state": "invalid_state",
            "temperature_band": "unknown_band",
        }

        state = _state_from_input(state_input)

        # Deve usar valores padrão
        assert state.permission_state == PermissionState.NONE
        assert state.temperature_band == TemperatureBand.WARM

    def test_with_dates(self):
        """Reconstrói datas."""
        now = datetime.now(timezone.utc)
        state_input = {
            "cliente_id": "test-123",
            "last_inbound_at": now.isoformat(),
            "cooling_off_until": now.isoformat(),
        }

        state = _state_from_input(state_input)

        assert state.last_inbound_at is not None
        assert state.cooling_off_until is not None


class TestComputeHash:
    """Testes para hash de estado."""

    def test_hash_is_deterministic(self):
        """Mesmo input gera mesmo hash."""
        state_input = {"cliente_id": "test", "temperature": 0.5}

        hash1 = _compute_hash(state_input)
        hash2 = _compute_hash(state_input)

        assert hash1 == hash2

    def test_hash_differs_for_different_input(self):
        """Inputs diferentes geram hashes diferentes."""
        state1 = {"cliente_id": "test", "temperature": 0.5}
        state2 = {"cliente_id": "test", "temperature": 0.6}

        hash1 = _compute_hash(state1)
        hash2 = _compute_hash(state2)

        assert hash1 != hash2

    def test_hash_is_16_chars(self):
        """Hash tem 16 caracteres."""
        state_input = {"cliente_id": "test"}

        hash_val = _compute_hash(state_input)

        assert len(hash_val) == 16


class TestReplayDecision:
    """Testes para replay de decisão."""

    @pytest.mark.asyncio
    @patch("app.services.policy.replay.get_decision_by_id")
    @patch("app.services.policy.replay.PolicyDecide")
    async def test_replay_matching(self, mock_policy_class, mock_get):
        """Replay com resultado igual ao original."""
        # Setup mock da decisão original
        mock_get.return_value = {
            "rule_matched": "rule_default",
            "primary_action": "followup",
            "tone": "direto",
            "requires_human": False,
            "snapshot_hash": "abcd1234abcd1234",
            "doctor_state_input": {
                "cliente_id": "test-123",
                "permission_state": "active",
                "temperature": 0.5,
                "temperature_band": "warm",
                "temperature_trend": "stable",
                "risk_tolerance": "unknown",
                "lifecycle_stage": "novo",
            },
            "is_first_message": False,
            "conversa_status": "active",
        }

        # Setup mock do PolicyDecide
        mock_policy = mock_policy_class.return_value
        mock_decision = AsyncMock()
        mock_decision.rule_id = "rule_default"
        mock_decision.primary_action.value = "followup"
        mock_decision.tone.value = "direto"
        mock_decision.requires_human = False
        mock_policy.decide = AsyncMock(return_value=mock_decision)

        result = await replay_decision("decision-123")

        assert result is not None
        assert result.match is True
        assert result.original_rule == "rule_default"
        assert result.replayed_rule == "rule_default"
        assert len(result.differences) == 0

    @pytest.mark.asyncio
    @patch("app.services.policy.replay.get_decision_by_id")
    @patch("app.services.policy.replay.PolicyDecide")
    async def test_replay_mismatch(self, mock_policy_class, mock_get):
        """Replay com resultado diferente do original."""
        mock_get.return_value = {
            "rule_matched": "rule_default",
            "primary_action": "followup",
            "tone": "direto",
            "requires_human": False,
            "snapshot_hash": "abcd1234abcd1234",
            "doctor_state_input": {
                "cliente_id": "test-123",
                "permission_state": "active",
                "temperature": 0.5,
                "temperature_band": "warm",
                "temperature_trend": "stable",
                "risk_tolerance": "unknown",
                "lifecycle_stage": "novo",
            },
        }

        mock_policy = mock_policy_class.return_value
        mock_decision = AsyncMock()
        mock_decision.rule_id = "rule_new"  # Diferente!
        mock_decision.primary_action.value = "offer"  # Diferente!
        mock_decision.tone.value = "direto"
        mock_decision.requires_human = False
        mock_policy.decide = AsyncMock(return_value=mock_decision)

        result = await replay_decision("decision-123")

        assert result is not None
        assert result.match is False
        assert len(result.differences) > 0

    @pytest.mark.asyncio
    @patch("app.services.policy.replay.get_decision_by_id")
    async def test_replay_not_found(self, mock_get):
        """Replay de decisão não encontrada."""
        mock_get.return_value = None

        result = await replay_decision("decision-not-found")

        assert result is None


class TestReplayBatch:
    """Testes para replay em lote."""

    @pytest.mark.asyncio
    @patch("app.services.policy.replay.replay_decision")
    async def test_batch_stats(self, mock_replay):
        """Calcula estatísticas do lote."""
        # Simular 3 replays: 2 match, 1 mismatch
        mock_replay.side_effect = [
            ReplayResult(
                original_decision_id="1",
                original_rule="rule_a",
                original_action="followup",
                replayed_rule="rule_a",
                replayed_action="followup",
                match=True,
                hash_match=True,
                original_snapshot_hash="hash1",
                computed_snapshot_hash="hash1",
                differences=[],
            ),
            ReplayResult(
                original_decision_id="2",
                original_rule="rule_b",
                original_action="wait",
                replayed_rule="rule_b",
                replayed_action="wait",
                match=True,
                hash_match=True,
                original_snapshot_hash="hash2",
                computed_snapshot_hash="hash2",
                differences=[],
            ),
            ReplayResult(
                original_decision_id="3",
                original_rule="rule_c",
                original_action="followup",
                replayed_rule="rule_d",
                replayed_action="offer",
                match=False,
                hash_match=True,
                original_snapshot_hash="hash3",
                computed_snapshot_hash="hash3",
                differences=["rule: rule_c → rule_d"],
            ),
        ]

        stats = await replay_batch(["1", "2", "3"])

        assert stats["total"] == 3
        assert stats["successful"] == 3
        assert stats["match"] == 2
        assert stats["mismatch"] == 1
        assert len(stats["mismatches"]) == 1

    @pytest.mark.asyncio
    @patch("app.services.policy.replay.replay_decision")
    async def test_batch_with_errors(self, mock_replay):
        """Trata erros no lote."""
        mock_replay.side_effect = [
            ReplayResult(
                original_decision_id="1",
                original_rule="rule_a",
                original_action="followup",
                replayed_rule="rule_a",
                replayed_action="followup",
                match=True,
                hash_match=True,
                original_snapshot_hash="hash1",
                computed_snapshot_hash="hash1",
                differences=[],
            ),
            None,  # Erro
            Exception("DB error"),  # Exceção
        ]

        stats = await replay_batch(["1", "2", "3"])

        assert stats["total"] == 3
        assert stats["successful"] == 1
        assert stats["errors"] == 2
