"""
Utilidades para tasks assincronas.

Sprint 30 - S30.E4.1

Este modulo fornece wrappers seguros para asyncio.create_task
com error handling, logging e metricas.
"""
import asyncio
import logging
from typing import Coroutine, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)

# Contador de falhas por tipo (para metricas)
_task_failures: dict[str, int] = {}


async def _safe_wrapper(
    coro: Coroutine,
    task_name: str,
    on_error: Optional[Callable[[Exception], None]] = None
) -> Any:
    """
    Wrapper que executa coroutine com error handling.

    Args:
        coro: Coroutine a executar
        task_name: Nome para logging/metricas
        on_error: Callback opcional para erros
    """
    try:
        return await coro
    except asyncio.CancelledError:
        logger.debug(f"Task cancelada: {task_name}")
        raise
    except Exception as e:
        # Incrementar contador de falhas
        _task_failures[task_name] = _task_failures.get(task_name, 0) + 1

        logger.error(
            f"Erro em background task '{task_name}': {e}",
            exc_info=True,
            extra={
                "task_name": task_name,
                "error_type": type(e).__name__,
                "total_failures": _task_failures[task_name]
            }
        )

        if on_error:
            try:
                on_error(e)
            except Exception as callback_error:
                logger.error(f"Erro no callback on_error: {callback_error}")

        # Nao re-raise para nao crashar outras tasks
        return None


def safe_create_task(
    coro: Coroutine,
    name: Optional[str] = None,
    on_error: Optional[Callable[[Exception], None]] = None
) -> asyncio.Task:
    """
    Cria task com error handling automatico.

    Uso:
        # Em vez de:
        asyncio.create_task(minha_funcao())

        # Use:
        safe_create_task(minha_funcao(), name="minha_funcao")

    Args:
        coro: Coroutine a executar
        name: Nome da task (para logging)
        on_error: Callback opcional para quando ocorrer erro

    Returns:
        asyncio.Task com wrapper de error handling

    Example:
        # Basico
        safe_create_task(
            emitir_evento(data),
            name="emitir_evento"
        )

        # Com callback de erro
        def log_falha(e):
            slack_notify(f"Falha em task: {e}")

        safe_create_task(
            processo_critico(data),
            name="processo_critico",
            on_error=log_falha
        )
    """
    task_name = name or (coro.__qualname__ if hasattr(coro, '__qualname__') else "unknown")
    wrapped = _safe_wrapper(coro, task_name, on_error)
    return asyncio.create_task(wrapped, name=task_name)


def fire_and_forget(name: Optional[str] = None):
    """
    Decorator para funcoes que devem rodar em background.

    Uso:
        @fire_and_forget(name="processar_evento")
        async def processar_evento(data):
            # Esta funcao sera executada em background
            # com error handling automatico
            pass

        # Chamada cria task automaticamente
        processar_evento(data)

    Note:
        O retorno da funcao decorada eh a Task, nao o resultado.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            coro = func(*args, **kwargs)
            task_name = name or func.__name__
            return safe_create_task(coro, name=task_name)
        return wrapper
    return decorator


def get_task_failure_counts() -> dict[str, int]:
    """Retorna contagem de falhas por task (para metricas/alertas)."""
    return _task_failures.copy()


def reset_task_failure_counts():
    """Reseta contadores (para testes)."""
    global _task_failures
    _task_failures = {}


async def safe_gather(*coros, return_exceptions: bool = True) -> list:
    """
    Wrapper para asyncio.gather com error handling.

    Diferente de safe_create_task, este aguarda todas as tasks.
    """
    tasks = [
        _safe_wrapper(coro, f"gather_task_{i}", None)
        for i, coro in enumerate(coros)
    ]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


def schedule_with_delay(
    coro: Coroutine,
    delay_seconds: float,
    name: Optional[str] = None
) -> asyncio.Task:
    """
    Agenda task para executar apos delay.

    Uso:
        schedule_with_delay(
            enviar_followup(medico_id),
            delay_seconds=300,  # 5 minutos
            name="followup_agendado"
        )
    """
    async def delayed():
        await asyncio.sleep(delay_seconds)
        return await coro

    task_name = name or f"delayed_{coro.__qualname__ if hasattr(coro, '__qualname__') else 'task'}"
    return safe_create_task(delayed(), name=task_name)
