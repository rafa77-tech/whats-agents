"""
Decorators utilitarios do Agente Julia.

Sprint 10 - S10.E4.2
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, ParamSpec

from app.core.exceptions import JuliaException, DatabaseError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def handle_errors(
    default_return: Optional[Any] = None, log_level: str = "error", reraise: bool = False
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator para tratamento padronizado de erros.

    Args:
        default_return: Valor retornado em caso de erro (se reraise=False)
        log_level: Nivel de log para erros ('error', 'warning', 'info')
        reraise: Se True, re-levanta a exception apos logar

    Usage:
        @handle_errors(default_return=[])
        async def listar_vagas():
            ...

        @handle_errors(reraise=True)
        async def operacao_critica():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except JuliaException:
                # Re-raise exceptions conhecidas
                raise
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"Erro em {func.__name__}: {e}",
                    exc_info=True,
                    extra={"function": func.__name__, "error": str(e)},
                )

                if reraise:
                    raise DatabaseError(
                        f"Erro inesperado em {func.__name__}",
                        details={"error": str(e)},
                        original_error=e,
                    )

                return default_return

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except JuliaException:
                raise
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"Erro em {func.__name__}: {e}",
                    exc_info=True,
                    extra={"function": func.__name__, "error": str(e)},
                )

                if reraise:
                    raise DatabaseError(
                        f"Erro inesperado em {func.__name__}",
                        details={"error": str(e)},
                        original_error=e,
                    )

                return default_return

        # Detecta se e async
        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_execution(
    level: str = "info", include_args: bool = False
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator para logar execucao de funcoes.

    Args:
        level: Nivel de log ('debug', 'info', 'warning')
        include_args: Se deve incluir argumentos no log

    Usage:
        @log_execution()
        async def processar_mensagem(telefone, mensagem):
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log_func = getattr(logger, level, logger.info)

            log_msg = f"Executando {func.__name__}"
            if include_args:
                log_msg += f" args={args}, kwargs={kwargs}"
            log_func(log_msg)

            result = await func(*args, **kwargs)

            log_func(f"Concluido {func.__name__}")
            return result

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log_func = getattr(logger, level, logger.info)

            log_msg = f"Executando {func.__name__}"
            if include_args:
                log_msg += f" args={args}, kwargs={kwargs}"
            log_func(log_msg)

            result = func(*args, **kwargs)

            log_func(f"Concluido {func.__name__}")
            return result

        if functools.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
