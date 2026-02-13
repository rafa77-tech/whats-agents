"""
Ciclo de warming de chips.

Sprint 60 - Issue #98: Registrar warming job no scheduler.
"""

import logging

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ciclo-warming")
@job_endpoint("ciclo-warming")
async def job_ciclo_warming():
    """
    Job para executar ciclo de warming de chips.

    Busca atividades pendentes no warmup_schedule, executa-as,
    verifica transicoes de fase e recalcula trust scores.

    Schedule: */5 8-20 * * 1-5 (a cada 5 min, 8h-20h, seg-sex)
    """
    from app.services.warmer.orchestrator import orchestrator

    await orchestrator.ciclo_warmup()

    status = await orchestrator.obter_status_pool()

    return {
        "status": "ok",
        "message": "Ciclo de warming executado",
        "pool": status,
    }
