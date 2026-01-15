"""
Middlewares da API.

Sprint 31 - S31.E3.2

Middlewares para processamento de requisições HTTP.
"""
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.tracing import (
    generate_trace_id,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
)

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona trace_id a cada request.

    Funcionalidades:
    - Gera trace_id único ou usa do header X-Trace-ID
    - Propaga via context var para todo o código async
    - Adiciona ao request.state para acesso fácil
    - Retorna no header X-Trace-ID da response
    - Loga métricas de cada request

    Uso:
        # Em main.py
        from app.api.middleware import TracingMiddleware
        app.add_middleware(TracingMiddleware)

        # Em qualquer route
        @router.post("/webhook")
        async def webhook(request: Request):
            trace_id = request.state.trace_id
            # ou
            from app.core.tracing import get_trace_id
            trace_id = get_trace_id()
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Processa request com tracing."""
        # Gerar ou usar trace_id do header
        trace_id = request.headers.get("X-Trace-ID") or generate_trace_id()
        set_trace_id(trace_id)

        # Adicionar ao request state para acesso fácil nas routes
        request.state.trace_id = trace_id

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log do request completado
            logger.info(
                f"[{trace_id}] {request.method} {request.url.path} "
                f"→ {response.status_code} ({int(duration * 1000)}ms)"
            )

            # Adicionar trace_id no response header
            response.headers["X-Trace-ID"] = trace_id
            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{trace_id}] {request.method} {request.url.path} "
                f"→ ERROR ({int(duration * 1000)}ms): {e}"
            )
            raise

        finally:
            clear_trace_id()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para logging detalhado de requests.

    Complementa o TracingMiddleware com logs mais detalhados.
    Útil para debug em desenvolvimento.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Processa request com logging detalhado."""
        trace_id = get_trace_id() or "no-trace"

        # Log do request recebido
        logger.debug(
            f"[{trace_id}] Request: {request.method} {request.url.path}",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client": request.client.host if request.client else "unknown",
            }
        )

        response = await call_next(request)

        return response
