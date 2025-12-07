"""
Rotas de health check.
"""
from fastapi import APIRouter
from datetime import datetime

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
    # TODO: Adicionar verificações de Supabase, Evolution, etc.
    return {
        "status": "ready",
        "checks": {
            "database": "ok",  # TODO: verificar conexão real
            "evolution": "ok",  # TODO: verificar conexão real
        },
    }
