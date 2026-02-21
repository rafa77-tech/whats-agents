"""
Meta Dashboard API endpoints.

Sprint 69 — Epic 69.2, Chunk 16.

Dashboard-specific aggregation endpoints.
"""

import hmac
import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta/dashboard", tags=["Meta Dashboard"])


def _verificar_api_key(request: Request) -> None:
    """Verifica X-API-Key no header."""
    api_key = request.headers.get("X-API-Key", "")
    expected = settings.META_API_KEY
    if not api_key or not expected or not hmac.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="API key inválida")


@router.get("/quality/overview")
async def quality_overview(request: Request):
    """Overview de qualidade de todos os chips Meta."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    overview = await dashboard_service.obter_quality_overview()
    return JSONResponse({"status": "ok", "data": overview})


@router.get("/quality/history")
async def quality_history(
    request: Request,
    chip_id: str = Query(None),
    days: int = Query(30, ge=1, le=90),
):
    """Histórico de qualidade por chip."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    history = await dashboard_service.obter_quality_history(chip_id=chip_id, days=days)
    return JSONResponse({"status": "ok", "data": history, "count": len(history)})


@router.post("/quality/kill-switch")
async def quality_kill_switch(
    request: Request,
    waba_id: str = Query(...),
):
    """Kill switch — desativa todos os chips de uma WABA."""
    _verificar_api_key(request)

    from app.services.meta.quality_monitor import quality_monitor

    result = await quality_monitor.kill_switch_waba(waba_id)
    return JSONResponse({"status": "ok", "data": result})


@router.get("/costs/summary")
async def costs_summary(
    request: Request,
    days: int = Query(7, ge=1, le=90),
):
    """Resumo de custos por período."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    summary = await dashboard_service.obter_cost_summary(days=days)
    return JSONResponse({"status": "ok", "data": summary})


@router.get("/costs/by-chip")
async def costs_by_chip(
    request: Request,
    days: int = Query(7, ge=1, le=90),
):
    """Custo por chip."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    data = await dashboard_service.obter_cost_by_chip(days=days)
    return JSONResponse({"status": "ok", "data": data, "count": len(data)})


@router.get("/costs/by-template")
async def costs_by_template(
    request: Request,
    days: int = Query(7, ge=1, le=90),
):
    """Custo por template."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    data = await dashboard_service.obter_cost_by_template(days=days)
    return JSONResponse({"status": "ok", "data": data, "count": len(data)})


@router.get("/templates/list")
async def templates_list(
    request: Request,
    waba_id: str = Query(None),
):
    """Lista templates com analytics joinados."""
    _verificar_api_key(request)

    from app.services.meta.dashboard_service import dashboard_service

    data = await dashboard_service.obter_templates_com_analytics(waba_id=waba_id)
    return JSONResponse({"status": "ok", "data": data, "count": len(data)})
