"""
Dashboard campaigns endpoints.

Provides campaign management for the dashboard:
- List campaigns with filters
- Create/update campaigns
- Start/pause campaigns
- Audience counting

DB Column Mapping:
- nome_template -> nome (API)
- tipo_campanha -> tipo (API)
- corpo -> mensagem (API)
- agendar_para -> scheduled_at (API)
- iniciada_em -> started_at (API)
- concluida_em -> completed_at (API)
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
    audience_filters: Optional[Dict[str, Any]] = None
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: str
    created_by: Optional[str] = None


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


def _map_db_to_summary(c: dict) -> CampaignSummary:
    """Map DB row to CampaignSummary."""
    return CampaignSummary(
        id=c["id"],
        nome=c.get("nome_template") or "Sem nome",
        tipo=c.get("tipo_campanha") or "custom",
        status=c.get("status") or "rascunho",
        total_destinatarios=c.get("total_destinatarios") or 0,
        enviados=c.get("enviados") or 0,
        entregues=c.get("entregues") or 0,
        respondidos=c.get("respondidos") or 0,
        scheduled_at=c.get("agendar_para"),
        created_at=c["created_at"]
    )


def _map_db_to_detail(c: dict) -> CampaignDetail:
    """Map DB row to CampaignDetail."""
    return CampaignDetail(
        id=c["id"],
        nome=c.get("nome_template") or "Sem nome",
        tipo=c.get("tipo_campanha") or "custom",
        mensagem=c.get("corpo") or "",
        status=c.get("status") or "rascunho",
        total_destinatarios=c.get("total_destinatarios") or 0,
        enviados=c.get("enviados") or 0,
        entregues=c.get("entregues") or 0,
        respondidos=c.get("respondidos") or 0,
        audience_filters=c.get("audience_filters") or {},
        scheduled_at=c.get("agendar_para"),
        started_at=c.get("iniciada_em"),
        completed_at=c.get("concluida_em"),
        created_at=c["created_at"],
        created_by=c.get("created_by")
    )


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

        campaigns = [_map_db_to_summary(c) for c in paginated]

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

        return _map_db_to_detail(result.data)

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

        # Base insert - only columns that definitely exist in schema cache
        insert_data = {
            "nome_template": data.nome,
            "tipo_campanha": data.tipo,
            "corpo": data.mensagem,
            "status": "rascunho",
        }

        if data.scheduled_at:
            insert_data["agendar_para"] = data.scheduled_at
            insert_data["status"] = "agendada"

        # Try with all columns, progressively fall back
        new_columns = {
            "total_destinatarios": audience_count,
            "enviados": 0,
            "entregues": 0,
            "respondidos": 0,
            "audience_filters": data.audience_filters,
            "created_by": user.email,
        }

        # Try full insert first
        try:
            result = supabase.table("campanhas").insert({
                **insert_data, **new_columns
            }).execute()
        except Exception as e:
            if "PGRST204" in str(e):
                # Schema cache issue - try without new columns
                logger.warning(f"Schema cache issue, using minimal insert: {e}")
                result = supabase.table("campanhas").insert(insert_data).execute()
            else:
                raise

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

        return await get_campaign(str(campaign_id), user)

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

        valid_states = ["rascunho", "agendada", "pausada", "draft", "scheduled", "paused"]
        if existing.data["status"] not in valid_states:
            raise HTTPException(400, "Campanha nao pode ser iniciada")

        # Update status using DB column names
        supabase.table("campanhas").update({
            "status": "executando",
            "iniciada_em": datetime.now().isoformat()
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

        return {"success": True, "status": "executando"}

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

        if existing.data["status"] not in ["executando", "running"]:
            raise HTTPException(400, "Campanha nao esta em execucao")

        # Update status
        supabase.table("campanhas").update({
            "status": "pausada"
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

        return {"success": True, "status": "pausada"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao pausar campanha {campaign_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
