"""
Endpoints para jobs e tarefas agendadas.

Sprint 10 - S10.E3.1: Logica de negocio extraida para app/services/jobs/
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from app.services.fila_mensagens import processar_mensagens_agendadas
from app.services.qualidade import avaliar_conversas_pendentes
from app.services.alertas import executar_verificacao_alertas
from app.services.relatorio import gerar_relatorio_diario, enviar_relatorio_slack
from app.services.feedback import atualizar_prompt_com_feedback
from app.services.followup import followup_service
from app.services.monitor_whatsapp import executar_verificacao_whatsapp

# Novos services refatorados
from app.services.jobs import (
    enviar_primeira_mensagem,
    processar_fila,
    processar_campanhas_agendadas,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)


class PrimeiraMensagemRequest(BaseModel):
    telefone: str


@router.post("/primeira-mensagem")
async def job_primeira_mensagem(request: PrimeiraMensagemRequest):
    """Envia primeira mensagem de prospecao para um medico."""
    resultado = await enviar_primeira_mensagem(request.telefone)

    if resultado.opted_out:
        return JSONResponse({
            "status": "blocked",
            "message": resultado.erro,
            "cliente": resultado.cliente_nome,
            "opted_out": True
        })

    if not resultado.sucesso:
        return JSONResponse(
            {"status": "error", "message": resultado.erro},
            status_code=500
        )

    return JSONResponse({
        "status": "ok",
        "message": "Primeira mensagem enviada",
        "cliente": resultado.cliente_nome,
        "conversa_id": resultado.conversa_id,
        "resposta": resultado.mensagem_enviada,
        "envio": resultado.resultado_envio
    })


@router.post("/processar-mensagens-agendadas")
async def job_processar_mensagens_agendadas():
    """Job para processar mensagens agendadas."""
    try:
        await processar_mensagens_agendadas()
        return JSONResponse({"status": "ok", "message": "Mensagens agendadas processadas"})
    except Exception as e:
        logger.error(f"Erro ao processar mensagens agendadas: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/avaliar-conversas-pendentes")
async def job_avaliar_conversas_pendentes():
    """Job para avaliar conversas encerradas."""
    try:
        await avaliar_conversas_pendentes(limite=50)
        return JSONResponse({"status": "ok", "message": "Conversas pendentes avaliadas"})
    except Exception as e:
        logger.error(f"Erro ao avaliar conversas pendentes: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/verificar-alertas")
async def job_verificar_alertas():
    """Job para verificar e enviar alertas."""
    try:
        await executar_verificacao_alertas()
        return JSONResponse({"status": "ok", "message": "Alertas verificados"})
    except Exception as e:
        logger.error(f"Erro ao verificar alertas: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/relatorio-diario")
async def job_relatorio_diario():
    """Job para gerar e enviar relatorio diario."""
    try:
        relatorio = await gerar_relatorio_diario()
        await enviar_relatorio_slack(relatorio)
        return JSONResponse({"status": "ok", "message": "Relatorio diario enviado", "relatorio": relatorio})
    except Exception as e:
        logger.error(f"Erro ao enviar relatorio diario: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/atualizar-prompt-feedback")
async def job_atualizar_prompt_feedback():
    """Job para atualizar prompt com feedback do gestor."""
    try:
        await atualizar_prompt_com_feedback()
        return JSONResponse({"status": "ok", "message": "Prompt atualizado com feedback"})
    except Exception as e:
        logger.error(f"Erro ao atualizar prompt com feedback: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/processar-campanhas-agendadas")
async def job_processar_campanhas_agendadas():
    """Job para iniciar campanhas agendadas."""
    try:
        resultado = await processar_campanhas_agendadas()
        return JSONResponse({
            "status": "ok",
            "message": f"{resultado.campanhas_iniciadas} campanha(s) iniciada(s)"
        })
    except Exception as e:
        logger.error(f"Erro ao processar campanhas agendadas: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/report-periodo")
async def job_report_periodo(tipo: str = "manha"):
    """Gera e envia report do periodo."""
    try:
        from app.services.relatorio import gerar_report_periodo, enviar_report_periodo_slack
        report = await gerar_report_periodo(tipo)
        await enviar_report_periodo_slack(report)
        return JSONResponse({"status": "ok", "periodo": tipo, "metricas": report["metricas"]})
    except Exception as e:
        logger.error(f"Erro ao gerar report {tipo}: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/report-semanal")
async def job_report_semanal():
    """Gera e envia report semanal."""
    try:
        from app.services.relatorio import gerar_report_semanal, enviar_report_semanal_slack
        report = await gerar_report_semanal()
        await enviar_report_semanal_slack(report)
        return JSONResponse({"status": "ok", "semana": report["semana"], "metricas": report["metricas"]})
    except Exception as e:
        logger.error(f"Erro ao gerar report semanal: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/processar-followups")
async def job_processar_followups():
    """Job diario para processar follow-ups pendentes."""
    try:
        from app.services.followup import processar_followups_pendentes
        stats = await processar_followups_pendentes()
        return JSONResponse({"status": "ok", "stats": stats})
    except Exception as e:
        logger.error(f"Erro ao processar follow-ups: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/processar-pausas-expiradas")
async def job_processar_pausas_expiradas():
    """Job diario para reativar conversas pausadas."""
    try:
        from app.services.followup import processar_pausas_expiradas
        stats = await processar_pausas_expiradas()
        return JSONResponse({"status": "ok", "stats": stats})
    except Exception as e:
        logger.error(f"Erro ao processar pausas expiradas: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/sincronizar-briefing")
async def job_sincronizar_briefing():
    """Job para sincronizar briefing do Google Docs."""
    try:
        from app.services.briefing import sincronizar_briefing
        result = await sincronizar_briefing()
        return JSONResponse({"status": "ok", "result": result})
    except Exception as e:
        logger.error(f"Erro ao sincronizar briefing: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/followup-diario")
async def job_followup_diario():
    """Job diario de follow-up (LEGADO)."""
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
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/verificar-whatsapp")
async def job_verificar_whatsapp():
    """Job para verificar conexao WhatsApp."""
    try:
        resultado = await executar_verificacao_whatsapp()
        return JSONResponse({"status": "ok", "verificacao": resultado})
    except Exception as e:
        logger.error(f"Erro ao verificar WhatsApp: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/processar-fila-mensagens")
async def job_processar_fila_mensagens(limite: int = 20):
    """Job para processar fila de mensagens."""
    try:
        stats = await processar_fila(limite)
        return JSONResponse({
            "status": "ok",
            "stats": {
                "processadas": stats.processadas,
                "enviadas": stats.enviadas,
                "bloqueadas_optout": stats.bloqueadas_optout,
                "erros": stats.erros
            }
        })
    except Exception as e:
        logger.error(f"Erro ao processar fila de mensagens: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de manutenção do doctor_state (Sprint 15)
# ==========================================

@router.post("/doctor-state-manutencao-diaria")
async def job_doctor_state_manutencao_diaria():
    """
    Job diário de manutenção do doctor_state.

    Executa:
    - Decay de temperatura por inatividade
    - Expiração de cooling_off vencidos
    - Atualização de lifecycle stages
    """
    try:
        from app.workers.temperature_decay import run_daily_maintenance
        result = await run_daily_maintenance()
        return JSONResponse({
            "status": "ok",
            "message": "Manutenção diária concluída",
            "result": result
        })
    except Exception as e:
        logger.error(f"Erro na manutenção diária: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/doctor-state-manutencao-semanal")
async def job_doctor_state_manutencao_semanal():
    """
    Job semanal de manutenção do doctor_state.

    Executa tudo do diário + reset de contadores semanais.
    """
    try:
        from app.workers.temperature_decay import run_weekly_maintenance
        result = await run_weekly_maintenance()
        return JSONResponse({
            "status": "ok",
            "message": "Manutenção semanal concluída",
            "result": result
        })
    except Exception as e:
        logger.error(f"Erro na manutenção semanal: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/doctor-state-decay")
async def job_doctor_state_decay(batch_size: int = 100):
    """
    Job específico de decay de temperatura.

    Decai temperatura de médicos inativos.
    Idempotente: usa last_decay_at para evitar decay duplo.
    """
    try:
        from app.workers.temperature_decay import decay_all_temperatures
        decayed = await decay_all_temperatures(batch_size)
        return JSONResponse({
            "status": "ok",
            "message": f"Decay aplicado em {decayed} médicos",
            "decayed": decayed
        })
    except Exception as e:
        logger.error(f"Erro no decay de temperatura: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/doctor-state-expire-cooling")
async def job_doctor_state_expire_cooling():
    """
    Job específico para expirar cooling_off vencidos.

    Médicos com cooling_off expirado voltam para 'active'.
    """
    try:
        from app.workers.temperature_decay import expire_cooling_off
        expired = await expire_cooling_off()
        return JSONResponse({
            "status": "ok",
            "message": f"{expired} cooling_off expirado(s)",
            "expired": expired
        })
    except Exception as e:
        logger.error(f"Erro ao expirar cooling_off: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de processamento de grupos WhatsApp (Sprint 14)
# ==========================================

@router.post("/processar-grupos")
async def job_processar_grupos(batch_size: int = 50, max_workers: int = 5):
    """
    Job para processar mensagens de grupos WhatsApp.

    Processa um ciclo do pipeline:
    Pendente -> Heurística -> Classificação -> Extração -> Normalização -> Deduplicação -> Importação

    Args:
        batch_size: Quantidade de itens a processar por estágio
        max_workers: Processamentos paralelos
    """
    try:
        from app.workers.grupos_worker import processar_ciclo_grupos
        resultado = await processar_ciclo_grupos(batch_size, max_workers)
        return JSONResponse({
            "status": "ok" if resultado["sucesso"] else "error",
            "ciclo": resultado.get("ciclo", {}),
            "fila": resultado.get("fila", {})
        })
    except Exception as e:
        logger.error(f"Erro ao processar grupos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/status-grupos")
async def job_status_grupos():
    """
    Retorna status do processamento de grupos.

    Inclui estatísticas da fila e itens travados.
    """
    try:
        from app.workers.grupos_worker import obter_status_worker
        status = await obter_status_worker()
        return JSONResponse(status)
    except Exception as e:
        logger.error(f"Erro ao obter status de grupos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/limpar-grupos-finalizados")
async def job_limpar_grupos_finalizados(dias: int = 7):
    """
    Job para limpar itens finalizados antigos da fila.

    Args:
        dias: Manter itens dos últimos N dias
    """
    try:
        from app.services.grupos.fila import limpar_finalizados
        removidos = await limpar_finalizados(dias)
        return JSONResponse({
            "status": "ok",
            "message": f"{removidos} item(ns) removido(s)",
            "removidos": removidos
        })
    except Exception as e:
        logger.error(f"Erro ao limpar finalizados: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/reprocessar-grupos-erro")
async def job_reprocessar_grupos_erro(limite: int = 100):
    """
    Job para reprocessar itens com erro.

    Args:
        limite: Máximo de itens a reprocessar
    """
    try:
        from app.services.grupos.fila import reprocessar_erros
        reprocessados = await reprocessar_erros(limite)
        return JSONResponse({
            "status": "ok",
            "message": f"{reprocessados} item(ns) enviado(s) para reprocessamento",
            "reprocessados": reprocessados
        })
    except Exception as e:
        logger.error(f"Erro ao reprocessar erros: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
