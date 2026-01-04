"""
Dashboard doctors endpoints.

Provides doctor management for the dashboard:
- List doctors with filters and pagination
- Get doctor details
- Get doctor timeline (interactions history)
- Update funnel status
- Toggle opt-out
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from app.api.routes.dashboard import (
    CurrentUser,
    require_operator,
    DashboardUser,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["dashboard-doctors"])


# Response Models
class DoctorSummary(BaseModel):
    id: str
    nome: str
    telefone: str
    especialidade: Optional[str] = None
    cidade: Optional[str] = None
    stage_jornada: Optional[str] = None
    opt_out: bool = False
    created_at: datetime


class DoctorDetail(BaseModel):
    id: str
    nome: str
    telefone: str
    crm: Optional[str] = None
    especialidade: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    email: Optional[str] = None
    stage_jornada: Optional[str] = None
    opt_out: bool = False
    opt_out_data: Optional[datetime] = None
    pressure_score_atual: Optional[int] = None
    contexto_consolidado: Optional[str] = None
    created_at: datetime
    conversations_count: int = 0
    last_interaction_at: Optional[datetime] = None


class TimelineEvent(BaseModel):
    id: str
    type: str
    title: str
    description: Optional[str] = None
    created_at: datetime
    metadata: Optional[dict] = None


class PaginatedDoctorsResponse(BaseModel):
    data: List[DoctorSummary]
    total: int
    page: int
    per_page: int
    pages: int


class TimelineResponse(BaseModel):
    events: List[TimelineEvent]


class FunnelUpdateRequest(BaseModel):
    status: str


class OptOutRequest(BaseModel):
    opt_out: bool


@router.get("", response_model=PaginatedDoctorsResponse)
async def list_doctors(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    stage_jornada: Optional[str] = None,
    especialidade: Optional[str] = None,
    opt_out: Optional[bool] = None,
    search: Optional[str] = None
):
    """Lista médicos com filtros e paginacao."""

    try:
        # Build query
        query = supabase.table("clientes").select(
            "id, primeiro_nome, sobrenome, telefone, especialidade, cidade, stage_jornada, opt_out, created_at"
        )

        if stage_jornada:
            query = query.eq("stage_jornada", stage_jornada)
        if especialidade:
            query = query.ilike("especialidade", f"%{especialidade}%")
        if opt_out is not None:
            query = query.eq("opt_out", opt_out)

        # Execute
        result = query.execute()
        filtered_data = result.data

        # Search filter (post-query)
        if search:
            search_lower = search.lower()
            filtered_data = [
                d for d in filtered_data
                if (d.get("primeiro_nome", "").lower().find(search_lower) >= 0 or
                    d.get("sobrenome", "").lower().find(search_lower) >= 0 or
                    d.get("telefone", "").find(search) >= 0 or
                    (d.get("crm") or "").find(search) >= 0)
            ]

        total = len(filtered_data)

        # Sort by created_at desc
        filtered_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Paginate
        offset = (page - 1) * per_page
        paginated_data = filtered_data[offset:offset + per_page]

        # Map to response
        doctors = []
        for doc in paginated_data:
            primeiro = doc.get("primeiro_nome", "")
            sobrenome = doc.get("sobrenome", "")
            nome = f"{primeiro} {sobrenome}".strip() or "Desconhecido"

            doctors.append(DoctorSummary(
                id=doc["id"],
                nome=nome,
                telefone=doc.get("telefone", ""),
                especialidade=doc.get("especialidade"),
                cidade=doc.get("cidade"),
                stage_jornada=doc.get("stage_jornada"),
                opt_out=doc.get("opt_out", False),
                created_at=doc["created_at"]
            ))

        return PaginatedDoctorsResponse(
            data=doctors,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if total > 0 else 1
        )

    except Exception as e:
        logger.error(f"Erro ao listar médicos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doctor_id}", response_model=DoctorDetail)
async def get_doctor(doctor_id: str, user: CurrentUser):
    """Detalhes de um médico."""

    try:
        # Get doctor
        doc_result = supabase.table("clientes").select("*").eq(
            "id", doctor_id
        ).single().execute()

        if not doc_result.data:
            raise HTTPException(404, "Médico não encontrado")

        doc = doc_result.data

        # Build nome
        primeiro = doc.get("primeiro_nome", "")
        sobrenome = doc.get("sobrenome", "")
        nome = f"{primeiro} {sobrenome}".strip() or "Desconhecido"

        # Get conversations count
        conv_result = supabase.table("conversations").select(
            "id", count="exact"
        ).eq("cliente_id", doctor_id).execute()
        conversations_count = conv_result.count or 0

        # Get last interaction
        last_interaction = None
        interaction_result = supabase.table("interacoes").select(
            "created_at"
        ).eq("cliente_id", doctor_id).order(
            "created_at", desc=True
        ).limit(1).execute()

        if interaction_result.data:
            last_interaction = interaction_result.data[0].get("created_at")

        return DoctorDetail(
            id=doc["id"],
            nome=nome,
            telefone=doc.get("telefone", ""),
            crm=doc.get("crm"),
            especialidade=doc.get("especialidade"),
            cidade=doc.get("cidade"),
            estado=doc.get("estado"),
            email=doc.get("email"),
            stage_jornada=doc.get("stage_jornada"),
            opt_out=doc.get("opt_out", False),
            opt_out_data=doc.get("opt_out_data"),
            pressure_score_atual=doc.get("pressure_score_atual"),
            contexto_consolidado=doc.get("contexto_consolidado"),
            created_at=doc["created_at"],
            conversations_count=conversations_count,
            last_interaction_at=last_interaction
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar médico {doctor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doctor_id}/timeline", response_model=TimelineResponse)
async def get_doctor_timeline(doctor_id: str, user: CurrentUser):
    """Timeline de interações do médico."""

    try:
        events: List[TimelineEvent] = []

        # Get interactions
        interactions = supabase.table("interacoes").select(
            "id, origem, conteudo, created_at"
        ).eq("cliente_id", doctor_id).order(
            "created_at", desc=True
        ).limit(50).execute()

        for interaction in interactions.data:
            origem = interaction.get("origem", "")
            event_type = "message_received" if origem == "medico" else "message_sent"
            title = "Mensagem recebida" if origem == "medico" else "Mensagem enviada"

            # Truncate content for description
            content = interaction.get("conteudo", "")
            description = content[:100] + "..." if len(content) > 100 else content

            events.append(TimelineEvent(
                id=str(interaction["id"]),
                type=event_type,
                title=title,
                description=description,
                created_at=interaction["created_at"]
            ))

        # Get handoffs (via conversations)
        # First get conversation IDs for this doctor
        convs = supabase.table("conversations").select("id").eq(
            "cliente_id", doctor_id
        ).execute()

        conv_ids = [c["id"] for c in convs.data] if convs.data else []

        if conv_ids:
            handoffs = supabase.table("handoffs").select(
                "id, reason, created_at"
            ).in_("conversation_id", conv_ids).order(
                "created_at", desc=True
            ).limit(20).execute()

            for handoff in handoffs.data:
                events.append(TimelineEvent(
                    id=handoff["id"],
                    type="handoff",
                    title="Transferencia para humano",
                    description=handoff.get("reason"),
                    created_at=handoff["created_at"]
                ))

        # Sort all events by date
        events.sort(key=lambda x: x.created_at, reverse=True)

        return TimelineResponse(events=events[:50])

    except Exception as e:
        logger.error(f"Erro ao buscar timeline do médico {doctor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{doctor_id}/funnel")
async def update_funnel_status(
    doctor_id: str,
    data: FunnelUpdateRequest,
    user: DashboardUser = Depends(require_operator)
):
    """Atualiza status do funil."""

    try:
        # Verify doctor exists
        existing = supabase.table("clientes").select("id").eq(
            "id", doctor_id
        ).execute()

        if not existing.data:
            raise HTTPException(404, "Médico não encontrado")

        # Update
        supabase.table("clientes").update({
            "stage_jornada": data.status
        }).eq("id", doctor_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "update_funnel_status",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "doctor_id": doctor_id,
                "new_status": data.status
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Funnel updated for {doctor_id} to {data.status} by {user.email}")

        return {"success": True, "stage_jornada": data.status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar funil do médico {doctor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{doctor_id}/opt-out")
async def toggle_opt_out(
    doctor_id: str,
    data: OptOutRequest,
    user: DashboardUser = Depends(require_operator)
):
    """Toggle opt-out do médico."""

    try:
        # Verify doctor exists
        existing = supabase.table("clientes").select("id").eq(
            "id", doctor_id
        ).execute()

        if not existing.data:
            raise HTTPException(404, "Médico não encontrado")

        # Update
        update_data = {
            "opt_out": data.opt_out
        }
        if data.opt_out:
            update_data["opt_out_data"] = datetime.now().isoformat()
        else:
            update_data["opt_out_data"] = None

        supabase.table("clientes").update(update_data).eq("id", doctor_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "toggle_opt_out",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "doctor_id": doctor_id,
                "opt_out": data.opt_out
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Opt-out toggled for {doctor_id} to {data.opt_out} by {user.email}")

        return {"success": True, "opt_out": data.opt_out}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao toggle opt-out do médico {doctor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
