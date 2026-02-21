"""
Testes para API Routes de Meta Templates.

Sprint 66 — CRUD endpoints com auth guard.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_key():
    return "test_jwt_secret_key_for_tests"


@pytest.fixture
def auth_headers(api_key):
    return {"X-API-Key": api_key}


@pytest.fixture
def mock_settings(api_key):
    with patch("app.api.routes.meta_templates.settings") as mock:
        mock.JWT_SECRET_KEY = api_key
        yield mock


@pytest.fixture
def mock_template_service():
    with patch("app.api.routes.meta_templates.template_service") as mock:
        yield mock


class TestAuth:
    """Testes de autenticação."""

    def test_sem_api_key_retorna_422(self, client):
        """Endpoint sem X-API-Key retorna 422 (missing header)."""
        response = client.get("/meta/templates?waba_id=test")
        assert response.status_code == 422

    def test_api_key_invalida_retorna_401(self, client, mock_settings):
        """Endpoint com X-API-Key errada retorna 401."""
        response = client.get(
            "/meta/templates?waba_id=test",
            headers={"X-API-Key": "wrong_key"},
        )
        assert response.status_code == 401

    def test_api_key_valida_aceita(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        """Endpoint com X-API-Key correta funciona."""
        mock_template_service.listar_templates = AsyncMock(return_value=[])
        response = client.get(
            "/meta/templates?waba_id=test",
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestCriarTemplate:
    """Testes para POST /meta/templates."""

    def test_criar_sucesso(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.criar_template = AsyncMock(
            return_value={"success": True, "meta_status": "PENDING"}
        )

        response = client.post(
            "/meta/templates",
            headers=auth_headers,
            json={
                "waba_id": "waba_123",
                "name": "julia_test_v1",
                "category": "MARKETING",
                "language": "pt_BR",
                "components": [{"type": "BODY", "text": "Oi {{1}}"}],
            },
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_criar_categoria_invalida(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        response = client.post(
            "/meta/templates",
            headers=auth_headers,
            json={
                "waba_id": "waba_123",
                "name": "test",
                "category": "INVALID",
                "components": [],
            },
        )
        assert response.status_code == 400

    def test_criar_sem_access_token_no_body(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        """access_token não deve ser aceito no body (foi removido)."""
        mock_template_service.criar_template = AsyncMock(
            return_value={"success": True}
        )

        response = client.post(
            "/meta/templates",
            headers=auth_headers,
            json={
                "waba_id": "waba_123",
                "name": "test",
                "category": "MARKETING",
                "components": [],
                "access_token": "should_be_ignored",
            },
        )

        # Deve aceitar (Pydantic ignora campos extras por default)
        assert response.status_code == 200
        # Verificar que access_token NÃO foi passado ao service
        call_kwargs = mock_template_service.criar_template.call_args.kwargs
        assert "access_token" not in call_kwargs


class TestListarTemplates:
    """Testes para GET /meta/templates."""

    def test_listar_com_filtros(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.listar_templates = AsyncMock(
            return_value=[
                {"template_name": "t1", "category": "MARKETING"},
                {"template_name": "t2", "category": "UTILITY"},
            ]
        )

        response = client.get(
            "/meta/templates?waba_id=waba_123&category=MARKETING",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["templates"][0]["template_name"] == "t1"


class TestBuscarTemplate:
    """Testes para GET /meta/templates/{name}."""

    def test_buscar_encontrado(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.buscar_template_por_nome = AsyncMock(
            return_value={"template_name": "julia_discovery_v1", "status": "APPROVED"}
        )

        response = client.get(
            "/meta/templates/julia_discovery_v1",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["template_name"] == "julia_discovery_v1"

    def test_buscar_nao_encontrado(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.buscar_template_por_nome = AsyncMock(return_value=None)

        response = client.get(
            "/meta/templates/inexistente",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDeletarTemplate:
    """Testes para DELETE /meta/templates/{name}."""

    def test_deletar_sucesso(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.deletar_template = AsyncMock(
            return_value={"success": True}
        )

        response = client.request(
            "DELETE",
            "/meta/templates/julia_test",
            headers=auth_headers,
            json={"waba_id": "waba_123"},
        )

        assert response.status_code == 200


class TestSincronizarTemplates:
    """Testes para POST /meta/templates/sync."""

    def test_sync_sucesso(
        self, client, mock_settings, auth_headers, mock_template_service
    ):
        mock_template_service.sincronizar_templates = AsyncMock(
            return_value={"success": True, "total": 5, "synced": 5}
        )

        response = client.post(
            "/meta/templates/sync",
            headers=auth_headers,
            json={"waba_id": "waba_123"},
        )

        assert response.status_code == 200
        assert response.json()["synced"] == 5
