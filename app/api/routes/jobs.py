"""
Endpoints para jobs e tarefas agendadas.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

from app.services.fila_mensagens import processar_mensagens_agendadas

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)


@router.post("/processar-mensagens-agendadas")
async def job_processar_mensagens_agendadas():
    """
    Job para processar mensagens agendadas.
    
    Executar via cron a cada minuto:
    * * * * * curl -X POST http://localhost:8000/jobs/processar-mensagens-agendadas
    """
    try:
        await processar_mensagens_agendadas()
        return JSONResponse({
            "status": "ok",
            "message": "Mensagens agendadas processadas"
        })
    except Exception as e:
        logger.error(f"Erro ao processar mensagens agendadas: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

