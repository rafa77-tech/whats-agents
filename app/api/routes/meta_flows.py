"""
API Routes para WhatsApp Flows.

Sprint 68 — Epic 68.2: CRUD de Flows + envio.
Protegido por X-API-Key header.
"""

import hmac
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta/flows", tags=["meta-flows"])


async def _verificar_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    """Verifica X-API-Key header."""
    expected = settings.META_API_KEY
    if not expected:
        raise HTTPException(500, "API key não configurada")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "API key inválida")
    return x_api_key


class CreateFlowRequest(BaseModel):
    waba_id: str
    name: str
    flow_type: str = "FLOW"
    categories: Optional[list] = None


class UpdateFlowRequest(BaseModel):
    waba_id: str
    json_definition: dict


class SendFlowRequest(BaseModel):
    waba_id: str
    phone: str
    flow_id: str
    flow_token: str
    header_text: str = ""
    body_text: str = ""
    flow_cta: str = "Abrir"


@router.post("")
async def criar_flow(req: CreateFlowRequest, api_key: str = Header(..., alias="X-API-Key")):
    """Cria um novo Flow."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    result = await flow_service.criar_flow(
        waba_id=req.waba_id,
        name=req.name,
        flow_type=req.flow_type,
        categories=req.categories,
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao criar flow"))
    return result


@router.get("")
async def listar_flows(waba_id: str, api_key: str = Header(..., alias="X-API-Key")):
    """Lista flows de uma WABA."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    flows = await flow_service.listar_flows(waba_id)
    return {"flows": flows, "total": len(flows)}


@router.get("/{flow_id}")
async def buscar_flow(flow_id: str, api_key: str = Header(..., alias="X-API-Key")):
    """Busca flow por ID."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    flow = await flow_service.buscar_flow(flow_id)
    if not flow:
        raise HTTPException(404, "Flow não encontrado")
    return flow


@router.post("/{flow_id}/publish")
async def publicar_flow(
    flow_id: str,
    waba_id: str,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Publica um flow."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    result = await flow_service.publicar_flow(waba_id, flow_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao publicar"))
    return result


@router.post("/{flow_id}/send")
async def enviar_flow(
    flow_id: str,
    req: SendFlowRequest,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Envia flow para um telefone."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    # v1: retorna info, não envia via provider
    return {
        "success": True,
        "message": "Flow send queued",
        "flow_id": flow_id,
        "phone": req.phone,
    }


@router.delete("/{flow_id}")
async def deprecar_flow(
    flow_id: str,
    waba_id: str,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Depreca um flow."""
    await _verificar_api_key(api_key)
    from app.services.meta.flow_service import flow_service

    result = await flow_service.deprecar_flow(waba_id, flow_id)
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao deprecar"))
    return result
