"""
Cache de vagas usando Redis.

Sprint 10 - S10.E3.2
"""

import logging
from typing import Optional

from app.services.redis import cache_get_json, cache_set_json, redis_client
from app.core.config import DatabaseConfig

logger = logging.getLogger(__name__)

CACHE_PREFIX = "vagas:"


async def get_cached(especialidade_id: str, limite: int) -> Optional[list[dict]]:
    """Busca vagas do cache."""
    cache_key = f"{CACHE_PREFIX}especialidade:{especialidade_id}:limite:{limite}"
    cached = await cache_get_json(cache_key)
    if cached:
        logger.debug(f"Cache hit para vagas: especialidade {especialidade_id}")
    return cached


async def set_cached(especialidade_id: str, limite: int, vagas: list[dict]) -> None:
    """Salva vagas no cache."""
    cache_key = f"{CACHE_PREFIX}especialidade:{especialidade_id}:limite:{limite}"
    await cache_set_json(cache_key, vagas, DatabaseConfig.CACHE_TTL_VAGAS)


async def invalidar(especialidade_id: Optional[str] = None) -> None:
    """
    Invalida cache de vagas.

    Args:
        especialidade_id: ID da especialidade (opcional, invalida todas se None)
    """
    try:
        if especialidade_id:
            pattern = f"{CACHE_PREFIX}especialidade:{especialidade_id}:*"
        else:
            pattern = f"{CACHE_PREFIX}*"

        keys = await redis_client.keys(pattern)

        if keys:
            await redis_client.delete(*keys)
            logger.debug(f"Cache invalidado: {len(keys)} chave(s) removida(s)")
    except Exception as e:
        logger.warning(f"Erro ao invalidar cache de vagas: {e}")
