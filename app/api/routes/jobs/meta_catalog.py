"""
Job de sincronização de catálogo Meta.

Sprint 68 — Epic 68.4, Chunk 12.
"""

import logging

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/meta-catalog-sync")
@job_endpoint("meta-catalog-sync")
async def job_meta_catalog_sync():
    """
    Sincroniza vagas abertas com catálogo Meta.

    Cron: 0 8 * * 1-5 (diário às 8h, seg-sex)
    """
    from app.core.config import settings
    from app.services.meta.catalog_service import catalog_service

    if not settings.META_CATALOG_SYNC_ENABLED:
        return {"status": "ok", "message": "Catalog sync desabilitado", "processados": 0}

    catalog_id = settings.META_CATALOG_ID
    if not catalog_id:
        return {"status": "ok", "message": "META_CATALOG_ID não configurado", "processados": 0}

    # Buscar primeira WABA disponível
    from app.services.supabase import supabase

    chips_resp = (
        supabase.table("chips")
        .select("meta_waba_id")
        .not_.is_("meta_waba_id", "null")
        .eq("status", "active")
        .limit(1)
        .execute()
    )

    if not chips_resp.data:
        return {"status": "ok", "message": "Nenhuma WABA ativa", "processados": 0}

    waba_id = chips_resp.data[0]["meta_waba_id"]
    resultado = await catalog_service.sincronizar_vagas_catalogo(waba_id, catalog_id)
    return {
        "status": "ok",
        "processados": resultado.get("synced", 0),
        **resultado,
    }
