"""
API Routes para gerenciamento de templates Meta.

Sprint 66 — CRUD de templates com approval workflow.
Protegido por X-API-Key header (JWT_SECRET_KEY).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.meta.template_service import template_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta/templates", tags=["meta-templates"])


# --- Auth dependency ---


async def _verificar_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    """
    Verifica X-API-Key header contra JWT_SECRET_KEY.

    Raises:
        HTTPException 401 se chave inválida ou ausente
    """
    expected = settings.JWT_SECRET_KEY
    if not expected:
        raise HTTPException(500, "API key não configurada no servidor")
    if x_api_key != expected:
        raise HTTPException(401, "API key inválida")
    return x_api_key


# --- Request models (sem access_token — buscado do banco via waba_id) ---


class CreateTemplateRequest(BaseModel):
    """Request para criar template."""

    waba_id: str
    name: str
    category: str  # MARKETING, UTILITY, AUTHENTICATION
    language: str = "pt_BR"
    components: list
    variable_mapping: Optional[dict] = None
    campanha_tipo: Optional[str] = None


class UpdateTemplateRequest(BaseModel):
    """Request para atualizar template."""

    waba_id: str
    components: list


class DeleteTemplateRequest(BaseModel):
    """Request para deletar template."""

    waba_id: str


class CreateRichTemplateRequest(BaseModel):
    """Request para criar template com mídia."""

    waba_id: str
    name: str
    category: str  # MARKETING, UTILITY
    language: str = "pt_BR"
    body_text: str
    body_variables: Optional[list] = None
    header_format: str = "IMAGE"  # IMAGE, VIDEO, DOCUMENT
    header_media_url: Optional[str] = None
    buttons: Optional[list] = None


class SendOtpRequest(BaseModel):
    """Request para enviar OTP."""

    telefone: str
    plantao_id: str
    template_name: str = "confirmacao_otp"


class VerifyOtpRequest(BaseModel):
    """Request para verificar OTP."""

    telefone: str
    codigo: str


class SyncTemplatesRequest(BaseModel):
    """Request para sincronizar templates."""

    waba_id: str


# --- Routes ---


@router.post("", dependencies=[Depends(_verificar_api_key)])
async def criar_template(req: CreateTemplateRequest):
    """Cria e submete template para aprovação Meta."""
    if req.category not in ("MARKETING", "UTILITY", "AUTHENTICATION"):
        raise HTTPException(400, "category deve ser MARKETING, UTILITY ou AUTHENTICATION")

    result = await template_service.criar_template(
        waba_id=req.waba_id,
        name=req.name,
        category=req.category,
        language=req.language,
        components=req.components,
        variable_mapping=req.variable_mapping,
        campanha_tipo=req.campanha_tipo,
    )
    return result


@router.get("", dependencies=[Depends(_verificar_api_key)])
async def listar_templates(
    waba_id: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
):
    """Lista templates do banco local."""
    templates = await template_service.listar_templates(waba_id=waba_id, status=status)
    if category:
        templates = [t for t in templates if t.get("category") == category]
    return {"templates": templates, "total": len(templates)}


@router.get("/{name}", dependencies=[Depends(_verificar_api_key)])
async def buscar_template(name: str, waba_id: Optional[str] = None):
    """Busca template por nome."""
    if waba_id:
        template = await template_service.buscar_template(waba_id, name)
    else:
        template = await template_service.buscar_template_por_nome(name)

    if not template:
        raise HTTPException(404, f"Template '{name}' não encontrado")
    return template


@router.put("/{name}", dependencies=[Depends(_verificar_api_key)])
async def atualizar_template(name: str, req: UpdateTemplateRequest):
    """Atualiza template (resubmete para aprovação)."""
    result = await template_service.atualizar_template(
        waba_id=req.waba_id,
        template_name=name,
        components=req.components,
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao atualizar"))
    return result


@router.delete("/{name}", dependencies=[Depends(_verificar_api_key)])
async def deletar_template(name: str, req: DeleteTemplateRequest):
    """Deleta template da Meta e do banco local."""
    result = await template_service.deletar_template(
        waba_id=req.waba_id,
        template_name=name,
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao deletar"))
    return result


@router.post("/rich", dependencies=[Depends(_verificar_api_key)])
async def criar_template_com_media(req: CreateRichTemplateRequest):
    """Cria template com header de mídia (imagem/vídeo/documento)."""
    if req.header_format not in ("IMAGE", "VIDEO", "DOCUMENT"):
        raise HTTPException(400, "header_format deve ser IMAGE, VIDEO ou DOCUMENT")

    result = await template_service.criar_template_com_media(
        waba_id=req.waba_id,
        name=req.name,
        category=req.category,
        language=req.language,
        body_text=req.body_text,
        body_variables=req.body_variables,
        header_format=req.header_format,
        header_media_url=req.header_media_url,
        buttons=req.buttons,
    )
    return result


@router.post("/otp/send", dependencies=[Depends(_verificar_api_key)])
async def enviar_otp(req: SendOtpRequest):
    """Envia código OTP para confirmação de plantão."""
    from app.services.meta.otp_confirmation import otp_confirmation

    result = await otp_confirmation.enviar_confirmacao_plantao(
        telefone=req.telefone,
        plantao_id=req.plantao_id,
        template_name=req.template_name,
    )
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Erro ao enviar OTP"))
    return result


@router.post("/otp/verify", dependencies=[Depends(_verificar_api_key)])
async def verificar_otp(req: VerifyOtpRequest):
    """Verifica código OTP."""
    from app.services.meta.otp_confirmation import otp_confirmation

    result = await otp_confirmation.verificar_codigo_otp(
        telefone=req.telefone,
        codigo=req.codigo,
    )
    return result


@router.post("/sync", dependencies=[Depends(_verificar_api_key)])
async def sincronizar_templates(req: SyncTemplatesRequest):
    """Sincroniza templates da Meta para o banco local."""
    result = await template_service.sincronizar_templates(
        waba_id=req.waba_id,
    )
    return result
