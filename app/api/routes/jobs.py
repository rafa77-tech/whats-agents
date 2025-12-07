"""
Endpoints para jobs e tarefas agendadas.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import logging

from app.services.fila_mensagens import processar_mensagens_agendadas
from app.services.qualidade import avaliar_conversas_pendentes
from app.services.alertas import executar_verificacao_alertas
from app.services.relatorio import gerar_relatorio_diario, enviar_relatorio_slack
from app.services.feedback import atualizar_prompt_com_feedback
from app.services.followup import followup_service

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


@router.post("/avaliar-conversas-pendentes")
async def job_avaliar_conversas_pendentes():
    """
    Job para avaliar conversas encerradas que ainda não foram avaliadas.
    
    Executar via cron diariamente:
    0 2 * * * curl -X POST http://localhost:8000/jobs/avaliar-conversas-pendentes
    """
    try:
        await avaliar_conversas_pendentes(limite=50)
        return JSONResponse({
            "status": "ok",
            "message": "Conversas pendentes avaliadas"
        })
    except Exception as e:
        logger.error(f"Erro ao avaliar conversas pendentes: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/verificar-alertas")
async def job_verificar_alertas():
    """
    Job para verificar e enviar alertas.
    
    Executar via cron a cada 15 minutos:
    */15 * * * * curl -X POST http://localhost:8000/jobs/verificar-alertas
    """
    try:
        await executar_verificacao_alertas()
        return JSONResponse({
            "status": "ok",
            "message": "Alertas verificados"
        })
    except Exception as e:
        logger.error(f"Erro ao verificar alertas: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/relatorio-diario")
async def job_relatorio_diario():
    """
    Job para gerar e enviar relatório diário.
    
    Executar via cron às 8h:
    0 8 * * * curl -X POST http://localhost:8000/jobs/relatorio-diario
    """
    try:
        relatorio = await gerar_relatorio_diario()
        await enviar_relatorio_slack(relatorio)
        return JSONResponse({
            "status": "ok",
            "message": "Relatório diário enviado",
            "relatorio": relatorio
        })
    except Exception as e:
        logger.error(f"Erro ao enviar relatório diário: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/atualizar-prompt-feedback")
async def job_atualizar_prompt_feedback():
    """
    Job para atualizar prompt com feedback do gestor.
    
    Executar via cron semanalmente:
    0 2 * * 0 curl -X POST http://localhost:8000/jobs/atualizar-prompt-feedback
    """
    try:
        await atualizar_prompt_com_feedback()
        return JSONResponse({
            "status": "ok",
            "message": "Prompt atualizado com feedback"
        })
    except Exception as e:
        logger.error(f"Erro ao atualizar prompt com feedback: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/processar-campanhas-agendadas")
async def job_processar_campanhas_agendadas():
    """
    Job para iniciar campanhas agendadas.
    
    Executar via cron a cada minuto:
    * * * * * curl -X POST http://localhost:8000/jobs/processar-campanhas-agendadas
    """
    try:
        from datetime import datetime
        from app.services.supabase import supabase
        from app.services.campanha import criar_envios_campanha
        
        agora = datetime.utcnow().isoformat()
        
        # Buscar campanhas prontas
        campanhas_resp = (
            supabase.table("campanhas")
            .select("id")
            .eq("status", "agendada")
            .lte("agendar_para", agora)
            .execute()
        )
        
        campanhas = campanhas_resp.data or []
        iniciadas = 0
        
        for campanha in campanhas:
            await criar_envios_campanha(campanha["id"])
            supabase.table("campanhas").update({
                "status": "ativa",
                "iniciada_em": agora
            }).eq("id", campanha["id"]).execute()
            iniciadas += 1
        
        return JSONResponse({
            "status": "ok",
            "message": f"{iniciadas} campanha(s) iniciada(s)"
        })
    except Exception as e:
        logger.error(f"Erro ao processar campanhas agendadas: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/followup-diario")
async def job_followup_diario():
    """
    Job diário de follow-up.
    
    Executar via cron às 10h:
    0 10 * * * curl -X POST http://localhost:8000/jobs/followup-diario
    """
    try:
        pendentes = await followup_service.verificar_followups_pendentes()
        
        enviados = 0
        for item in pendentes:
            sucesso = await followup_service.enviar_followup(
                conversa_id=item["conversa"]["id"],
                tipo=item["tipo"]
            )
            if sucesso:
                enviados += 1
        
        return JSONResponse({
            "status": "ok",
            "message": f"{enviados} follow-up(s) agendado(s)",
            "pendentes": len(pendentes),
            "enviados": enviados
        })
    except Exception as e:
        logger.error(f"Erro ao processar follow-ups: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

