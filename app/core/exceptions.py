"""
Exceptions customizadas do Agente Julia.

Sprint 10 - S10.E4.2
"""
from typing import Optional


class JuliaException(Exception):
    """Base exception para todos os erros do sistema."""

    def __init__(
        self,
        message: str,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.details = details or {}
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


class DatabaseError(JuliaException):
    """Erro de banco de dados (Supabase)."""
    pass


class ExternalAPIError(JuliaException):
    """Erro de API externa (WhatsApp, Slack, LLM, etc)."""

    def __init__(
        self,
        message: str,
        service: str,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None
    ):
        self.service = service
        super().__init__(message, details, original_error)


class ValidationError(JuliaException):
    """Erro de validacao de dados de entrada."""
    pass


class RateLimitError(JuliaException):
    """Rate limit atingido."""

    def __init__(
        self,
        message: str = "Rate limit atingido",
        telefone: Optional[str] = None,
        limite_tipo: Optional[str] = None
    ):
        details = {}
        if telefone:
            details["telefone"] = telefone[:8] + "..."
        if limite_tipo:
            details["limite_tipo"] = limite_tipo
        super().__init__(message, details)


class NotFoundError(JuliaException):
    """Recurso nao encontrado."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None
    ):
        message = f"{resource} nao encontrado"
        details = {}
        if identifier:
            details["id"] = identifier
        super().__init__(message, details)


class HandoffError(JuliaException):
    """Erro durante processo de handoff."""
    pass


class ConfigurationError(JuliaException):
    """Erro de configuracao do sistema."""
    pass
