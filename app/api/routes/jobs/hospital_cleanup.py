"""
Job de limpeza de hospitais.

Sprint 60 - Épico 6C: Cleanup semanal automático.
"""

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/limpeza-hospitais")
@job_endpoint("limpeza-hospitais")
async def job_limpeza_hospitais():
    """
    Limpeza automática de hospitais Tier 1.

    Deleta hospitais sem referências (zero FKs) cujos nomes
    falham no validador (blocklist, fragmentos, etc).

    Schedule: 0 4 * * 0 (domingo às 4h)
    """
    from app.services.grupos.hospital_cleanup import executar_limpeza_tier1

    resultado = await executar_limpeza_tier1(limite=200)

    return {
        "status": "ok",
        "message": f"Limpeza: {resultado['deletados']} deletados de {resultado['candidatos']} candidatos",
        "processados": resultado["deletados"],
        **resultado,
    }
