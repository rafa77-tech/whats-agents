"""
Core jobs: heartbeat, mensagens, campanhas, relatorios, followups.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from app.core.timezone import agora_utc
from app.services.supabase import supabase
from app.services.fila_mensagens import processar_mensagens_agendadas
from app.services.qualidade import avaliar_conversas_pendentes
from app.services.alertas import executar_verificacao_alertas
from app.services.relatorio import gerar_relatorio_diario, enviar_relatorio_slack
from app.services.feedback import atualizar_prompt_com_feedback
from app.services.followup import followup_service
from app.services.monitor_whatsapp import executar_verificacao_whatsapp
from app.services.jobs import (
    enviar_primeira_mensagem,
    processar_fila,
    processar_campanhas_agendadas,
)

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/heartbeat")
@job_endpoint("heartbeat")
async def job_heartbeat():
    """
    Job de heartbeat para monitoramento de status da Julia.

    Insere um registro com status='online' na tabela julia_status.
    O dashboard verifica se o ultimo heartbeat foi ha menos de 5 minutos
    para determinar se a Julia esta online.

    Schedule: * * * * * (a cada minuto)
    """
    supabase.table("julia_status").insert(
        {
            "status": "ativo",
            "motivo": "Heartbeat automático",
            "alterado_por": "scheduler",
            "alterado_via": "sistema",
            "created_at": agora_utc().isoformat(),
        }
    ).execute()

    return {"status": "ok", "message": "Heartbeat registrado"}


class PrimeiraMensagemRequest(BaseModel):
    telefone: str


@router.post("/primeira-mensagem")
async def job_primeira_mensagem(request: PrimeiraMensagemRequest):
    """Envia primeira mensagem de prospecao para um medico."""
    resultado = await enviar_primeira_mensagem(request.telefone)

    if resultado.opted_out:
        return JSONResponse(
            {
                "status": "blocked",
                "message": resultado.erro,
                "cliente": resultado.cliente_nome,
                "opted_out": True,
            }
        )

    if not resultado.sucesso:
        return JSONResponse({"status": "error", "message": resultado.erro}, status_code=500)

    return JSONResponse(
        {
            "status": "ok",
            "message": "Primeira mensagem enviada",
            "cliente": resultado.cliente_nome,
            "conversa_id": resultado.conversa_id,
            "resposta": resultado.mensagem_enviada,
            "envio": resultado.resultado_envio,
        }
    )


@router.post("/processar-mensagens-agendadas")
@job_endpoint("processar-mensagens-agendadas")
async def job_processar_mensagens_agendadas():
    """Job para processar mensagens agendadas."""
    await processar_mensagens_agendadas()
    return {"status": "ok", "message": "Mensagens agendadas processadas"}


@router.post("/avaliar-conversas-pendentes")
@job_endpoint("avaliar-conversas-pendentes")
async def job_avaliar_conversas_pendentes():
    """Job para avaliar conversas encerradas."""
    await avaliar_conversas_pendentes(limite=50)
    return {"status": "ok", "message": "Conversas pendentes avaliadas"}


@router.post("/verificar-alertas")
@job_endpoint("verificar-alertas")
async def job_verificar_alertas():
    """Job para verificar e enviar alertas."""
    await executar_verificacao_alertas()
    return {"status": "ok", "message": "Alertas verificados"}


@router.post("/relatorio-diario")
@job_endpoint("relatorio-diario")
async def job_relatorio_diario():
    """Job para gerar e enviar relatorio diario."""
    relatorio = await gerar_relatorio_diario()
    await enviar_relatorio_slack(relatorio)
    return {"status": "ok", "message": "Relatorio diario enviado", "relatorio": relatorio}


@router.post("/atualizar-prompt-feedback")
@job_endpoint("atualizar-prompt-feedback")
async def job_atualizar_prompt_feedback():
    """Job para atualizar prompt com feedback do gestor.

    Extrai exemplos bons e ruins das avaliacoes do gestor
    e salva na tabela 'prompts' para uso pelo sistema.
    """
    resultado = await atualizar_prompt_com_feedback()
    return {
        "status": "ok",
        "message": "Exemplos de feedback atualizados no banco",
        "exemplos_bons": resultado.get("exemplos_bons", 0),
        "exemplos_ruins": resultado.get("exemplos_ruins", 0),
    }


@router.post("/processar-campanhas-agendadas")
@job_endpoint("processar-campanhas-agendadas")
async def job_processar_campanhas_agendadas():
    """Job para iniciar campanhas agendadas."""
    resultado = await processar_campanhas_agendadas()
    return {
        "status": "ok",
        "message": f"{resultado.campanhas_iniciadas} campanha(s) iniciada(s)",
    }


@router.post("/report-periodo")
@job_endpoint("report-periodo")
async def job_report_periodo(tipo: str = "manha"):
    """Gera e envia report do periodo."""
    from app.services.relatorio import gerar_report_periodo, enviar_report_periodo_slack

    report = await gerar_report_periodo(tipo)
    await enviar_report_periodo_slack(report)
    return {"status": "ok", "periodo": tipo, "metricas": report["metricas"]}


@router.post("/report-semanal")
@job_endpoint("report-semanal")
async def job_report_semanal():
    """Gera e envia report semanal."""
    from app.services.relatorio import gerar_report_semanal, enviar_report_semanal_slack

    report = await gerar_report_semanal()
    await enviar_report_semanal_slack(report)
    return {"status": "ok", "semana": report["semana"], "metricas": report["metricas"]}


@router.post("/processar-followups")
@job_endpoint("processar-followups")
async def job_processar_followups():
    """Job diario para processar follow-ups pendentes."""
    from app.services.followup import processar_followups_pendentes

    stats = await processar_followups_pendentes()
    return {"status": "ok", "stats": stats}


@router.post("/processar-pausas-expiradas")
@job_endpoint("processar-pausas-expiradas")
async def job_processar_pausas_expiradas():
    """Job diario para reativar conversas pausadas."""
    from app.services.followup import processar_pausas_expiradas

    stats = await processar_pausas_expiradas()
    return {"status": "ok", "stats": stats}


@router.post("/sincronizar-briefing")
@job_endpoint("sincronizar-briefing")
async def job_sincronizar_briefing():
    """Job para sincronizar briefing do Google Docs."""
    from app.services.briefing import sincronizar_briefing

    result = await sincronizar_briefing()
    return {"status": "ok", "result": result}


@router.post("/followup-diario")
@job_endpoint("followup-diario")
async def job_followup_diario():
    """Job diario de follow-up (LEGADO)."""
    pendentes = await followup_service.verificar_followups_pendentes()
    enviados = 0
    for item in pendentes:
        sucesso = await followup_service.enviar_followup(
            conversa_id=item["conversa"]["id"], tipo=item["tipo"]
        )
        if sucesso:
            enviados += 1

    return {
        "status": "ok",
        "message": f"{enviados} follow-up(s) agendado(s)",
        "pendentes": len(pendentes),
        "enviados": enviados,
    }


@router.post("/verificar-whatsapp")
@job_endpoint("verificar-whatsapp")
async def job_verificar_whatsapp():
    """Job para verificar conexao WhatsApp."""
    resultado = await executar_verificacao_whatsapp()
    return {"status": "ok", "verificacao": resultado}


@router.post("/processar-fila-mensagens")
@job_endpoint("processar-fila-mensagens")
async def job_processar_fila_mensagens(limite: int = 20):
    """Job para processar fila de mensagens."""
    stats = await processar_fila(limite)
    return {
        "status": "ok",
        "stats": {
            "processadas": stats.processadas,
            "enviadas": stats.enviadas,
            "bloqueadas_optout": stats.bloqueadas_optout,
            "erros": stats.erros,
        },
    }
