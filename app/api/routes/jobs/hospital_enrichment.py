"""
Job de enriquecimento de hospitais com CNES + Google Places.

Sprint 61 - Épico 4.
"""

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/enriquecimento-hospitais")
@job_endpoint("enriquecimento-hospitais")
async def job_enriquecer_hospitais():
    """
    Enriquece hospitais existentes com dados CNES e Google Places.

    Job one-shot — executar manualmente quando necessário.
    """
    from app.services.grupos.hospital_enrichment import enriquecer_hospitais_batch

    resultado = await enriquecer_hospitais_batch()

    return {
        "status": "ok",
        "message": (
            f"CNES: {resultado.enriquecidos_cnes}, "
            f"Google: {resultado.enriquecidos_google}, "
            f"Sem match: {resultado.sem_match}"
        ),
        "processados": resultado.total,
        "enriquecidos_cnes": resultado.enriquecidos_cnes,
        "enriquecidos_google": resultado.enriquecidos_google,
        "sem_match": resultado.sem_match,
        "erros": resultado.erros,
    }
