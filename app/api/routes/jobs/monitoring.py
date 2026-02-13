"""
Monitoramento de fila de mensagens e worker health.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Monitoramento de Fila (Sprint 36)
# =============================================================================


@router.post("/monitorar-fila")
@job_endpoint("monitorar-fila")
async def job_monitorar_fila(
    limite_pendentes: int = 50,
    limite_idade_minutos: int = 30,
):
    """
    Sprint 36 - T01.5: Monitora saude da fila de mensagens.

    Verifica:
    - Quantidade de mensagens pendentes
    - Idade da mensagem mais antiga
    - Erros nas ultimas 24h

    Alerta via log se:
    - Mais de `limite_pendentes` mensagens pendentes
    - Mensagem mais antiga ha mais de `limite_idade_minutos` minutos

    Args:
        limite_pendentes: Maximo de mensagens pendentes (default: 50)
        limite_idade_minutos: Minutos max da mensagem mais antiga (default: 30)

    Schedule: */10 * * * * (a cada 10 minutos)
    """
    from app.services.fila import fila_service

    metricas = await fila_service.obter_metricas_fila()

    pendentes = metricas["pendentes"]
    idade = metricas["mensagem_mais_antiga_min"]
    erros_24h = metricas["erros_ultimas_24h"]

    alertas = []

    # Verificar fila acumulando
    if pendentes > limite_pendentes:
        alertas.append(f"Fila com {pendentes} pendentes (limite: {limite_pendentes})")

    # Verificar mensagens travadas
    if idade and idade > limite_idade_minutos:
        alertas.append(
            f"Mensagem mais antiga há {idade:.0f} min (limite: {limite_idade_minutos})"
        )

    # Verificar muitos erros
    if erros_24h > 20:
        alertas.append(f"{erros_24h} erros nas últimas 24h")

    # Sprint 47: Removida notificacao Slack - apenas log
    if alertas:
        logger.warning(
            "[MonitorFila] Alertas detectados",
            extra={
                "alertas": alertas,
                "pendentes": pendentes,
                "idade_min": idade,
                "erros_24h": erros_24h,
            },
        )

    status = "warning" if alertas else "ok"

    return JSONResponse(
        {
            "status": status,
            "pendentes": pendentes,
            "processando": metricas["processando"],
            "mensagem_mais_antiga_min": idade,
            "erros_24h": erros_24h,
            "alertas": alertas,
        }
    )


# =============================================================================
# Fila Worker Health (Sprint 36)
# =============================================================================


@router.get("/fila-worker-health")
@job_endpoint("fila-worker-health")
async def job_fila_worker_health():
    """
    Sprint 36 - T01.6: Health check do fila_worker.

    Verifica:
    - Status do circuit breaker
    - Se ha mensagens sendo processadas (nao travadas)
    - Metricas gerais da fila

    Retorna status:
    - healthy: Tudo funcionando
    - warning: Problemas detectados mas operacional
    - critical: Worker possivelmente parado/travado

    Util para monitoramento externo e dashboards.
    """
    from app.services.fila import fila_service
    from app.services.circuit_breaker import circuit_evolution

    metricas = await fila_service.obter_metricas_fila()

    pendentes = metricas["pendentes"]
    processando = metricas["processando"]
    idade = metricas["mensagem_mais_antiga_min"]
    erros_24h = metricas["erros_ultimas_24h"]

    # Status do circuit breaker
    circuit_status = circuit_evolution.status()
    circuit_estado = circuit_status["estado"]

    # Determinar status geral
    issues = []

    # Circuit breaker aberto e critico
    if circuit_estado == "open":
        issues.append("circuit_breaker_open")

    # Mensagem muito antiga indica worker travado
    if idade and idade > 60:
        issues.append("message_stuck_60min")

    # Muitos erros e preocupante
    if erros_24h > 50:
        issues.append("high_error_rate")

    # Muitas mensagens acumulando
    if pendentes > 100:
        issues.append("queue_backlog")

    # Determinar status final
    if "circuit_breaker_open" in issues or "message_stuck_60min" in issues:
        status = "critical"
    elif issues:
        status = "warning"
    else:
        status = "healthy"

    return JSONResponse(
        {
            "status": status,
            "circuit_breaker": {
                "estado": circuit_estado,
                "falhas_consecutivas": circuit_status["falhas_consecutivas"],
                "ultima_falha": circuit_status["ultima_falha"],
            },
            "fila": {
                "pendentes": pendentes,
                "processando": processando,
                "mensagem_mais_antiga_min": round(idade, 1) if idade else None,
                "erros_24h": erros_24h,
            },
            "issues": issues,
        }
    )
