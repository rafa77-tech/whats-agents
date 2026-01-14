"""
Testes para exception handlers do FastAPI.

Sprint 30 - S30.E1.2
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.error_handlers import register_exception_handlers
from app.core.exceptions import (
    DatabaseError,
    ExternalAPIError,
    ValidationError,
    RateLimitError,
    NotFoundError,
    HandoffError,
    ConfigurationError,
)


@pytest.fixture
def app_with_handlers():
    """Cria app FastAPI com handlers registrados."""
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(app_with_handlers):
    """Cliente de teste."""
    return TestClient(app_with_handlers, raise_server_exceptions=False)


class TestExceptionHandlers:
    """Testes para cada tipo de exception."""

    def test_not_found_error_returns_404(self, app_with_handlers, client):
        """NotFoundError deve retornar 404."""
        @app_with_handlers.get("/test-not-found")
        async def raise_not_found():
            # NotFoundError aceita (resource, identifier)
            raise NotFoundError("Medico", identifier="123")

        response = client.get("/test-not-found")

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "NotFoundError"
        assert "nao encontrado" in data["message"]
        assert data["details"]["id"] == "123"

    def test_validation_error_returns_400(self, app_with_handlers, client):
        """ValidationError deve retornar 400."""
        @app_with_handlers.get("/test-validation")
        async def raise_validation():
            # ValidationError herda de JuliaException (message, details)
            raise ValidationError("Campo invalido", details={"field": "email"})

        response = client.get("/test-validation")

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "ValidationError"

    def test_rate_limit_error_returns_429(self, app_with_handlers, client):
        """RateLimitError deve retornar 429."""
        @app_with_handlers.get("/test-rate-limit")
        async def raise_rate_limit():
            # RateLimitError aceita (message, telefone, limite_tipo)
            raise RateLimitError("Limite excedido", limite_tipo="hora")

        response = client.get("/test-rate-limit")

        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "RateLimitError"

    def test_external_api_error_returns_502(self, app_with_handlers, client):
        """ExternalAPIError deve retornar 502."""
        @app_with_handlers.get("/test-external")
        async def raise_external():
            # ExternalAPIError aceita (message, service, details)
            raise ExternalAPIError(
                "Evolution API falhou",
                service="evolution",
                details={"status_code": 503}
            )

        response = client.get("/test-external")

        assert response.status_code == 502
        data = response.json()
        assert data["error"] == "ExternalAPIError"

    def test_database_error_returns_503(self, app_with_handlers, client):
        """DatabaseError deve retornar 503."""
        @app_with_handlers.get("/test-database")
        async def raise_database():
            # DatabaseError herda de JuliaException (message, details)
            raise DatabaseError("Conexao perdida", details={"table": "clientes"})

        response = client.get("/test-database")

        assert response.status_code == 503
        data = response.json()
        assert data["error"] == "DatabaseError"

    def test_configuration_error_returns_500(self, app_with_handlers, client):
        """ConfigurationError deve retornar 500."""
        @app_with_handlers.get("/test-config")
        async def raise_config():
            # ConfigurationError herda de JuliaException (message, details)
            raise ConfigurationError("API key faltando")

        response = client.get("/test-config")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "ConfigurationError"

    def test_handoff_error_returns_500(self, app_with_handlers, client):
        """HandoffError deve retornar 500."""
        @app_with_handlers.get("/test-handoff")
        async def raise_handoff():
            # HandoffError herda de JuliaException (message, details)
            raise HandoffError("Falha no handoff")

        response = client.get("/test-handoff")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "HandoffError"

    def test_generic_exception_returns_500(self, app_with_handlers, client):
        """Exception generica deve retornar 500 sem expor detalhes."""
        @app_with_handlers.get("/test-generic")
        async def raise_generic():
            raise ValueError("Erro interno secreto")

        response = client.get("/test-generic")

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "InternalServerError"
        # NAO deve expor a mensagem interna
        assert "secreto" not in data["message"]
        assert data["message"] == "Erro interno do servidor"


class TestErrorResponseFormat:
    """Testes para formato da resposta de erro."""

    def test_error_response_has_required_fields(self, app_with_handlers, client):
        """Resposta de erro deve ter error, message e details."""
        @app_with_handlers.get("/test-format")
        async def raise_error():
            raise NotFoundError("Vaga", identifier="vaga-123")

        response = client.get("/test-format")
        data = response.json()

        assert "error" in data
        assert "message" in data
        assert "details" in data

    def test_details_can_be_empty(self, app_with_handlers, client):
        """Details pode ser dict vazio."""
        @app_with_handlers.get("/test-empty-details")
        async def raise_error():
            raise NotFoundError("Recurso")  # Sem identifier

        response = client.get("/test-empty-details")
        data = response.json()

        # Details deve existir, mesmo que vazio
        assert "details" in data
