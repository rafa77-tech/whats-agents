"""
Dashboard audit endpoints.

Provides audit log management:
- List audit logs with filters
- Export to CSV (admin only)
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import logging
import csv
import io

from app.api.routes.dashboard import (
    CurrentUser,
    require_manager,
    require_admin,
    DashboardUser,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["dashboard-audit"])


@router.get("")
async def list_audit_logs(
    user: DashboardUser = Depends(require_manager),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    actor_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Lista logs de auditoria. Requer role manager ou admin."""

    try:
        # Build query
        query = supabase.table("audit_logs").select("*")

        if action:
            query = query.eq("action", action)
        if actor_email:
            query = query.ilike("actor_email", f"%{actor_email}%")
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", f"{to_date}T23:59:59")

        # Get all for count (supabase doesn't support count with filters well)
        result = query.order("created_at", desc=True).execute()
        all_data = result.data or []

        total = len(all_data)
        offset = (page - 1) * per_page
        paginated = all_data[offset:offset + per_page]

        return {
            "data": paginated,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 1
        }

    except Exception as e:
        logger.error(f"Erro ao listar audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_audit_logs(
    user: DashboardUser = Depends(require_admin),
    action: Optional[str] = None,
    actor_email: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    """Exporta logs de auditoria em CSV. Requer role admin."""

    try:
        # Build query
        query = supabase.table("audit_logs").select("*")

        if action:
            query = query.eq("action", action)
        if actor_email:
            query = query.ilike("actor_email", f"%{actor_email}%")
        if from_date:
            query = query.gte("created_at", from_date)
        if to_date:
            query = query.lte("created_at", f"{to_date}T23:59:59")

        result = query.order("created_at", desc=True).execute()
        logs = result.data or []

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID", "Acao", "Usuario", "Role", "Detalhes", "Data/Hora"
        ])

        # Data
        for log in logs:
            writer.writerow([
                log.get("id", ""),
                log.get("action", ""),
                log.get("actor_email", ""),
                log.get("actor_role", ""),
                str(log.get("details", {})),
                log.get("created_at", "")
            ])

        output.seek(0)

        # Return as streaming response
        filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Erro ao exportar audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions")
async def list_audit_actions(user: DashboardUser = Depends(require_manager)):
    """Lista tipos de acoes disponiveis para filtro."""

    return {
        "actions": [
            {"value": "julia_toggle", "label": "Toggle Julia"},
            {"value": "julia_pause", "label": "Pausar Julia"},
            {"value": "feature_flag_update", "label": "Feature Flag"},
            {"value": "rate_limit_update", "label": "Rate Limit"},
            {"value": "manual_handoff", "label": "Handoff Manual"},
            {"value": "return_to_julia", "label": "Retornar Julia"},
            {"value": "circuit_reset", "label": "Reset Circuit"},
            {"value": "create_campaign", "label": "Criar Campanha"},
            {"value": "start_campaign", "label": "Iniciar Campanha"},
            {"value": "pause_campaign", "label": "Pausar Campanha"},
        ]
    }
