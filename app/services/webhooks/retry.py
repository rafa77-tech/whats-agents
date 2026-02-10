"""
Retry com backoff exponencial para webhooks.

Sprint 26 - E06
"""

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs,
) -> Any:
    """
    Executa funcao com retry e backoff exponencial.

    Args:
        func: Funcao async a executar
        max_retries: Numero maximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay maximo em segundos
        *args, **kwargs: Argumentos para a funcao

    Returns:
        Resultado da funcao

    Raises:
        Exception: Se todas as tentativas falharem
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                # Calcular delay exponencial: 1s, 2s, 4s, 8s, ...
                delay = min(base_delay * (2**attempt), max_delay)

                logger.warning(
                    f"[Retry] Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                    f"Aguardando {delay}s..."
                )

                await asyncio.sleep(delay)
            else:
                logger.error(f"[Retry] Todas as {max_retries} tentativas falharam: {e}")

    raise last_exception


async def retry_sync_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs,
) -> Any:
    """
    Executa funcao sincrona com retry e backoff exponencial.

    Args:
        func: Funcao sincrona a executar
        max_retries: Numero maximo de tentativas
        base_delay: Delay inicial em segundos
        max_delay: Delay maximo em segundos
        *args, **kwargs: Argumentos para a funcao

    Returns:
        Resultado da funcao

    Raises:
        Exception: Se todas as tentativas falharem
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            if attempt < max_retries - 1:
                delay = min(base_delay * (2**attempt), max_delay)

                logger.warning(
                    f"[Retry] Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                    f"Aguardando {delay}s..."
                )

                await asyncio.sleep(delay)
            else:
                logger.error(f"[Retry] Todas as {max_retries} tentativas falharam: {e}")

    raise last_exception
