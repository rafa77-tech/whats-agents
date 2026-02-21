"""
Jobs de analytics Meta: template analytics e budget check.

Sprint 67 - Epics 67.3/67.4.
"""

import logging

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/meta-template-analytics")
@job_endpoint("meta-template-analytics")
async def job_meta_template_analytics():
    """
    Coleta analytics de templates Meta.

    Cron: 0 6 * * * (diário às 6h)
    """
    from app.services.meta.template_analytics import template_analytics

    resultado = await template_analytics.coletar_analytics()
    return {
        "status": "ok",
        "processados": resultado["templates_atualizados"],
        **resultado,
    }


@router.post("/meta-budget-check")
@job_endpoint("meta-budget-check")
async def job_meta_budget_check():
    """
    Verifica budget diário Meta e alerta se necessário.

    Cron: 0 * * * * (a cada hora)
    """
    from app.services.meta.conversation_analytics import conversation_analytics

    budget_info = await conversation_analytics.alertar_budget_excedido()

    if budget_info:
        return {
            "status": "ok",
            "alerta": True,
            **budget_info,
        }

    return {"status": "ok", "alerta": False, "message": "Budget dentro do limite"}
