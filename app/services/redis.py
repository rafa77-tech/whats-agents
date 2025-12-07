"""
Cliente Redis para rate limiting e cache.
"""
import redis.asyncio as redis
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Cliente Redis global
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)


async def verificar_conexao_redis() -> bool:
    """Verifica se Redis está acessível."""
    try:
        await redis_client.ping()
        logger.debug("Redis conectado")
        return True
    except Exception as e:
        logger.error(f"Redis não acessível: {e}")
        return False
