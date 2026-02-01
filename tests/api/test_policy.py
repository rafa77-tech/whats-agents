"""
Testes para o router de Policy Engine.

Sprint 43 - S43.E7.2
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.policy.flags import DisabledRulesFlags


@pytest.fixture
def client():
    """Cliente de teste."""
    return TestClient(app, raise_server_exceptions=False)


class TestPolicyStatus:
    """Testes para endpoints de status."""

    @patch("app.api.routes.policy.is_policy_engine_enabled")
    @patch("app.api.routes.policy.is_safe_mode_active")
    @patch("app.api.routes.policy.get_safe_mode_action")
    @patch("app.api.routes.policy.are_campaigns_enabled")
    @patch("app.api.routes.policy.get_disabled_rules")
    def test_get_status(
        self, mock_disabled, mock_campaigns, mock_action, mock_safe, mock_enabled, client
    ):
        """GET /policy/status deve retornar status completo."""
        mock_enabled.return_value = True
        mock_safe.return_value = False
        mock_action.return_value = "wait"
        mock_campaigns.return_value = True
        mock_disabled.return_value = DisabledRulesFlags(rules=["rule_cold_temperature"])

        response = client.get("/policy/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["safe_mode"] is False
        assert data["safe_mode_action"] == "wait"
        assert data["campaigns_enabled"] is True
        assert "rule_cold_temperature" in data["disabled_rules"]

    @patch("app.api.routes.policy.enable_policy_engine")
    def test_enable_policy(self, mock_enable, client):
        """POST /policy/enable deve habilitar engine."""
        mock_enable.return_value = True

        response = client.post(
            "/policy/enable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is True

    @patch("app.api.routes.policy.disable_policy_engine")
    def test_disable_policy(self, mock_disable, client):
        """POST /policy/disable deve desabilitar engine."""
        mock_disable.return_value = True

        response = client.post(
            "/policy/disable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is False


class TestSafeMode:
    """Testes para endpoints de safe mode."""

    @patch("app.api.routes.policy.is_safe_mode_active")
    @patch("app.api.routes.policy.get_safe_mode_action")
    def test_get_safe_mode_status(self, mock_action, mock_active, client):
        """GET /policy/safe-mode deve retornar status."""
        mock_active.return_value = True
        mock_action.return_value = "handoff"

        response = client.get("/policy/safe-mode")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["mode"] == "handoff"

    @patch("app.api.routes.policy.enable_safe_mode")
    def test_enable_safe_mode_wait(self, mock_enable, client):
        """POST /policy/safe-mode/enable com mode=wait."""
        mock_enable.return_value = True

        response = client.post(
            "/policy/safe-mode/enable",
            json={"mode": "wait", "usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is True
        assert data["mode"] == "wait"

    @patch("app.api.routes.policy.enable_safe_mode")
    def test_enable_safe_mode_handoff(self, mock_enable, client):
        """POST /policy/safe-mode/enable com mode=handoff."""
        mock_enable.return_value = True

        response = client.post(
            "/policy/safe-mode/enable",
            json={"mode": "handoff", "usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "handoff"

    def test_enable_safe_mode_invalid_mode(self, client):
        """POST com mode inválido deve retornar 422."""
        response = client.post(
            "/policy/safe-mode/enable",
            json={"mode": "invalid", "usuario": "admin"},
        )

        assert response.status_code == 422

    @patch("app.api.routes.policy.disable_safe_mode")
    def test_disable_safe_mode(self, mock_disable, client):
        """POST /policy/safe-mode/disable deve desativar."""
        mock_disable.return_value = True

        response = client.post(
            "/policy/safe-mode/disable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is False


class TestRules:
    """Testes para endpoints de regras."""

    @patch("app.api.routes.policy.get_disabled_rules")
    def test_list_rules(self, mock_disabled, client):
        """GET /policy/rules deve listar regras."""
        mock_disabled.return_value = DisabledRulesFlags(rules=[])

        response = client.get("/policy/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert data["total"] > 0
        assert data["disabled_count"] == 0

        # Verificar estrutura de regra
        rule = data["rules"][0]
        assert "id" in rule
        assert "name" in rule
        assert "enabled" in rule

    @patch("app.api.routes.policy.get_disabled_rules")
    def test_list_rules_with_disabled(self, mock_disabled, client):
        """GET /policy/rules deve mostrar regras desabilitadas."""
        mock_disabled.return_value = DisabledRulesFlags(
            rules=["rule_cold_temperature", "rule_high_objection"]
        )

        response = client.get("/policy/rules")

        assert response.status_code == 200
        data = response.json()
        assert data["disabled_count"] == 2

    @patch("app.api.routes.policy.enable_rule")
    def test_enable_rule(self, mock_enable, client):
        """POST /policy/rules/{id}/enable deve habilitar regra."""
        mock_enable.return_value = True

        response = client.post(
            "/policy/rules/rule_cold_temperature/enable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rule_id"] == "rule_cold_temperature"
        assert data["enabled"] is True

    @patch("app.api.routes.policy.disable_rule")
    def test_disable_rule(self, mock_disable, client):
        """POST /policy/rules/{id}/disable deve desabilitar regra."""
        mock_disable.return_value = True

        response = client.post(
            "/policy/rules/rule_cold_temperature/disable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["enabled"] is False

    def test_disable_rule_default_forbidden(self, client):
        """POST /policy/rules/rule_default/disable deve retornar 400."""
        response = client.post(
            "/policy/rules/rule_default/disable",
            json={"usuario": "admin"},
        )

        assert response.status_code == 400
        assert "default" in response.json()["detail"].lower()


class TestMetrics:
    """Testes para endpoints de métricas."""

    @patch("app.api.routes.policy.get_policy_summary")
    def test_get_metrics_summary(self, mock_summary, client):
        """GET /policy/metrics deve retornar resumo."""
        mock_summary.return_value = {
            "period_hours": 24,
            "total_decisions": 1234,
            "total_handoffs": 45,
            "handoff_rate": 3.65,
            "decisions_by_rule": [{"rule_matched": "rule_default", "count": 1000}],
            "decisions_by_action": [{"primary_action": "followup", "count": 800}],
            "effects_by_type": [{"effect_type": "message_sent", "count": 750}],
        }

        response = client.get("/policy/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["total_decisions"] == 1234
        assert data["total_handoffs"] == 45
        assert data["handoff_rate"] == 3.65

    @patch("app.api.routes.policy.get_decisions_count")
    def test_get_decisions_count(self, mock_count, client):
        """GET /policy/metrics/decisions deve retornar contagem."""
        mock_count.return_value = 500

        response = client.get("/policy/metrics/decisions", params={"horas": 48})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 500
        assert data["period_hours"] == 48

    @patch("app.api.routes.policy.get_decisions_by_rule")
    def test_get_decisions_by_rule(self, mock_by_rule, client):
        """GET /policy/metrics/rules deve retornar por regra."""
        mock_by_rule.return_value = [
            {"rule_matched": "rule_default", "count": 100},
            {"rule_matched": "rule_grave_objection", "count": 10},
        ]

        response = client.get("/policy/metrics/rules")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    @patch("app.api.routes.policy.get_decisions_by_action")
    def test_get_decisions_by_action(self, mock_by_action, client):
        """GET /policy/metrics/actions deve retornar por ação."""
        mock_by_action.return_value = [
            {"primary_action": "followup", "count": 80},
            {"primary_action": "handoff", "count": 20},
        ]

        response = client.get("/policy/metrics/actions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    @patch("app.api.routes.policy.get_decisions_per_hour")
    def test_get_decisions_per_hour(self, mock_hourly, client):
        """GET /policy/metrics/hourly deve retornar por hora."""
        mock_hourly.return_value = [
            {"hour": "2026-01-31T10", "count": 50},
            {"hour": "2026-01-31T11", "count": 45},
        ]

        response = client.get("/policy/metrics/hourly")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2

    @patch("app.api.routes.policy.get_orphan_decisions")
    def test_get_orphan_decisions(self, mock_orphans, client):
        """GET /policy/metrics/orphans deve retornar órfãos."""
        mock_orphans.return_value = [
            {
                "policy_decision_id": "dec-1",
                "cliente_id": "cli-1",
                "rule_matched": "rule_default",
                "ts": "2026-01-31T10:00:00Z",
            }
        ]

        response = client.get("/policy/metrics/orphans")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["orphans"]) == 1


class TestDecisions:
    """Testes para endpoints de decisões (debug)."""

    @patch("app.services.supabase.supabase")
    def test_get_decisions_by_cliente(self, mock_supabase, client):
        """GET /policy/decisions/cliente/{id} deve retornar decisões."""
        mock_response = MagicMock()
        mock_response.data = [
            {
                "policy_decision_id": "dec-1",
                "cliente_id": "cliente-123",
                "rule_matched": "rule_default",
                "primary_action": "followup",
                "ts": "2026-01-31T10:00:00Z",
            }
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = (
            mock_response
        )

        response = client.get("/policy/decisions/cliente/cliente-123")

        assert response.status_code == 200
        data = response.json()
        assert data["cliente_id"] == "cliente-123"
        assert data["count"] == 1
