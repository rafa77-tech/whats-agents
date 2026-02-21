"""
Job de verificação de qualidade de chips Meta e window management.

Sprint 67 - Epic 67.1: Quality Monitor.
Sprint 71 - Epic 71.4: Window Keeper.
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


@router.post("/meta-window-keeper")
@job_endpoint("meta-window-keeper")
async def job_meta_window_keeper():
    """
    Gerencia janelas de conversa proativamente.

    Sprint 71 — Epic 71.4.
    v2: envia check-in para manter janelas abertas (opt-in por chip).

    Cron: 0 8,10,12,14,16,18 * * 1-5 (a cada 2h, seg-sex)
    """
    from app.services.meta.window_keeper import window_keeper

    resultado = await window_keeper.executar_check_in()
    return {
        "status": "ok",
        "processados": resultado.get("enviados", 0),
        **resultado,
    }
