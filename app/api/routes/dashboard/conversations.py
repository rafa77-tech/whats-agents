"""
Dashboard conversations endpoints.

Provides conversation management for the dashboard:
- List conversations with filters and pagination
- Get conversation details with messages
- Trigger handoff to human
- Return conversation to Julia
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
import logging

from app.api.routes.dashboard import (
    CurrentUser,
    require_operator,
    DashboardUser,
)
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["dashboard-conversations"])


# Response Models
class ConversationSummary(BaseModel):
    id: str
    cliente_id: str
    cliente_nome: str
    cliente_telefone: str
    status: str
    controlled_by: str
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    created_at: datetime


class ConversationDetail(BaseModel):
    id: str
    cliente: dict
    messages: List[dict]
    status: str
    controlled_by: str
    handoff_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PaginatedResponse(BaseModel):
    data: List[ConversationSummary]
    total: int
    page: int
    per_page: int
    pages: int


class HandoffRequest(BaseModel):
    reason: Optional[str] = None


@router.get("", response_model=PaginatedResponse)
async def list_conversations(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    controlled_by: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista conversas com filtros e paginacao."""

    try:
        # Build query
        query = supabase.table("conversations").select(
            "*, clientes(nome, telefone)"
        )

        if status:
            query = query.eq("status", status)
        if controlled_by:
            query = query.eq("controlled_by", controlled_by)

        # Execute to get total
        count_result = query.execute()

        # Filter by search if provided (post-query filter due to Supabase limitations)
        filtered_data = count_result.data
        if search:
            search_lower = search.lower()
            filtered_data = [
                c for c in filtered_data
                if (c.get("clientes", {}).get("nome", "").lower().find(search_lower) >= 0 or
                    c.get("clientes", {}).get("telefone", "").find(search) >= 0)
            ]

        total = len(filtered_data)

        # Sort by updated_at desc
        filtered_data.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        # Paginate
        offset = (page - 1) * per_page
        paginated_data = filtered_data[offset:offset + per_page]

        # Map to response
        conversations = []
        for conv in paginated_data:
            cliente = conv.get("clientes") or {}
            conversations.append(ConversationSummary(
                id=conv["id"],
                cliente_id=conv["cliente_id"],
                cliente_nome=cliente.get("nome", "Desconhecido"),
                cliente_telefone=cliente.get("telefone", ""),
                status=conv.get("status", "unknown"),
                controlled_by=conv.get("controlled_by", "julia"),
                last_message=conv.get("last_message"),
                last_message_at=conv.get("last_message_at"),
                unread_count=conv.get("unread_count", 0),
                created_at=conv["created_at"]
            ))

        return PaginatedResponse(
            data=conversations,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page if total > 0 else 1
        )

    except Exception as e:
        logger.error(f"Erro ao listar conversas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, user: CurrentUser):
    """Detalhes de uma conversa com mensagens."""

    try:
        # Conversa
        conv_result = supabase.table("conversations").select(
            "*, clientes(*)"
        ).eq("id", conversation_id).single().execute()

        if not conv_result.data:
            raise HTTPException(404, "Conversa nao encontrada")

        conv = conv_result.data

        # Mensagens (ultimas 100)
        msgs_result = supabase.table("interacoes").select("*").eq(
            "conversa_id", conversation_id
        ).order("created_at", desc=True).limit(100).execute()

        return ConversationDetail(
            id=conv["id"],
            cliente=conv.get("clientes") or {},
            messages=list(reversed(msgs_result.data)),  # Ordem cronologica
            status=conv.get("status", "unknown"),
            controlled_by=conv.get("controlled_by", "julia"),
            handoff_reason=conv.get("handoff_reason"),
            created_at=conv["created_at"],
            updated_at=conv["updated_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar conversa {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/handoff")
async def trigger_handoff(
    conversation_id: str,
    request: HandoffRequest = None,
    user: DashboardUser = Depends(require_operator)
):
    """Forca handoff para humano."""

    reason = f"Manual via dashboard por {user.email}"
    if request and request.reason:
        reason = f"{reason}: {request.reason}"

    try:
        # Verificar se conversa existe
        existing = supabase.table("conversations").select("id").eq(
            "id", conversation_id
        ).execute()

        if not existing.data:
            raise HTTPException(404, "Conversa nao encontrada")

        result = supabase.table("conversations").update({
            "controlled_by": "human",
            "handoff_reason": reason,
            "updated_at": datetime.now().isoformat()
        }).eq("id", conversation_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "manual_handoff",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {
                "conversation_id": conversation_id,
                "reason": reason
            },
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Handoff triggered for {conversation_id} by {user.email}")

        return {"success": True, "controlled_by": "human"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer handoff da conversa {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/return-to-julia")
async def return_to_julia(
    conversation_id: str,
    user: DashboardUser = Depends(require_operator)
):
    """Retorna conversa para Julia."""

    try:
        # Verificar se conversa existe
        existing = supabase.table("conversations").select("id").eq(
            "id", conversation_id
        ).execute()

        if not existing.data:
            raise HTTPException(404, "Conversa nao encontrada")

        result = supabase.table("conversations").update({
            "controlled_by": "julia",
            "handoff_reason": None,
            "updated_at": datetime.now().isoformat()
        }).eq("id", conversation_id).execute()

        # Log
        supabase.table("audit_logs").insert({
            "action": "return_to_julia",
            "actor_email": user.email,
            "actor_role": user.role.value,
            "details": {"conversation_id": conversation_id},
            "created_at": datetime.now().isoformat()
        }).execute()

        logger.info(f"Conversation {conversation_id} returned to Julia by {user.email}")

        return {"success": True, "controlled_by": "julia"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao retornar conversa {conversation_id} para Julia: {e}")
        raise HTTPException(status_code=500, detail=str(e))
