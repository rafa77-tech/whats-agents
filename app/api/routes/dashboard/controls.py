"""
Dashboard control endpoints.

Provides operational controls for Julia:
- Toggle Julia on/off
- Pause for specific duration
- Feature flags management
- Rate limit configuration
- Circuit breaker reset
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.api.routes.dashboard import (
    CurrentUser,
    require_operator,
    require_manager,
    require_admin,
    DashboardUser,
)
from app.services.supabase import supabase
from app.services.circuit_breaker import (
    circuit_evolution,
    circuit_claude,
    circuit_supabase,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/controls", tags=["dashboard-controls"])


# Request Models
class JuliaToggleRequest(BaseModel):
    active: bool
    reason: Optional[str] = None


class JuliaPauseRequest(BaseModel):
    duration_minutes: int
    reason: str


class FeatureFlagUpdate(BaseModel):
    enabled: bool


class RateLimitUpdate(BaseModel):
    messages_per_hour: int
    messages_per_day: int


# Endpoints

@router.post("/julia/toggle")
async def toggle_julia(
    request: JuliaToggleRequest,
    user: DashboardUser = Depends(require_operator)
):
    """Liga/desliga Julia. Requer role operator+."""

    try:
        result = supabase.table("julia_status").insert({
            "is_active": request.active,
            "mode": "auto" if request.active else "paused",
            "pause_reason": request.reason if not request.active else None,
            "changed_by": user.email,
            "created_at": datetime.now().isoformat()
        }).execute()

        # Log de auditoria
        supabase.table("audit_logs").insert({
            "action": "julia_toggle",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "active": request.active,
                "reason": request.reason
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Julia toggled to {request.active} by {user.email}")

        return {"success": True, "is_active": request.active}

    except Exception as e:
        logger.error(f"Erro ao toggle Julia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/julia/pause")
async def pause_julia(
    request: JuliaPauseRequest,
    user: DashboardUser = Depends(require_operator)
):
    """Pausa Julia por tempo determinado."""

    if request.duration_minutes < 1 or request.duration_minutes > 1440:
        raise HTTPException(400, "Duracao deve ser entre 1 e 1440 minutos (24h)")

    paused_until = datetime.now() + timedelta(minutes=request.duration_minutes)

    try:
        result = supabase.table("julia_status").insert({
            "is_active": False,
            "mode": "paused",
            "paused_until": paused_until.isoformat(),
            "pause_reason": request.reason,
            "changed_by": user.email,
            "created_at": datetime.now().isoformat()
        }).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "julia_pause",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "duration_minutes": request.duration_minutes,
                "paused_until": paused_until.isoformat(),
                "reason": request.reason
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Julia paused for {request.duration_minutes}min by {user.email}")

        return {"success": True, "paused_until": paused_until}

    except Exception as e:
        logger.error(f"Erro ao pausar Julia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flags")
async def list_feature_flags(user: CurrentUser):
    """Lista feature flags. Viewer+."""

    try:
        result = supabase.table("feature_flags").select("*").execute()
        return {"flags": result.data}
    except Exception as e:
        logger.error(f"Erro ao listar feature flags: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/flags/{flag_name}")
async def update_feature_flag(
    flag_name: str,
    request: FeatureFlagUpdate,
    user: DashboardUser = Depends(require_manager)
):
    """Atualiza feature flag. Requer manager+."""

    try:
        # Verificar se existe
        existing = supabase.table("feature_flags").select("*").eq(
            "name", flag_name
        ).execute()

        if not existing.data:
            raise HTTPException(status_code=404, detail="Flag nao encontrada")

        result = supabase.table("feature_flags").update({
            "enabled": request.enabled,
            "updated_by": user.email,
            "updated_at": datetime.now().isoformat()
        }).eq("name", flag_name).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "feature_flag_update",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "flag": flag_name,
                "enabled": request.enabled
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Feature flag {flag_name} set to {request.enabled} by {user.email}")

        return {"success": True, "flag": flag_name, "enabled": request.enabled}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar feature flag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rate-limit")
async def update_rate_limit(
    request: RateLimitUpdate,
    user: DashboardUser = Depends(require_admin)
):
    """Atualiza limites de rate. Requer admin."""

    # Validacoes
    if request.messages_per_hour < 1 or request.messages_per_hour > 50:
        raise HTTPException(400, "Limite por hora deve ser entre 1 e 50")
    if request.messages_per_day < 10 or request.messages_per_day > 200:
        raise HTTPException(400, "Limite por dia deve ser entre 10 e 200")

    try:
        result = supabase.table("system_config").upsert({
            "key": "rate_limit",
            "value": {
                "messages_per_hour": request.messages_per_hour,
                "messages_per_day": request.messages_per_day
            },
            "updated_by": user.email,
            "updated_at": datetime.now().isoformat()
        }).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "rate_limit_update",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "messages_per_hour": request.messages_per_hour,
                "messages_per_day": request.messages_per_day
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Rate limit updated to {request.messages_per_hour}/h, {request.messages_per_day}/d by {user.email}")

        return {"success": True, "new_limits": request.model_dump()}

    except Exception as e:
        logger.error(f"Erro ao atualizar rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit/{service}/reset")
async def reset_circuit_breaker(
    service: str,
    user: DashboardUser = Depends(require_manager)
):
    """Reset circuit breaker. Requer manager+."""

    circuits = {
        "evolution": circuit_evolution,
        "claude": circuit_claude,
        "supabase": circuit_supabase,
    }

    if service not in circuits:
        raise HTTPException(400, f"Servico invalido. Use: {list(circuits.keys())}")

    try:
        circuits[service].reset()

        # Log
        supabase.table("audit_logs").insert({
            "action": "circuit_reset",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {"service": service},
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Circuit {service} reset by {user.email}")

        return {"success": True, "service": service, "status": "closed"}

    except Exception as e:
        logger.error(f"Erro ao resetar circuit {service}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
