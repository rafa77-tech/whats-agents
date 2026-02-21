"""
Job de verificação de qualidade de chips Meta.

Sprint 67 - Epic 67.1: Quality Monitor.
"""

import logging

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/meta-quality-check")
@job_endpoint("meta-quality-check")
async def job_meta_quality_check():
    """
    Verifica qualidade de todos os chips Meta ativos.

    Cron: */15 * * * * (a cada 15 minutos)
    """
    from app.services.meta.quality_monitor import quality_monitor

    resultado = await quality_monitor.verificar_quality_chips()
    return {
        "status": "ok",
        "processados": resultado["verificados"],
        **resultado,
    }
