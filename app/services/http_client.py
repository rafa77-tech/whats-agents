"""
Sprint 44 T06.2: HTTP Client Singleton com connection pooling.

Centraliza todas as chamadas HTTP externas para:
- Reutilização de conexões (evita overhead de TCP handshake)
- Connection pooling configurável
- HTTP/2 multiplexing
- Timeout padronizado
- Fechamento gracioso no shutdown
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cliente HTTP global (singleton)
_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """
    Obtém o cliente HTTP singleton.

    Cria o cliente na primeira chamada com configurações otimizadas.

    Returns:
        httpx.AsyncClient configurado com pooling
    """
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            # Timeouts
            timeout=httpx.Timeout(
                connect=10.0,  # Timeout para estabelecer conexão
                read=30.0,  # Timeout para leitura
                write=30.0,  # Timeout para escrita
                pool=5.0,  # Timeout para obter conexão do pool
            ),
            # Connection pooling
            limits=httpx.Limits(
                max_connections=100,  # Máximo de conexões totais
                max_keepalive_connections=20,  # Conexões mantidas abertas
                keepalive_expiry=30.0,  # Tempo para manter conexão ociosa
            ),
            # HTTP/2 para multiplexing
            http2=True,
            # Headers padrão
            headers={
                "User-Agent": "Julia-Agent/1.0",
            },
            # Seguir redirects
            follow_redirects=True,
        )
        logger.info("HTTP client singleton criado com pooling configurado")

    return _client


async def close_http_client() -> None:
    """
    Fecha o cliente HTTP.

    Deve ser chamado no shutdown da aplicação para liberar recursos.
    """
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("HTTP client singleton fechado")


# Funções de conveniência para requests comuns
async def http_get(url: str, **kwargs) -> httpx.Response:
    """GET request usando o cliente singleton."""
    client = await get_http_client()
    return await client.get(url, **kwargs)


async def http_post(url: str, **kwargs) -> httpx.Response:
    """POST request usando o cliente singleton."""
    client = await get_http_client()
    return await client.post(url, **kwargs)


async def http_put(url: str, **kwargs) -> httpx.Response:
    """PUT request usando o cliente singleton."""
    client = await get_http_client()
    return await client.put(url, **kwargs)


async def http_delete(url: str, **kwargs) -> httpx.Response:
    """DELETE request usando o cliente singleton."""
    client = await get_http_client()
    return await client.delete(url, **kwargs)
