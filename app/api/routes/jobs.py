"""
Endpoints para jobs e tarefas agendadas.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from app.services.fila_mensagens import processar_mensagens_agendadas
from app.services.fila import fila_service
from app.services.qualidade import avaliar_conversas_pendentes
from app.services.alertas import executar_verificacao_alertas
from app.services.relatorio import gerar_relatorio_diario, enviar_relatorio_slack
from app.services.feedback import atualizar_prompt_com_feedback
from app.services.followup import followup_service
from app.services.monitor_whatsapp import executar_verificacao_whatsapp

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)


class PrimeiraMensagemRequest(BaseModel):
    telefone: str


@router.post("/primeira-mensagem")
async def job_primeira_mensagem(request: PrimeiraMensagemRequest):
    """
    Envia primeira mensagem de prospecção para um médico.

    Usado para testes manuais (CT-01).

    Args:
        telefone: Telefone do médico (ex: 5511999999999)
    """
    from app.services.supabase import supabase
    from app.services.agente import gerar_resposta_julia, enviar_resposta
    from app.services.contexto import montar_contexto_completo
    from app.services.interacao import salvar_interacao
    from app.services.optout import verificar_opted_out
    from datetime import datetime

    try:
        # 1. Buscar cliente pelo telefone
        cliente_resp = (
            supabase.table("clientes")
            .select("*")
            .eq("telefone", request.telefone)
            .execute()
        )

        if not cliente_resp.data:
            # Cliente nao existe - criar novo
            logger.info(f"Cliente nao encontrado, criando novo: {request.telefone}")
            novo_cliente = (
                supabase.table("clientes")
                .insert({
                    "telefone": request.telefone,
                    "primeiro_nome": "Doutor(a)",  # Nome generico ate descobrir
                    "status": "novo",
                    "origem": "slack_comando",
                    "stage_jornada": "novo"
                })
                .execute()
            )
            cliente = novo_cliente.data[0]
            logger.info(f"Novo cliente criado: {cliente['id']}")
        else:
            cliente = cliente_resp.data[0]
            logger.info(f"Cliente encontrado: {cliente.get('primeiro_nome', 'N/A')} ({cliente['id']})")

        # 1.1 Verificar opt-out
        if await verificar_opted_out(cliente["id"]):
            logger.info(f"🛑 Cliente {cliente['id']} fez opt-out, não enviando mensagem")
            return JSONResponse({
                "status": "blocked",
                "message": "Cliente fez opt-out, mensagem não enviada",
                "cliente": cliente["primeiro_nome"],
                "opted_out": True
            })

        # 2. Criar ou buscar conversa ativa
        conversa_resp = (
            supabase.table("conversations")
            .select("*")
            .eq("cliente_id", cliente["id"])
            .eq("status", "active")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if conversa_resp.data:
            conversa = conversa_resp.data[0]
            logger.info(f"Conversa existente: {conversa['id']}")
        else:
            # Criar nova conversa
            nova_conversa = (
                supabase.table("conversations")
                .insert({
                    "cliente_id": cliente["id"],
                    "status": "active",
                    "controlled_by": "ai",
                    "stage": "novo"
                })
                .execute()
            )
            conversa = nova_conversa.data[0]
            logger.info(f"Nova conversa criada: {conversa['id']}")

        # 3. Montar contexto (vai detectar primeira_msg automaticamente)
        contexto = await montar_contexto_completo(cliente, conversa)

        # 4. Gerar primeira mensagem
        # Para primeira mensagem, usamos prompt especial sem mensagem de entrada
        resposta = await gerar_resposta_julia(
            mensagem="[INICIO_PROSPECCAO]",  # Trigger especial
            contexto=contexto,
            medico=cliente,
            conversa=conversa,
            incluir_historico=False,
            usar_tools=False  # Primeira msg não usa tools
        )

        logger.info(f"Resposta gerada: {resposta[:100]}...")

        # 5. Enviar via WhatsApp
        resultado_envio = await enviar_resposta(request.telefone, resposta)

        # 5.1 Sincronizar IDs com Chatwoot (após envio, Chatwoot cria contato/conversa)
        # Aguardar um pouco para Chatwoot processar
        import asyncio
        await asyncio.sleep(2)  # Dar tempo pro Chatwoot processar

        from app.services.chatwoot import sincronizar_ids_chatwoot
        try:
            ids_chatwoot = await sincronizar_ids_chatwoot(cliente["id"], request.telefone)
            logger.info(f"IDs Chatwoot sincronizados: {ids_chatwoot}")
        except Exception as e:
            logger.warning(f"Erro ao sincronizar Chatwoot (nao critico): {e}")

        # 6. Salvar interação no banco
        await salvar_interacao(
            conversa_id=conversa["id"],
            cliente_id=cliente["id"],
            tipo="saida",
            conteudo=resposta,
            autor_tipo="julia"
        )

        # 7. Atualizar cliente
        supabase.table("clientes").update({
            "ultima_mensagem_data": datetime.utcnow().isoformat(),
            "ultima_mensagem_tipo": "outbound",
            "stage_jornada": "prospectado"
        }).eq("id", cliente["id"]).execute()

        return JSONResponse({
            "status": "ok",
            "message": "Primeira mensagem enviada",
            "cliente": cliente["primeiro_nome"],
            "conversa_id": conversa["id"],
            "resposta": resposta,
            "envio": resultado_envio
        })

    except Exception as e:
        logger.error(f"Erro ao enviar primeira mensagem: {e}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


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


@router.post("/report-periodo")
async def job_report_periodo(tipo: str = "manha"):
    """
    Gera e envia report do periodo.

    Periodos: manha (10h), almoco (13h), tarde (17h), fim_dia (20h)

    Executar via cron:
    0 10 * * * curl -X POST "http://localhost:8000/jobs/report-periodo?tipo=manha"
    """
    try:
        from app.services.relatorio import gerar_report_periodo, enviar_report_periodo_slack
        report = await gerar_report_periodo(tipo)
        await enviar_report_periodo_slack(report)
        return JSONResponse({
            "status": "ok",
            "periodo": tipo,
            "metricas": report["metricas"]
        })
    except Exception as e:
        logger.error(f"Erro ao gerar report {tipo}: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/report-semanal")
async def job_report_semanal():
    """
    Gera e envia report semanal.

    Executar via cron segunda as 9h:
    0 9 * * 1 curl -X POST http://localhost:8000/jobs/report-semanal
    """
    try:
        from app.services.relatorio import gerar_report_semanal, enviar_report_semanal_slack
        report = await gerar_report_semanal()
        await enviar_report_semanal_slack(report)
        return JSONResponse({
            "status": "ok",
            "semana": report["semana"],
            "metricas": report["metricas"]
        })
    except Exception as e:
        logger.error(f"Erro ao gerar report semanal: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/processar-followups")
async def job_processar_followups():
    """
    Job diario para processar follow-ups pendentes.

    Usa a nova implementacao com stages (48h -> 5d -> 15d).

    Executar via cron as 10h:
    0 10 * * * curl -X POST http://localhost:8000/jobs/processar-followups
    """
    try:
        from app.services.followup import processar_followups_pendentes
        stats = await processar_followups_pendentes()
        return JSONResponse({
            "status": "ok",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Erro ao processar follow-ups: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/processar-pausas-expiradas")
async def job_processar_pausas_expiradas():
    """
    Job diario para reativar conversas pausadas.

    Conversas em 'nao_respondeu' com pausa > 60 dias voltam para 'recontato'.

    Executar via cron as 6h:
    0 6 * * * curl -X POST http://localhost:8000/jobs/processar-pausas-expiradas
    """
    try:
        from app.services.followup import processar_pausas_expiradas
        stats = await processar_pausas_expiradas()
        return JSONResponse({
            "status": "ok",
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Erro ao processar pausas expiradas: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/sincronizar-briefing")
async def job_sincronizar_briefing():
    """
    Job para sincronizar briefing do Google Docs.

    Verifica se o documento mudou e atualiza diretrizes no banco.

    Executar via cron a cada hora:
    0 * * * * curl -X POST http://localhost:8000/jobs/sincronizar-briefing
    """
    try:
        from app.services.briefing import sincronizar_briefing
        result = await sincronizar_briefing()
        return JSONResponse({
            "status": "ok",
            "result": result
        })
    except Exception as e:
        logger.error(f"Erro ao sincronizar briefing: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/followup-diario")
async def job_followup_diario():
    """
    Job diario de follow-up (LEGADO).

    Mantido para compatibilidade. Usa a implementacao antiga.

    Executar via cron as 10h:
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


@router.post("/verificar-whatsapp")
async def job_verificar_whatsapp():
    """
    Job para verificar conexao WhatsApp e detectar erros de criptografia.

    - Verifica se a instancia esta conectada
    - Analisa logs para erros de PreKeyError (criptografia)
    - Envia alerta Slack se detectar problemas
    - Reinicia Evolution API automaticamente se necessario

    Executar via cron a cada minuto:
    * * * * * curl -X POST http://localhost:8000/jobs/verificar-whatsapp
    """
    try:
        resultado = await executar_verificacao_whatsapp()
        return JSONResponse({
            "status": "ok",
            "verificacao": resultado
        })
    except Exception as e:
        logger.error(f"Erro ao verificar WhatsApp: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )


@router.post("/processar-fila-mensagens")
async def job_processar_fila_mensagens(limite: int = 20):
    """
    Job para processar fila de mensagens (follow-ups, lembretes, etc).

    Processa mensagens pendentes na tabela fila_mensagens:
    - Verifica opt-out antes de enviar
    - Envia via WhatsApp com simulacao de digitacao
    - Marca como enviada ou registra erro

    Executar via cron a cada minuto:
    * * * * * curl -X POST http://localhost:8000/jobs/processar-fila-mensagens
    """
    from app.services.whatsapp import enviar_com_digitacao
    from app.services.interacao import salvar_interacao
    from app.services.supabase import supabase

    stats = {
        "processadas": 0,
        "enviadas": 0,
        "bloqueadas_optout": 0,
        "erros": 0
    }

    try:
        for _ in range(limite):
            # Obter proxima mensagem da fila
            mensagem = await fila_service.obter_proxima()
            if not mensagem:
                break

            stats["processadas"] += 1
            cliente = mensagem.get("clientes", {})
            telefone = cliente.get("telefone")
            cliente_id = mensagem.get("cliente_id")

            if not telefone:
                logger.warning(f"Telefone nao encontrado para mensagem {mensagem['id']}")
                await fila_service.marcar_erro(mensagem["id"], "Telefone nao encontrado")
                stats["erros"] += 1
                continue

            # Verificar opt-out
            cliente_resp = (
                supabase.table("clientes")
                .select("opted_out")
                .eq("id", cliente_id)
                .single()
                .execute()
            )

            if cliente_resp.data and cliente_resp.data.get("opted_out"):
                logger.info(f"Cliente {cliente_id} fez opt-out, cancelando mensagem {mensagem['id']}")
                supabase.table("fila_mensagens").update({
                    "status": "cancelada",
                    "erro": "Cliente fez opt-out"
                }).eq("id", mensagem["id"]).execute()
                stats["bloqueadas_optout"] += 1
                continue

            # Enviar mensagem
            try:
                await enviar_com_digitacao(
                    telefone=telefone,
                    texto=mensagem["conteudo"]
                )

                # Marcar como enviada
                await fila_service.marcar_enviada(mensagem["id"])

                # Salvar interacao
                if mensagem.get("conversa_id"):
                    await salvar_interacao(
                        conversa_id=mensagem["conversa_id"],
                        cliente_id=cliente_id,
                        tipo="saida",
                        conteudo=mensagem["conteudo"],
                        autor_tipo="julia"
                    )

                logger.info(f"Mensagem {mensagem['id']} enviada para {telefone}")
                stats["enviadas"] += 1

            except Exception as e:
                logger.error(f"Erro ao enviar mensagem {mensagem['id']}: {e}")
                await fila_service.marcar_erro(mensagem["id"], str(e))
                stats["erros"] += 1

        return JSONResponse({
            "status": "ok",
            "stats": stats
        })

    except Exception as e:
        logger.error(f"Erro ao processar fila de mensagens: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e), "stats": stats},
            status_code=500
        )

