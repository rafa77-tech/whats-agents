"""
Helpers compartilhados pelos sub-routers de jobs.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import functools
import logging
from typing import Any, Callable, Coroutine

from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def job_endpoint(name: str):
    """
    Decorator DRY para endpoints de job.

    Encapsula o padrao try/except/JSONResponse comum a todos os handlers.

    Args:
        name: Nome do job para logging de erro.

    Uso:
        @router.post("/meu-job")
        @job_endpoint("meu-job")
        async def job_meu_job():
            # ... logica ...
            return {"status": "ok", "message": "feito"}
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, dict | JSONResponse]],
    ) -> Callable[..., Coroutine[Any, Any, JSONResponse]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> JSONResponse:
            try:
                result = await func(*args, **kwargs)
                # Se o handler ja retornou JSONResponse, passar adiante
                if isinstance(result, JSONResponse):
                    return result
                # Caso contrario, encapsular dict em JSONResponse
                return JSONResponse(result)
            except Exception as e:
                logger.error(f"Erro no job {name}: {e}")
                return JSONResponse(
                    {"status": "error", "message": str(e)},
                    status_code=500,
                )

        return wrapper

    return decorator
