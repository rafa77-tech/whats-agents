"""
Testes para métricas do Policy Engine.

Sprint 16 - Observability
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from app.services.policy.metrics import (
    get_decisions_count,
    get_decisions_by_rule,
    get_decisions_by_action,
    get_effects_by_type,
    get_handoff_count,
    get_decisions_per_hour,
    get_policy_summary,
)


class TestDecisionsCount:
    """Testes para contagem de decisões."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_count_decisions(self, mock_supabase):
        """Conta decisões nas últimas 24h."""
        mock_response = MagicMock()
        mock_response.count = 42
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_decisions_count(hours=24)

        assert result == 42
        mock_supabase.table.assert_called_with("policy_events")

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_count_decisions_with_cliente(self, mock_supabase):
        """Conta decisões filtradas por cliente."""
        mock_response = MagicMock()
        mock_response.count = 10
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.eq.return_value.execute.return_value = mock_response

        result = await get_decisions_count(hours=24, cliente_id="test-123")

        assert result == 10

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_count_decisions_error(self, mock_supabase):
        """Retorna 0 em caso de erro."""
        mock_supabase.table.side_effect = Exception("DB error")

        result = await get_decisions_count(hours=24)

        assert result == 0


class TestDecisionsByRule:
    """Testes para agrupamento por regra."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_group_by_rule(self, mock_supabase):
        """Agrupa decisões por regra."""
        mock_response = MagicMock()
        mock_response.data = [
            {"rule_matched": "rule_default"},
            {"rule_matched": "rule_default"},
            {"rule_matched": "rule_grave_objection"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_decisions_by_rule(hours=24)

        assert len(result) == 2
        # Ordenado por count desc
        assert result[0]["rule_matched"] == "rule_default"
        assert result[0]["count"] == 2
        assert result[1]["rule_matched"] == "rule_grave_objection"
        assert result[1]["count"] == 1

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_group_by_rule_empty(self, mock_supabase):
        """Retorna lista vazia se não há dados."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_decisions_by_rule(hours=24)

        assert result == []


class TestDecisionsByAction:
    """Testes para agrupamento por ação."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_group_by_action(self, mock_supabase):
        """Agrupa decisões por ação."""
        mock_response = MagicMock()
        mock_response.data = [
            {"primary_action": "followup"},
            {"primary_action": "followup"},
            {"primary_action": "wait"},
            {"primary_action": "handoff"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_decisions_by_action(hours=24)

        assert len(result) == 3
        assert result[0]["primary_action"] == "followup"
        assert result[0]["count"] == 2


class TestEffectsByType:
    """Testes para agrupamento de efeitos."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_group_effects(self, mock_supabase):
        """Agrupa efeitos por tipo."""
        mock_response = MagicMock()
        mock_response.data = [
            {"effect_type": "message_sent"},
            {"effect_type": "message_sent"},
            {"effect_type": "message_sent"},
            {"effect_type": "wait_applied"},
            {"effect_type": "handoff_triggered"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_effects_by_type(hours=24)

        assert len(result) == 3
        assert result[0]["effect_type"] == "message_sent"
        assert result[0]["count"] == 3


class TestHandoffCount:
    """Testes para contagem de handoffs."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_count_handoffs(self, mock_supabase):
        """Conta handoffs nas últimas 24h."""
        mock_response = MagicMock()
        mock_response.count = 5
        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_handoff_count(hours=24)

        assert result == 5


class TestDecisionsPerHour:
    """Testes para decisões por hora."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.supabase")
    async def test_group_by_hour(self, mock_supabase):
        """Agrupa decisões por hora."""
        mock_response = MagicMock()
        mock_response.data = [
            {"ts": "2024-01-15T10:30:00+00:00"},
            {"ts": "2024-01-15T10:45:00+00:00"},
            {"ts": "2024-01-15T11:00:00+00:00"},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_response

        result = await get_decisions_per_hour(hours=24)

        assert len(result) == 2
        # Ordenado cronologicamente
        assert result[0]["hour"] == "2024-01-15T10"
        assert result[0]["count"] == 2
        assert result[1]["hour"] == "2024-01-15T11"
        assert result[1]["count"] == 1


class TestPolicySummary:
    """Testes para resumo geral."""

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.get_effects_by_type")
    @patch("app.services.policy.metrics.get_decisions_by_action")
    @patch("app.services.policy.metrics.get_decisions_by_rule")
    @patch("app.services.policy.metrics.get_handoff_count")
    @patch("app.services.policy.metrics.get_decisions_count")
    async def test_summary(
        self, mock_count, mock_handoff, mock_rule, mock_action, mock_effect
    ):
        """Gera resumo completo."""
        mock_count.return_value = 100
        mock_handoff.return_value = 5
        mock_rule.return_value = [{"rule_matched": "default", "count": 100}]
        mock_action.return_value = [{"primary_action": "followup", "count": 95}]
        mock_effect.return_value = [{"effect_type": "message_sent", "count": 90}]

        result = await get_policy_summary(hours=24)

        assert result["total_decisions"] == 100
        assert result["total_handoffs"] == 5
        assert result["handoff_rate"] == 5.0
        assert result["period_hours"] == 24

    @pytest.mark.asyncio
    @patch("app.services.policy.metrics.get_effects_by_type")
    @patch("app.services.policy.metrics.get_decisions_by_action")
    @patch("app.services.policy.metrics.get_decisions_by_rule")
    @patch("app.services.policy.metrics.get_handoff_count")
    @patch("app.services.policy.metrics.get_decisions_count")
    async def test_summary_zero_decisions(
        self, mock_count, mock_handoff, mock_rule, mock_action, mock_effect
    ):
        """Handoff rate é 0 quando não há decisões."""
        mock_count.return_value = 0
        mock_handoff.return_value = 0
        mock_rule.return_value = []
        mock_action.return_value = []
        mock_effect.return_value = []

        result = await get_policy_summary(hours=24)

        assert result["handoff_rate"] == 0
