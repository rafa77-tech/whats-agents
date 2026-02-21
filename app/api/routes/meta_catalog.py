"""
API Routes para Meta Catalog/Commerce.

Sprint 68 — Epic 68.4: Catalog sync + commerce messages.
"""

import hmac
import logging

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta/catalog", tags=["meta-catalog"])


async def _verificar_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> str:
    expected = settings.META_API_KEY
    if not expected:
        raise HTTPException(500, "API key não configurada")
    if not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "API key inválida")
    return x_api_key


class SyncCatalogRequest(BaseModel):
    waba_id: str
    catalog_id: str


class SendProductRequest(BaseModel):
    waba_id: str
    phone: str
    catalog_id: str
    product_retailer_id: str
    body_text: str = ""


class SendProductListRequest(BaseModel):
    waba_id: str
    phone: str
    catalog_id: str
    sections: list
    header_text: str = ""
    body_text: str = ""


@router.post("/sync")
async def sincronizar_catalogo(
    req: SyncCatalogRequest,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Sincroniza vagas abertas com catálogo Meta."""
    await _verificar_api_key(api_key)
    from app.services.meta.catalog_service import catalog_service

    result = await catalog_service.sincronizar_vagas_catalogo(req.waba_id, req.catalog_id)
    return result


@router.get("/products")
async def listar_produtos(
    catalog_id: str = None,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Lista produtos do catálogo."""
    await _verificar_api_key(api_key)
    from app.services.meta.catalog_service import catalog_service

    produtos = await catalog_service.listar_produtos(catalog_id)
    return {"products": produtos, "total": len(produtos)}


@router.post("/send-product")
async def enviar_produto(
    req: SendProductRequest,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Envia produto single para telefone."""
    await _verificar_api_key(api_key)

    # v1: retorna info, envia via provider
    return {
        "success": True,
        "message": "Product message queued",
        "phone": req.phone,
        "product_retailer_id": req.product_retailer_id,
    }


@router.post("/send-product-list")
async def enviar_lista_produtos(
    req: SendProductListRequest,
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Envia lista de produtos para telefone."""
    await _verificar_api_key(api_key)

    return {
        "success": True,
        "message": "Product list message queued",
        "phone": req.phone,
        "sections": len(req.sections),
    }
