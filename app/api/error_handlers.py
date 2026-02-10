"""
Exception handlers para FastAPI.

Sprint 10 - S10.E4.2
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    JuliaException,
    DatabaseError,
    ExternalAPIError,
    ValidationError,
    RateLimitError,
    NotFoundError,
    HandoffError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


async def julia_exception_handler(request: Request, exc: JuliaException) -> JSONResponse:
    """Handler para todas as exceptions customizadas."""
    status_code = 500
    error_type = exc.__class__.__name__

    # Mapear tipo de exception para status code HTTP
    if isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, RateLimitError):
        status_code = 429
    elif isinstance(exc, ExternalAPIError):
        status_code = 502
    elif isinstance(exc, DatabaseError):
        status_code = 503
    elif isinstance(exc, ConfigurationError):
        status_code = 500
    elif isinstance(exc, HandoffError):
        status_code = 500

    # Log do erro
    logger.error(
        f"{error_type}: {exc.message}",
        extra={"error_type": error_type, "details": exc.details, "path": request.url.path},
    )

    return JSONResponse(
        status_code=status_code,
        content={"error": error_type, "message": exc.message, "details": exc.details},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para exceptions nao tratadas."""
    logger.exception(f"Erro nao tratado: {exc}", extra={"path": request.url.path})

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "Erro interno do servidor",
            "details": {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registra todos os exception handlers no app FastAPI.

    Usage:
        from app.api.error_handlers import register_exception_handlers

        app = FastAPI()
        register_exception_handlers(app)
    """
    # Handler para exceptions customizadas
    app.add_exception_handler(JuliaException, julia_exception_handler)

    # Handlers especificos (opcional - o handler base ja cobre)
    app.add_exception_handler(DatabaseError, julia_exception_handler)
    app.add_exception_handler(ExternalAPIError, julia_exception_handler)
    app.add_exception_handler(ValidationError, julia_exception_handler)
    app.add_exception_handler(RateLimitError, julia_exception_handler)
    app.add_exception_handler(NotFoundError, julia_exception_handler)
    app.add_exception_handler(HandoffError, julia_exception_handler)
    app.add_exception_handler(ConfigurationError, julia_exception_handler)

    # Handler generico para exceptions nao tratadas
    app.add_exception_handler(Exception, generic_exception_handler)
