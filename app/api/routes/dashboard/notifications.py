"""
Dashboard notifications endpoints.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth import DashboardUser, get_current_user
from app.services.supabase import supabase

router = APIRouter(prefix="/notifications", tags=["dashboard-notifications"])


class NotificationConfigUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    toast_enabled: Optional[bool] = None
    types: Optional[dict] = None


class PushSubscriptionData(BaseModel):
    subscription: dict


@router.get("")
async def list_notifications(
    user: DashboardUser = Depends(get_current_user),
    limit: int = Query(50, le=100),
    unread_only: bool = False,
):
    """Lista notificacoes do usuario."""
    query = (
        supabase.table("dashboard_notifications")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if unread_only:
        query = query.eq("read", False)

    result = query.execute()

    return {"notifications": result.data or []}


@router.get("/unread-count")
async def get_unread_count(user: DashboardUser = Depends(get_current_user)):
    """Retorna contagem de notificacoes nao lidas."""
    result = (
        supabase.table("dashboard_notifications")
        .select("id", count="exact")
        .eq("user_id", user.id)
        .eq("read", False)
        .execute()
    )

    return {"count": result.count or 0}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: str, user: DashboardUser = Depends(get_current_user)
):
    """Marca notificacao como lida."""
    supabase.table("dashboard_notifications").update(
        {"read": True, "read_at": datetime.now().isoformat()}
    ).eq("id", notification_id).eq("user_id", user.id).execute()

    return {"success": True}


@router.post("/read-all")
async def mark_all_as_read(user: DashboardUser = Depends(get_current_user)):
    """Marca todas notificacoes como lidas."""
    result = (
        supabase.table("dashboard_notifications")
        .update({"read": True, "read_at": datetime.now().isoformat()})
        .eq("user_id", user.id)
        .eq("read", False)
        .execute()
    )

    return {"success": True, "count": len(result.data) if result.data else 0}


@router.get("/config")
async def get_notification_config(user: DashboardUser = Depends(get_current_user)):
    """Retorna configuracoes de notificacao do usuario."""
    result = (
        supabase.table("dashboard_notification_config")
        .select("*")
        .eq("user_id", user.id)
        .maybeSingle()
        .execute()
    )

    if not result.data:
        return {
            "config": {
                "push_enabled": False,
                "toast_enabled": True,
                "types": {},
            }
        }

    return {"config": result.data}


@router.put("/config")
async def update_notification_config(
    config: NotificationConfigUpdate, user: DashboardUser = Depends(get_current_user)
):
    """Atualiza configuracoes de notificacao."""
    data = {k: v for k, v in config.model_dump().items() if v is not None}
    data["user_id"] = user.id
    data["updated_at"] = datetime.now().isoformat()

    supabase.table("dashboard_notification_config").upsert(
        data, on_conflict="user_id"
    ).execute()

    return {"success": True}


@router.post("/push-subscription")
async def save_push_subscription(
    data: PushSubscriptionData, user: DashboardUser = Depends(get_current_user)
):
    """Salva subscription de push do usuario."""
    supabase.table("dashboard_push_subscriptions").upsert(
        {
            "user_id": user.id,
            "subscription": data.subscription,
            "updated_at": datetime.now().isoformat(),
        },
        on_conflict="user_id",
    ).execute()

    return {"success": True}


@router.delete("/push-subscription")
async def delete_push_subscription(user: DashboardUser = Depends(get_current_user)):
    """Remove subscription de push do usuario."""
    supabase.table("dashboard_push_subscriptions").delete().eq(
        "user_id", user.id
    ).execute()

    return {"success": True}
