"""
Dashboard campaigns endpoints.

Provides campaign management for the dashboard:
- List campaigns with filters
- Create/update campaigns
- Start/pause campaigns
- Audience counting
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from app.api.routes.dashboard import (
    CurrentUser,
    require_operator,
    DashboardUser,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["dashboard-campaigns"])


# Request/Response Models
class CampaignSummary(BaseModel):
    id: int
    nome: str
    tipo: str
    status: str
    total_destinatarios: int
    enviados: int
    entregues: int
    respondidos: int
    scheduled_at: Optional[str] = None
    created_at: str


class CampaignDetail(BaseModel):
    id: int
    nome: str
    tipo: str
    mensagem: str
    status: str
    total_destinatarios: int
    enviados: int
    entregues: int
    respondidos: int
    audience_filters: Optional[Dict[str, Any]] = None  # Optional - may not exist in DB
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    created_by: Optional[str] = None  # Optional - may not exist in DB


class PaginatedCampaignsResponse(BaseModel):
    data: List[CampaignSummary]
    total: int
    page: int
    per_page: int
    pages: int


class CampaignCreate(BaseModel):
    nome: str
    tipo: str
    mensagem: str
    scheduled_at: Optional[str] = None
    audience_filters: Dict[str, Any] = {}


class AudienceFilters(BaseModel):
    stage_jornada: Optional[List[str]] = None
    especialidades: Optional[List[str]] = None
    ultimo_contato_dias: Optional[int] = None


@router.get("", response_model=PaginatedCampaignsResponse)
async def list_campaigns(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None
):
    """Lista campanhas com filtros."""

    try:
        query = supabase.table("campanhas").select("*")

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()
        all_data = result.data or []

        total = len(all_data)
        offset = (page - 1) * per_page
        paginated = all_data[offset:offset + per_page]

        campaigns = []
        for c in paginated:
            campaigns.append(CampaignSummary(
                id=c["id"],
                nome=c.get("nome", "Sem nome"),
                tipo=c.get("tipo", "custom"),
                status=c.get("status", "draft"),
                total_destinatarios=c.get("total_destinatarios", 0),
                enviados=c.get("enviados", 0),
                entregues=c.get("entregues", 0),
                respondidos=c.get("respondidos", 0),
                scheduled_at=c.get("scheduled_at"),
                created_at=c["created_at"]
            ))

        return PaginatedCampaignsResponse(
            data=campaigns,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if total > 0 else 1
        )

    except Exception as e:
        logger.error(f"Erro ao listar campanhas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audience-options")
async def get_audience_options(user: CurrentUser):
    """Retorna opcoes de filtro disponiveis."""

    try:
        # Get unique stage_jornada values
        stages = supabase.table("clientes").select("stage_jornada").execute()
        unique_stages = list(set(
            s["stage_jornada"] for s in stages.data
            if s.get("stage_jornada")
        ))

        # Get especialidades
        especialidades = supabase.table("especialidades").select(
            "id, nome"
        ).order("nome").execute()

        return {
            "stages": unique_stages,
            "especialidades": [
                {"id": e["id"], "nome": e["nome"]}
                for e in especialidades.data
            ]
        }

    except Exception as e:
        logger.error(f"Erro ao buscar opcoes de audiencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audience-count")
async def get_audience_count(
    filters: AudienceFilters,
    user: CurrentUser
):
    """Conta destinatarios com filtros."""

    try:
        query = supabase.table("clientes").select("id", count="exact")

        # Exclude opt-out
        query = query.eq("opt_out", False)

        if filters.stage_jornada:
            query = query.in_("stage_jornada", filters.stage_jornada)

        # Note: ultimo_contato_dias would need a more complex query
        # For now, simplified

        result = query.execute()

        return {"count": result.count or 0}

    except Exception as e:
        logger.error(f"Erro ao contar audiencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def get_campaign(campaign_id: str, user: CurrentUser):
    """Detalhes de uma campanha."""

    try:
        result = supabase.table("campanhas").select(
            "*"
        ).eq("id", campaign_id).single().execute()

        if not result.data:
            raise HTTPException(404, "Campanha nao encontrada")

        c = result.data

        return CampaignDetail(
            id=c["id"],
            nome=c.get("nome", "Sem nome"),
            tipo=c.get("tipo", "custom"),
            mensagem=c.get("mensagem", ""),
            status=c.get("status", "draft"),
            total_destinatarios=c.get("total_destinatarios", 0),
            enviados=c.get("enviados", 0),
            entregues=c.get("entregues", 0),
            respondidos=c.get("respondidos", 0),
            audience_filters=c.get("audience_filters") or {},
            scheduled_at=c.get("scheduled_at"),
            started_at=c.get("started_at"),
            completed_at=c.get("completed_at"),
            created_at=c["created_at"],
            created_by=c.get("created_by")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar campanha {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=CampaignDetail)
async def create_campaign(
    data: CampaignCreate,
    user: DashboardUser = Depends(require_operator)
):
    """Cria nova campanha."""

    try:
        # Count audience (simplified - count all non-opt-out)
        try:
            count_result = supabase.table("clientes").select(
                "id", count="exact"
            ).eq("opt_out", False).execute()
            audience_count = count_result.count or 0
        except Exception:
            audience_count = 0

        # Base insert data - only use columns that definitely exist
        insert_data = {
            "nome": data.nome,
            "tipo": data.tipo,
            "mensagem": data.mensagem,
            "status": "draft",
            "total_destinatarios": audience_count,
            "enviados": 0,
            "entregues": 0,
            "respondidos": 0,
        }

        if data.scheduled_at:
            insert_data["scheduled_at"] = data.scheduled_at
            insert_data["status"] = "scheduled"

        result = supabase.table("campanhas").insert(insert_data).execute()

        if not result.data:
            raise HTTPException(500, "Erro ao criar campanha")

        campaign_id = result.data[0]["id"]

        # Audit log (optional - don't fail if table doesn't exist)
        try:
            supabase.table("audit_logs").insert({
                "action": "create_campaign",
                "actor_email": user.email,
                "actor_role": str(user.role),
                "details": {"campaign_id": campaign_id, "nome": data.nome},
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed (non-critical): {e}")

        logger.info(f"Campanha {campaign_id} criada por {user.email}")

        return await get_campaign(campaign_id, user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    user: DashboardUser = Depends(require_operator)
):
    """Inicia execucao da campanha."""

    try:
        # Verify campaign exists and is in valid state
        existing = supabase.table("campanhas").select(
            "id, status"
        ).eq("id", campaign_id).single().execute()

        if not existing.data:
            raise HTTPException(404, "Campanha nao encontrada")

        if existing.data["status"] not in ["draft", "scheduled", "paused"]:
            raise HTTPException(400, "Campanha nao pode ser iniciada")

        # Update status
        supabase.table("campanhas").update({
            "status": "running",
            "started_at": datetime.now().isoformat()
        }).eq("id", campaign_id).execute()

        # Audit log (optional)
        try:
            supabase.table("audit_logs").insert({
                "action": "start_campaign",
                "actor_email": user.email,
                "actor_role": str(user.role),
                "details": {"campaign_id": campaign_id},
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed (non-critical): {e}")

        logger.info(f"Campanha {campaign_id} iniciada por {user.email}")

        return {"success": True, "status": "running"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao iniciar campanha {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    user: DashboardUser = Depends(require_operator)
):
    """Pausa campanha em execucao."""

    try:
        # Verify campaign is running
        existing = supabase.table("campanhas").select(
            "id, status"
        ).eq("id", campaign_id).single().execute()

        if not existing.data:
            raise HTTPException(404, "Campanha nao encontrada")

        if existing.data["status"] != "running":
            raise HTTPException(400, "Campanha nao esta em execucao")

        # Update status
        supabase.table("campanhas").update({
            "status": "paused"
        }).eq("id", campaign_id).execute()

        # Audit log (optional)
        try:
            supabase.table("audit_logs").insert({
                "action": "pause_campaign",
                "actor_email": user.email,
                "actor_role": str(user.role),
                "details": {"campaign_id": campaign_id},
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.warning(f"Audit log failed (non-critical): {e}")

        logger.info(f"Campanha {campaign_id} pausada por {user.email}")

        return {"success": True, "status": "paused"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao pausar campanha {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
