"""
Rate limiting service usando Redis.

Sprint 21 - E03 - Rate limit para endpoints sensíveis.

Implementação:
- Sliding window usando Redis sorted sets
- Limites configuráveis por endpoint
- Suporte a múltiplas janelas (minuto, hora)
"""
import logging
import time
from typing import Tuple

from app.services.redis import redis_client

logger = logging.getLogger(__name__)

# Prefixo para chaves de rate limit
RATE_LIMIT_PREFIX = "ratelimit"


async def check_rate_limit(
    key: str,
    limit_per_minute: int = 30,
    limit_per_hour: int = 200,
) -> Tuple[bool, str, int]:
    """
    Verifica se o rate limit foi atingido usando sliding window.

    Args:
        key: Identificador único (ex: IP address)
        limit_per_minute: Limite de requests por minuto
        limit_per_hour: Limite de requests por hora

    Returns:
        Tuple de (allowed: bool, reason: str, retry_after: int)
        - allowed: True se request permitido
        - reason: Motivo do bloqueio se não permitido
        - retry_after: Segundos até poder tentar novamente
    """
    now = time.time()

    # Chaves para janelas de tempo
    minute_key = f"{RATE_LIMIT_PREFIX}:min:{key}"
    hour_key = f"{RATE_LIMIT_PREFIX}:hour:{key}"

    try:
        # Usar pipeline para operações atômicas
        pipe = redis_client.pipeline()

        # Limpar entradas antigas (sliding window)
        one_minute_ago = now - 60
        one_hour_ago = now - 3600

        pipe.zremrangebyscore(minute_key, 0, one_minute_ago)
        pipe.zremrangebyscore(hour_key, 0, one_hour_ago)

        # Contar requests atuais nas janelas
        pipe.zcard(minute_key)
        pipe.zcard(hour_key)

        results = await pipe.execute()

        count_minute = results[2]
        count_hour = results[3]

        # Verificar limite por minuto
        if count_minute >= limit_per_minute:
            retry_after = 60 - int(now - one_minute_ago)
            logger.warning(
                f"Rate limit atingido (minuto): key={key}, count={count_minute}"
            )
            return False, "rate_limit_minute", max(1, retry_after)

        # Verificar limite por hora
        if count_hour >= limit_per_hour:
            retry_after = 3600 - int(now - one_hour_ago)
            logger.warning(
                f"Rate limit atingido (hora): key={key}, count={count_hour}"
            )
            return False, "rate_limit_hour", max(1, retry_after)

        # Adicionar request atual às janelas
        pipe2 = redis_client.pipeline()
        pipe2.zadd(minute_key, {str(now): now})
        pipe2.zadd(hour_key, {str(now): now})
        pipe2.expire(minute_key, 120)  # TTL 2 min (margem)
        pipe2.expire(hour_key, 7200)   # TTL 2 horas (margem)
        await pipe2.execute()

        return True, "", 0

    except Exception as e:
        # Em caso de erro de Redis, permitir (fail-open)
        logger.error(f"Erro no rate limit: {e}")
        return True, "", 0


async def get_rate_limit_status(key: str) -> dict:
    """
    Retorna status atual do rate limit para uma chave.

    Args:
        key: Identificador único

    Returns:
        Dict com contadores atuais
    """
    now = time.time()

    minute_key = f"{RATE_LIMIT_PREFIX}:min:{key}"
    hour_key = f"{RATE_LIMIT_PREFIX}:hour:{key}"

    try:
        pipe = redis_client.pipeline()

        one_minute_ago = now - 60
        one_hour_ago = now - 3600

        pipe.zcount(minute_key, one_minute_ago, now)
        pipe.zcount(hour_key, one_hour_ago, now)

        results = await pipe.execute()

        return {
            "requests_last_minute": results[0],
            "requests_last_hour": results[1],
        }

    except Exception as e:
        logger.error(f"Erro ao obter status de rate limit: {e}")
        return {"requests_last_minute": 0, "requests_last_hour": 0}


def render_rate_limit_page(retry_after: int) -> str:
    """
    Renderiza página HTML amigável para rate limit.

    Args:
        retry_after: Segundos até poder tentar novamente

    Returns:
        HTML string
    """
    minutos = max(1, retry_after // 60)

    html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Aguarde - Revoluna</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                background: #F59E0B;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
            }}
            .icon svg {{
                width: 40px;
                height: 40px;
                fill: white;
            }}
            h1 {{
                color: #1F2937;
                font-size: 24px;
                margin-bottom: 12px;
            }}
            p {{
                color: #6B7280;
                font-size: 16px;
                line-height: 1.5;
            }}
            .retry {{
                margin-top: 16px;
                font-size: 14px;
                color: #9CA3AF;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                    <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
                </svg>
            </div>
            <h1>Um Momento</h1>
            <p>Detectamos muitos acessos do seu endereço. Por favor, aguarde um pouco antes de tentar novamente.</p>
            <p class="retry">Tente novamente em aproximadamente {minutos} minuto{"s" if minutos > 1 else ""}.</p>
        </div>
    </body>
    </html>
    """
    return html
