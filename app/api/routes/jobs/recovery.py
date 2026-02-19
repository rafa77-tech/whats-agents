"""
Job de recuperação de vagas incompletas.

Sprint 63 - Épico D: Envia DMs pedindo campos faltantes.
"""

from fastapi import APIRouter

from ._helpers import job_endpoint

router = APIRouter()


@router.post("/recovery-vagas-incompletas")
@job_endpoint("recovery-vagas-incompletas")
async def job_recovery_vagas_incompletas():
    from app.services.grupos.recovery_agent import executar_recovery

    stats = await executar_recovery(limite=20)
    return {
        "status": "ok",
        "processados": stats["vagas_encontradas"],
        "dms_enviados": stats["dms_enviados"],
        "sem_telefone": stats["sem_telefone"],
        "erros": stats["erros"],
    }
