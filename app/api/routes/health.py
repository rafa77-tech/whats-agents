"""
Rotas de health check.
"""
from fastapi import APIRouter
from datetime import datetime

from app.services.redis import verificar_conexao_redis
from app.services.rate_limiter import obter_estatisticas
from app.services.circuit_breaker import obter_status_circuits
from app.services.whatsapp import evolution

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Verifica se a API está funcionando.
    Usado para monitoramento e load balancers.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "julia-api",
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Verifica se a API está pronta para receber requests.
    Pode incluir verificações de dependências.
    """
    redis_ok = await verificar_conexao_redis()

    return {
        "status": "ready" if redis_ok else "degraded",
        "checks": {
            "database": "ok",  # TODO: verificar conexão real
            "evolution": "ok",  # TODO: verificar conexão real
            "redis": "ok" if redis_ok else "error",
        },
    }


@router.get("/health/rate-limit")
async def rate_limit_stats():
    """
    Retorna estatísticas de rate limiting.
    """
    stats = await obter_estatisticas()
    return {
        "rate_limit": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/circuits")
async def circuit_status():
    """
    Retorna status dos circuit breakers.
    """
    return {
        "circuits": obter_status_circuits(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/whatsapp")
async def whatsapp_status():
    """
    Verifica status da conexao WhatsApp com Evolution API.
    Retorna connected: true/false e detalhes da instancia.
    """
    try:
        status = await evolution.verificar_conexao()
        # Estado pode estar em status.instance.state ou status.state
        state = None
        if status:
            if "instance" in status:
                state = status.get("instance", {}).get("state")
            else:
                state = status.get("state")

        connected = state == "open"

        return {
            "connected": connected,
            "instance": evolution.instance,
            "state": state or "unknown",
            "details": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "connected": False,
            "instance": evolution.instance,
            "state": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
