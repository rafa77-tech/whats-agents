"""
Jobs de analytics Meta: template analytics, budget check, template optimization.

Sprint 67 - Epics 67.3/67.4.
Sprint 71 - Epic 71.3: Template optimization.
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


@router.post("/meta-template-optimization")
@job_endpoint("meta-template-optimization")
async def job_meta_template_optimization():
    """
    Analisa performance de templates e salva recomendações.

    Sprint 71 — Epic 71.3.
    Cron: 0 5 * * 1 (segunda às 5h)
    """
    from app.services.meta.template_optimizer import template_optimizer
    from app.services.supabase import supabase
    from datetime import datetime, timezone

    problemas = await template_optimizer.identificar_baixa_performance(days=7)

    # Salvar recomendações no banco
    for p in problemas:
        sugestoes = await template_optimizer.sugerir_melhorias(p["template_name"])
        try:
            supabase.table("meta_template_recommendations").upsert(
                {
                    "template_name": p["template_name"],
                    "waba_id": p.get("waba_id", ""),
                    "delivery_rate": p["delivery_rate"],
                    "read_rate": p["read_rate"],
                    "total_sent": p["total_sent"],
                    "issues": p["issues"],
                    "suggestions": [s["mensagem"] for s in sugestoes],
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="template_name",
            ).execute()
        except Exception as e:
            logger.warning("[TemplateOptimization] Erro ao salvar recomendação: %s", e)

    return {
        "status": "ok",
        "processados": len(problemas),
        "templates_com_problemas": [p["template_name"] for p in problemas],
    }
