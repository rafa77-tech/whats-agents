"""
Dashboard shifts endpoints.

Provides shift/vaga management for the dashboard:
- List shifts with filters and pagination
- Get shift details
- Create/update/delete shifts
- View reservations
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import logging

from app.api.routes.dashboard import (
    CurrentUser,
    require_operator,
    require_manager,
    DashboardUser,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shifts", tags=["dashboard-shifts"])


# Response Models
class ShiftSummary(BaseModel):
    id: str
    hospital: str
    hospital_id: str
    especialidade: str
    especialidade_id: str
    data: str
    hora_inicio: str
    hora_fim: str
    valor: int
    status: str
    reservas_count: int = 0
    created_at: datetime


class ShiftDetail(BaseModel):
    id: str
    hospital: str
    hospital_id: str
    especialidade: str
    especialidade_id: str
    setor: Optional[str] = None
    setor_id: Optional[str] = None
    data: str
    hora_inicio: str
    hora_fim: str
    valor: int
    status: str
    cliente_id: Optional[str] = None
    cliente_nome: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginatedShiftsResponse(BaseModel):
    data: List[ShiftSummary]
    total: int
    page: int
    per_page: int
    pages: int


class ShiftCreate(BaseModel):
    hospital_id: str
    especialidade_id: str
    setor_id: Optional[str] = None
    data: str
    hora_inicio: str
    hora_fim: str
    valor: int
    status: str = "aberta"


class ShiftUpdate(BaseModel):
    hospital_id: Optional[str] = None
    especialidade_id: Optional[str] = None
    setor_id: Optional[str] = None
    data: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    valor: Optional[int] = None
    status: Optional[str] = None


class HospitalOption(BaseModel):
    id: str
    nome: str


class EspecialidadeOption(BaseModel):
    id: str
    nome: str


@router.get("", response_model=PaginatedShiftsResponse)
async def list_shifts(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    hospital_id: Optional[str] = None,
    especialidade_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista vagas com filtros e paginacao."""

    try:
        # Build query with joins
        query = supabase.table("vagas").select(
            "*, hospitais(nome), especialidades(nome)"
        )

        if status:
            query = query.eq("status", status)
        if hospital_id:
            query = query.eq("hospital_id", hospital_id)
        if especialidade_id:
            query = query.eq("especialidade_id", especialidade_id)
        if date_from:
            query = query.gte("data", date_from)
        if date_to:
            query = query.lte("data", date_to)

        # Execute
        result = query.order("data", desc=True).execute()
        filtered_data = result.data

        # Search filter (post-query)
        if search:
            search_lower = search.lower()
            filtered_data = [
                v for v in filtered_data
                if (v.get("hospitais", {}).get("nome", "").lower().find(search_lower) >= 0 or
                    v.get("especialidades", {}).get("nome", "").lower().find(search_lower) >= 0)
            ]

        total = len(filtered_data)

        # Paginate
        offset = (page - 1) * per_page
        paginated_data = filtered_data[offset:offset + per_page]

        # Map to response
        shifts = []
        for vaga in paginated_data:
            hospital = vaga.get("hospitais") or {}
            especialidade = vaga.get("especialidades") or {}

            shifts.append(ShiftSummary(
                id=vaga["id"],
                hospital=hospital.get("nome", "Desconhecido"),
                hospital_id=vaga.get("hospital_id", ""),
                especialidade=especialidade.get("nome", "Desconhecida"),
                especialidade_id=vaga.get("especialidade_id", ""),
                data=str(vaga.get("data", "")),
                hora_inicio=str(vaga.get("hora_inicio", ""))[:5],
                hora_fim=str(vaga.get("hora_fim", ""))[:5],
                valor=vaga.get("valor", 0),
                status=vaga.get("status", "aberta"),
                reservas_count=1 if vaga.get("cliente_id") else 0,
                created_at=vaga["created_at"]
            ))

        return PaginatedShiftsResponse(
            data=shifts,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if total > 0 else 1
        )

    except Exception as e:
        logger.error(f"Erro ao listar vagas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/hospitals", response_model=List[HospitalOption])
async def list_hospitals(user: CurrentUser):
    """Lista hospitais para select."""
    try:
        result = supabase.table("hospitais").select("id, nome").order("nome").execute()
        return [HospitalOption(id=h["id"], nome=h["nome"]) for h in result.data]
    except Exception as e:
        logger.error(f"Erro ao listar hospitais: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/especialidades", response_model=List[EspecialidadeOption])
async def list_especialidades(user: CurrentUser):
    """Lista especialidades para select."""
    try:
        result = supabase.table("especialidades").select("id, nome").order("nome").execute()
        return [EspecialidadeOption(id=e["id"], nome=e["nome"]) for e in result.data]
    except Exception as e:
        logger.error(f"Erro ao listar especialidades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{shift_id}", response_model=ShiftDetail)
async def get_shift(shift_id: str, user: CurrentUser):
    """Detalhes de uma vaga."""

    try:
        result = supabase.table("vagas").select(
            "*, hospitais(nome), especialidades(nome), setores(nome), clientes(primeiro_nome, sobrenome)"
        ).eq("id", shift_id).single().execute()

        if not result.data:
            raise HTTPException(404, "Vaga nao encontrada")

        vaga = result.data
        hospital = vaga.get("hospitais") or {}
        especialidade = vaga.get("especialidades") or {}
        setor = vaga.get("setores") or {}
        cliente = vaga.get("clientes") or {}

        cliente_nome = None
        if cliente:
            primeiro = cliente.get("primeiro_nome", "")
            sobrenome = cliente.get("sobrenome", "")
            cliente_nome = f"{primeiro} {sobrenome}".strip() or None

        return ShiftDetail(
            id=vaga["id"],
            hospital=hospital.get("nome", "Desconhecido"),
            hospital_id=vaga.get("hospital_id", ""),
            especialidade=especialidade.get("nome", "Desconhecida"),
            especialidade_id=vaga.get("especialidade_id", ""),
            setor=setor.get("nome"),
            setor_id=vaga.get("setor_id"),
            data=str(vaga.get("data", "")),
            hora_inicio=str(vaga.get("hora_inicio", ""))[:5],
            hora_fim=str(vaga.get("hora_fim", ""))[:5],
            valor=vaga.get("valor", 0),
            status=vaga.get("status", "aberta"),
            cliente_id=vaga.get("cliente_id"),
            cliente_nome=cliente_nome,
            created_at=vaga["created_at"],
            updated_at=vaga.get("updated_at")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar vaga {shift_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ShiftDetail)
async def create_shift(
    data: ShiftCreate,
    user: DashboardUser = Depends(require_operator)
):
    """Cria nova vaga."""

    try:
        insert_data = {
            "hospital_id": data.hospital_id,
            "especialidade_id": data.especialidade_id,
            "data": data.data,
            "hora_inicio": data.hora_inicio,
            "hora_fim": data.hora_fim,
            "valor": data.valor,
            "status": data.status,
            "created_at": datetime.now().isoformat()
        }

        if data.setor_id:
            insert_data["setor_id"] = data.setor_id

        result = supabase.table("vagas").insert(insert_data).execute()

        if not result.data:
            raise HTTPException(500, "Erro ao criar vaga")

        vaga_id = result.data[0]["id"]

        # Log
        supabase.table("audit_logs").insert({
            "action": "create_shift",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {"shift_id": vaga_id},
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Vaga {vaga_id} criada por {user.email}")

        # Return full details
        return await get_shift(vaga_id, user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar vaga: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{shift_id}", response_model=ShiftDetail)
async def update_shift(
    shift_id: str,
    data: ShiftUpdate,
    user: DashboardUser = Depends(require_operator)
):
    """Atualiza vaga."""

    try:
        # Verify exists
        existing = supabase.table("vagas").select("id").eq("id", shift_id).execute()
        if not existing.data:
            raise HTTPException(404, "Vaga nao encontrada")

        # Build update dict
        update_data = {"updated_at": datetime.now().isoformat()}
        if data.hospital_id is not None:
            update_data["hospital_id"] = data.hospital_id
        if data.especialidade_id is not None:
            update_data["especialidade_id"] = data.especialidade_id
        if data.setor_id is not None:
            update_data["setor_id"] = data.setor_id
        if data.data is not None:
            update_data["data"] = data.data
        if data.hora_inicio is not None:
            update_data["hora_inicio"] = data.hora_inicio
        if data.hora_fim is not None:
            update_data["hora_fim"] = data.hora_fim
        if data.valor is not None:
            update_data["valor"] = data.valor
        if data.status is not None:
            update_data["status"] = data.status

        supabase.table("vagas").update(update_data).eq("id", shift_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "update_shift",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {"shift_id": shift_id, "changes": update_data},
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Vaga {shift_id} atualizada por {user.email}")

        return await get_shift(shift_id, user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar vaga {shift_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{shift_id}")
async def delete_shift(
    shift_id: str,
    user: DashboardUser = Depends(require_manager)
):
    """Remove vaga (apenas managers)."""

    try:
        # Verify exists
        existing = supabase.table("vagas").select("id, status").eq("id", shift_id).execute()
        if not existing.data:
            raise HTTPException(404, "Vaga nao encontrada")

        # Don't delete confirmed shifts
        if existing.data[0].get("status") == "confirmada":
            raise HTTPException(400, "Nao e possivel excluir vaga confirmada")

        supabase.table("vagas").delete().eq("id", shift_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "delete_shift",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {"shift_id": shift_id},
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Vaga {shift_id} excluida por {user.email}")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao excluir vaga {shift_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
