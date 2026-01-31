"""
Testes para o router de Guardrails.

Sprint 43 - S43.E7.1
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Cliente de teste."""
    return TestClient(app, raise_server_exceptions=False)


class TestFeatureFlags:
    """Testes para endpoints de feature flags."""

    @patch("app.api.routes.guardrails.listar_feature_flags")
    def test_listar_flags_retorna_todas_flags(self, mock_listar, client):
        """GET /guardrails/flags deve retornar lista de flags."""
        mock_listar.return_value = {
            "envio_prospeccao": True,
            "envio_followup": True,
            "envio_campanha": False,
        }

        response = client.get("/guardrails/flags")

        assert response.status_code == 200
        data = response.json()
        assert "flags" in data
        assert data["total"] == 3
        assert data["flags"]["envio_prospeccao"] is True
        assert data["flags"]["envio_campanha"] is False

    @patch("app.api.routes.guardrails.obter_feature_flag")
    def test_obter_flag_especifica(self, mock_obter, client):
        """GET /guardrails/flags/{flag_name} deve retornar flag específica."""
        mock_obter.return_value = True

        response = client.get("/guardrails/flags/envio_prospeccao")

        assert response.status_code == 200
        data = response.json()
        assert data["flag"] == "envio_prospeccao"
        assert data["enabled"] is True

    def test_obter_flag_invalida_retorna_400(self, client):
        """GET /guardrails/flags/{flag_invalida} deve retornar 400."""
        response = client.get("/guardrails/flags/flag_inexistente")

        assert response.status_code == 400
        assert "inválida" in response.json()["detail"].lower()

    @patch("app.api.routes.guardrails.definir_feature_flag")
    def test_atualizar_flag(self, mock_definir, client):
        """POST /guardrails/flags/{flag_name} deve atualizar flag."""
        mock_definir.return_value = True

        response = client.post(
            "/guardrails/flags/envio_prospeccao",
            json={
                "enabled": False,
                "motivo": "Manutenção programada",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["flag"] == "envio_prospeccao"
        assert data["enabled"] is False

    def test_atualizar_flag_sem_motivo_retorna_422(self, client):
        """POST sem motivo deve retornar 422."""
        response = client.post(
            "/guardrails/flags/envio_prospeccao",
            json={"enabled": False},
        )

        assert response.status_code == 422


class TestDesbloqueio:
    """Testes para endpoints de desbloqueio."""

    @patch("app.api.routes.guardrails.desbloquear_chip")
    def test_desbloquear_chip_sucesso(self, mock_desbloquear, client):
        """POST /guardrails/desbloquear/chip/{id} deve desbloquear chip."""
        mock_desbloquear.return_value = True

        response = client.post(
            "/guardrails/desbloquear/chip/chip-123",
            json={
                "motivo": "Chip estava bloqueado por engano",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["entidade"] == "chip"
        assert data["entidade_id"] == "chip-123"

    @patch("app.api.routes.guardrails.desbloquear_chip")
    def test_desbloquear_chip_nao_encontrado(self, mock_desbloquear, client):
        """POST para chip inexistente deve retornar 404."""
        mock_desbloquear.return_value = False

        response = client.post(
            "/guardrails/desbloquear/chip/chip-inexistente",
            json={
                "motivo": "Tentativa de desbloqueio",
                "usuario": "admin",
            },
        )

        assert response.status_code == 404

    @patch("app.api.routes.guardrails.desbloquear_cliente")
    def test_desbloquear_cliente_sucesso(self, mock_desbloquear, client):
        """POST /guardrails/desbloquear/cliente/{id} deve desbloquear cliente."""
        mock_desbloquear.return_value = True

        response = client.post(
            "/guardrails/desbloquear/cliente/cliente-123",
            json={
                "motivo": "Cliente solicitou reativação",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["entidade"] == "cliente"


class TestCircuitBreakers:
    """Testes para endpoints de circuit breakers."""

    @patch("app.api.routes.guardrails.circuit_evolution")
    @patch("app.api.routes.guardrails.circuit_claude")
    @patch("app.api.routes.guardrails.circuit_supabase")
    def test_listar_circuits(self, mock_supabase, mock_claude, mock_evolution, client):
        """GET /guardrails/circuits deve listar todos os circuits."""
        mock_evolution.status.return_value = {
            "state": "CLOSED",
            "failures": 0,
            "threshold": 5,
        }
        mock_claude.status.return_value = {
            "state": "HALF_OPEN",
            "failures": 3,
            "threshold": 5,
        }
        mock_supabase.status.return_value = {
            "state": "OPEN",
            "failures": 5,
            "threshold": 5,
        }

        response = client.get("/guardrails/circuits")

        assert response.status_code == 200
        data = response.json()
        assert len(data["circuits"]) == 3

        # Verificar que temos os 3 circuits
        circuit_names = [c["name"] for c in data["circuits"]]
        assert "evolution" in circuit_names
        assert "claude" in circuit_names
        assert "supabase" in circuit_names

    @patch("app.api.routes.guardrails.resetar_circuit_breaker_global")
    def test_resetar_circuit_sucesso(self, mock_resetar, client):
        """POST /guardrails/circuits/{name}/reset deve resetar circuit."""
        mock_resetar.return_value = True

        response = client.post(
            "/guardrails/circuits/claude/reset",
            json={
                "motivo": "Problema resolvido",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["circuit"] == "claude"

    def test_resetar_circuit_invalido(self, client):
        """POST para circuit inválido deve retornar 400."""
        response = client.post(
            "/guardrails/circuits/invalido/reset",
            json={
                "motivo": "Teste",
                "usuario": "admin",
            },
        )

        assert response.status_code == 400


class TestModoEmergencia:
    """Testes para endpoints de modo emergência."""

    @patch("app.api.routes.guardrails.obter_feature_flag")
    def test_status_emergencia(self, mock_obter, client):
        """GET /guardrails/emergencia/status deve retornar status."""
        # Simular algumas flags desabilitadas (emergência parcial)
        async def mock_flag(flag):
            if flag.value == "envio_prospeccao":
                return False
            return True

        mock_obter.side_effect = mock_flag

        response = client.get("/guardrails/emergencia/status")

        assert response.status_code == 200
        data = response.json()
        assert "ativo" in data
        assert "flags_envio" in data

    @patch("app.api.routes.guardrails.ativar_modo_emergencia")
    def test_ativar_emergencia(self, mock_ativar, client):
        """POST /guardrails/emergencia/ativar deve ativar emergência."""
        mock_ativar.return_value = True

        response = client.post(
            "/guardrails/emergencia/ativar",
            json={
                "motivo": "Incidente crítico",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ativo"] is True

    @patch("app.api.routes.guardrails.desativar_modo_emergencia")
    def test_desativar_emergencia(self, mock_desativar, client):
        """POST /guardrails/emergencia/desativar deve desativar emergência."""
        mock_desativar.return_value = True

        response = client.post(
            "/guardrails/emergencia/desativar",
            json={
                "motivo": "Incidente resolvido",
                "usuario": "admin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ativo"] is False


class TestAuditTrail:
    """Testes para endpoint de audit trail."""

    @patch("app.api.routes.guardrails.buscar_audit_trail")
    def test_buscar_audit_trail(self, mock_buscar, client):
        """GET /guardrails/audit deve retornar registros."""
        mock_buscar.return_value = [
            {
                "id": "audit-1",
                "acao": "feature_flag_change",
                "entidade": "feature_flag",
                "entidade_id": None,
                "detalhes": {"habilitada": False},
                "usuario": "admin",
                "created_at": "2026-01-31T10:00:00Z",
            }
        ]

        response = client.get("/guardrails/audit")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert data["total"] == 1
        assert data["entries"][0]["acao"] == "feature_flag_change"

    @patch("app.api.routes.guardrails.buscar_audit_trail")
    def test_buscar_audit_com_filtros(self, mock_buscar, client):
        """GET /guardrails/audit com filtros deve passar parâmetros."""
        mock_buscar.return_value = []

        response = client.get(
            "/guardrails/audit",
            params={
                "acao": "chip_desbloqueado",
                "usuario": "admin",
                "horas": 48,
            },
        )

        assert response.status_code == 200
        mock_buscar.assert_called_once_with(
            acao="chip_desbloqueado",
            entidade=None,
            entidade_id=None,
            usuario="admin",
            horas=48,
            limite=100,
        )
