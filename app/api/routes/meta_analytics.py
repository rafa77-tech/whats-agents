"""
API endpoints para Meta Template & Conversation Analytics.

Sprint 67 - Epic 67.3/67.4: Analytics endpoints.

Autenticação: X-API-Key header (mesmo padrão do admin).
"""

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta/analytics", tags=["Meta Analytics"])


def _verificar_api_key(request: Request) -> None:
    """Verifica X-API-Key no header."""
    api_key = request.headers.get("X-API-Key", "")
    expected = settings.SUPABASE_SERVICE_KEY
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="API key inválida")


@router.get("/templates/ranking")
async def ranking_templates(
    request: Request,
    waba_id: str = Query(None, description="Filtrar por WABA ID"),
    days: int = Query(7, ge=1, le=90, description="Período em dias"),
    limit: int = Query(20, ge=1, le=100),
):
    """Ranking de templates por delivery rate."""
    _verificar_api_key(request)

    from app.services.meta.template_analytics import template_analytics

    ranking = await template_analytics.obter_ranking_templates(
        waba_id=waba_id, days=days, limit=limit
    )
    return JSONResponse({"status": "ok", "data": ranking, "count": len(ranking)})


@router.get("/templates/{template_name}")
async def analytics_template(
    request: Request,
    template_name: str,
    waba_id: str = Query(None),
    days: int = Query(30, ge=1, le=90),
):
    """Analytics detalhado de um template."""
    _verificar_api_key(request)

    from app.services.meta.template_analytics import template_analytics

    data = await template_analytics.obter_analytics_template(
        template_name=template_name, waba_id=waba_id, days=days
    )
    return JSONResponse({"status": "ok", "data": data, "count": len(data)})


@router.get("/mm-lite/stats")
async def mm_lite_stats(
    request: Request,
    waba_id: str = Query(None),
    days: int = Query(7, ge=1, le=90),
):
    """Estatísticas de envios MM Lite."""
    _verificar_api_key(request)

    from app.services.meta.mm_lite import mm_lite_service

    stats = await mm_lite_service.obter_metricas(waba_id=waba_id, days=days)
    return JSONResponse({"status": "ok", "data": stats})


@router.get("/templates/alerts/low-performance")
async def templates_baixa_performance(
    request: Request,
    waba_id: str = Query(None),
    days: int = Query(7, ge=1, le=30),
):
    """Templates com baixa performance."""
    _verificar_api_key(request)

    from app.services.meta.template_analytics import template_analytics

    alertas = await template_analytics.detectar_templates_baixa_performance(
        waba_id=waba_id, days=days
    )
    return JSONResponse({"status": "ok", "data": alertas, "count": len(alertas)})
