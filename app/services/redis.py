"""
Cliente Redis para rate limiting e cache.
"""
import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Track if we've already logged Redis connection failure (avoid log spam in dev)
_redis_connection_logged = False

# Cliente Redis global
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True
)


async def verificar_conexao_redis() -> bool:
    """Verifica se Redis está acessível."""
    global _redis_connection_logged
    try:
        await redis_client.ping()
        logger.debug("Redis conectado")
        _redis_connection_logged = False  # Reset on successful connection
        return True
    except Exception as e:
        # Only log once in dev to avoid spam
        if not _redis_connection_logged:
            if settings.ENVIRONMENT == "development":
                logger.debug(f"Redis não disponível em dev: {e}")
            else:
                logger.error(f"Redis não acessível: {e}")
            _redis_connection_logged = True
        return False


# Funções de cache genérico
async def cache_get(key: str) -> Optional[str]:
    """Obtém valor do cache."""
    try:
        return await redis_client.get(key)
    except Exception as e:
        logger.error(f"Erro ao buscar cache {key}: {e}")
        return None


async def cache_set(key: str, value: str, ttl: int = 300) -> bool:
    """Define valor no cache com TTL em segundos."""
    try:
        await redis_client.setex(key, ttl, value)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar cache {key}: {e}")
        return False


async def cache_get_json(key: str) -> Optional[Dict[str, Any]]:
    """Obtém JSON do cache."""
    data = await cache_get(key)
    if data:
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None
    return None


async def cache_set_json(key: str, value: Dict[str, Any], ttl: int = 300) -> bool:
    """Define JSON no cache."""
    try:
        json_str = json.dumps(value, ensure_ascii=False)
        return await cache_set(key, json_str, ttl)
    except Exception as e:
        logger.error(f"Erro ao salvar JSON no cache {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Remove valor do cache."""
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar cache {key}: {e}")
        return False
