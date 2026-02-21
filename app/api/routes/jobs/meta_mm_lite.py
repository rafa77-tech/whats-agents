"""
Job de métricas MM Lite.

Sprint 68 — Epic 68.1, Chunk 3.
"""

import logging

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/meta-mm-lite-metrics")
@job_endpoint("meta-mm-lite-metrics")
async def job_meta_mm_lite_metrics():
    """
    Coleta métricas de envios MM Lite.

    Cron: 0 7 * * * (diário às 7h)
    """
    from app.services.meta.mm_lite import mm_lite_service

    metricas = await mm_lite_service.obter_metricas()
    return {
        "status": "ok",
        "processados": metricas["total_sent"],
        **metricas,
    }
