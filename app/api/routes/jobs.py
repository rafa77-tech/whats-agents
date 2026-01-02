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
async def job_processar_grupos(batch_size: int = 50, max_workers: int = 20):
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


@router.post("/verificar-alertas-grupos")
async def job_verificar_alertas_grupos():
    """
    Job para verificar alertas do pipeline de grupos.

    Verifica:
    - Fila travada (muitos erros)
    - Taxa de conversão baixa
    - Custo acima do orçamento
    - Itens pendentes antigos
    - Taxa de duplicação alta
    """
    try:
        from app.services.grupos.alertas import executar_verificacao_alertas_grupos
        alertas = await executar_verificacao_alertas_grupos()
        return JSONResponse({
            "status": "ok",
            "message": f"{len(alertas)} alerta(s) encontrado(s)",
            "alertas": alertas
        })
    except Exception as e:
        logger.error(f"Erro ao verificar alertas de grupos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/consolidar-metricas-grupos")
async def job_consolidar_metricas_grupos():
    """
    Job para consolidar métricas do pipeline de grupos.

    Consolida métricas do dia anterior para a tabela agregada.
    Executar diariamente (recomendado: 1h da manhã).
    """
    try:
        from app.services.grupos.metricas import consolidar_metricas_dia, coletor_metricas

        # Primeiro, flush das métricas pendentes
        await coletor_metricas.flush()

        # Depois, consolidar dia anterior
        sucesso = await consolidar_metricas_dia()

        return JSONResponse({
            "status": "ok" if sucesso else "error",
            "message": "Métricas consolidadas" if sucesso else "Erro na consolidação"
        })
    except Exception as e:
        logger.error(f"Erro ao consolidar métricas de grupos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Jobs de Confirmação de Plantão (Sprint 17)
# =============================================================================

@router.post("/processar-confirmacao-plantao")
async def job_processar_confirmacao_plantao(buffer_horas: int = 2):
    """
    Job horário para transicionar vagas vencidas.

    Regra: reservada -> pendente_confirmacao quando fim_plantao <= now() - buffer

    Args:
        buffer_horas: Horas após fim do plantão para considerar vencido (default: 2)
    """
    try:
        from app.services.confirmacao_plantao import processar_vagas_vencidas

        resultado = await processar_vagas_vencidas(buffer_horas=buffer_horas)

        return JSONResponse({
            "status": "ok",
            "processadas": resultado["processadas"],
            "erros": resultado["erros"],
            "vagas": resultado["vagas"]
        })
    except Exception as e:
        logger.error(f"Erro ao processar confirmação de plantão: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/backfill-confirmacao-plantao")
async def job_backfill_confirmacao_plantao():
    """
    Job único para backfill de vagas reservadas antigas.

    Move vagas reservadas vencidas para pendente_confirmacao com source='backfill'.
    """
    try:
        from app.services.confirmacao_plantao import processar_vagas_vencidas

        resultado = await processar_vagas_vencidas(buffer_horas=2, is_backfill=True)

        return JSONResponse({
            "status": "ok",
            "message": f"Backfill concluído: {resultado['processadas']} vagas transicionadas",
            "processadas": resultado["processadas"],
            "erros": resultado["erros"]
        })
    except Exception as e:
        logger.error(f"Erro no backfill: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/pendentes-confirmacao")
async def listar_pendentes_confirmacao():
    """
    Lista vagas aguardando confirmação.

    Retorna vagas em pendente_confirmacao para exibição/ação.
    """
    try:
        from app.services.confirmacao_plantao import listar_pendentes_confirmacao

        vagas = await listar_pendentes_confirmacao()

        return JSONResponse({
            "status": "ok",
            "total": len(vagas),
            "vagas": [
                {
                    "id": v.id,
                    "data": v.data,
                    "horario": f"{v.hora_inicio} - {v.hora_fim}",
                    "valor": v.valor,
                    "hospital": v.hospital_nome,
                    "especialidade": v.especialidade_nome,
                    "medico": v.cliente_nome,
                    "telefone": v.cliente_telefone
                }
                for v in vagas
            ]
        })
    except Exception as e:
        logger.error(f"Erro ao listar pendentes: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/confirmar-plantao/{vaga_id}")
async def confirmar_plantao(vaga_id: str, realizado: bool, confirmado_por: str = "api"):
    """
    Confirma status de um plantão.

    Args:
        vaga_id: UUID da vaga
        realizado: True = realizado, False = não ocorreu
        confirmado_por: Identificador de quem confirmou
    """
    try:
        from app.services.confirmacao_plantao import (
            confirmar_plantao_realizado,
            confirmar_plantao_nao_ocorreu
        )

        if realizado:
            resultado = await confirmar_plantao_realizado(vaga_id, confirmado_por)
        else:
            resultado = await confirmar_plantao_nao_ocorreu(vaga_id, confirmado_por)

        if resultado.sucesso:
            return JSONResponse({
                "status": "ok",
                "vaga_id": vaga_id,
                "novo_status": resultado.status_novo,
                "confirmado_por": confirmado_por
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": resultado.erro
            }, status_code=400)
    except Exception as e:
        logger.error(f"Erro ao confirmar plantão {vaga_id}: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# TEMPLATES DE CAMPANHA
# =============================================================================


@router.post("/sync-templates")
async def job_sync_templates():
    """
    Sincroniza templates de campanha do Google Drive.

    Busca a pasta configurada em GOOGLE_TEMPLATES_FOLDER_ID,
    procura subpastas para cada tipo de campanha (Discovery, Oferta, etc),
    e sincroniza o arquivo mais recente de cada pasta para o banco.
    """
    try:
        from app.services.campaign_templates import sincronizar_templates

        resultado = await sincronizar_templates()
        return JSONResponse(resultado)
    except Exception as e:
        logger.error(f"Erro ao sincronizar templates: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/setup-templates")
async def job_setup_templates(parent_folder_id: str):
    """
    Cria estrutura de pastas e templates iniciais no Google Drive.

    Args:
        parent_folder_id: ID da pasta onde criar a estrutura (ex: pasta de Briefings)

    Estrutura criada:
        Templates/
        ├── Discovery/
        │   └── discovery_2025-01-01
        ├── Oferta/
        │   └── oferta_2025-01-01
        ├── Reativacao/
        │   └── reativacao_2025-01-01
        ├── Followup/
        │   └── followup_2025-01-01
        └── Feedback/
            └── feedback_2025-01-01
    """
    import os
    from datetime import datetime
    from app.services.google_docs import criar_pasta, criar_documento, listar_subpastas

    try:
        # Verificar se ja existe pasta Templates
        subpastas = await listar_subpastas(parent_folder_id)
        templates_folder = next((p for p in subpastas if p['name'] == 'Templates'), None)

        if templates_folder:
            templates_id = templates_folder['id']
            logger.info(f"Pasta Templates ja existe: {templates_id}")
        else:
            # Criar pasta principal Templates
            templates_id = await criar_pasta("Templates", parent_folder_id)
            if not templates_id:
                return JSONResponse({
                    "status": "error",
                    "message": "Falha ao criar pasta Templates"
                }, status_code=500)

        # Estrutura de templates
        templates_config = [
            ("Discovery", "discovery"),
            ("Oferta", "oferta"),
            ("Reativacao", "reativacao"),
            ("Followup", "followup"),
            ("Feedback", "feedback"),
        ]

        data_hoje = datetime.now().strftime("%Y-%m-%d")
        resultado = {"pastas": [], "documentos": [], "templates_folder_id": templates_id}

        # Verificar subpastas existentes
        subpastas_templates = await listar_subpastas(templates_id)
        subpastas_existentes = {p['name']: p['id'] for p in subpastas_templates}

        for pasta_nome, template_tipo in templates_config:
            # Criar subpasta se nao existe
            if pasta_nome in subpastas_existentes:
                pasta_id = subpastas_existentes[pasta_nome]
                logger.info(f"Subpasta {pasta_nome} ja existe: {pasta_id}")
            else:
                pasta_id = await criar_pasta(pasta_nome, templates_id)
                if pasta_id:
                    resultado["pastas"].append({"nome": pasta_nome, "id": pasta_id})

            if not pasta_id:
                continue

            # Ler template do arquivo local
            template_path = f"docs/templates/{template_tipo}_2025-01-01.md"
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    conteudo = f.read()

                # Criar documento
                doc_nome = f"{template_tipo}_{data_hoje}"
                doc_id = await criar_documento(doc_nome, conteudo, pasta_id)
                if doc_id:
                    resultado["documentos"].append({
                        "nome": doc_nome,
                        "id": doc_id,
                        "tipo": template_tipo
                    })

        return JSONResponse({
            "status": "ok",
            "message": f"Estrutura criada com {len(resultado['pastas'])} pastas e {len(resultado['documentos'])} documentos",
            **resultado
        })

    except Exception as e:
        logger.error(f"Erro ao criar estrutura de templates: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Jobs de External Handoff (Sprint 20)
# =============================================================================


@router.post("/processar-handoffs")
async def job_processar_handoffs():
    """
    Job para processar handoffs pendentes (follow-up e expiracao).

    Executa a cada 10 minutos:
    - Envia follow-ups (2h, 24h, 36h)
    - Expira handoffs vencidos (48h)
    - Libera vagas expiradas
    - Notifica medicos

    Sprint 20 - E07.
    """
    try:
        from app.workers.handoff_processor import processar_handoffs_pendentes

        stats = await processar_handoffs_pendentes()

        return JSONResponse({
            "status": "ok",
            "message": f"Processados {stats['total_processados']} handoffs",
            **stats
        })
    except Exception as e:
        logger.error(f"Erro ao processar handoffs: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/processar-retomadas")
async def job_processar_retomadas():
    """
    Job para processar mensagens fora do horario pendentes.

    Executa as 08:00 de dias uteis.
    Retoma conversas com contexto preservado.

    Sprint 22 - Responsividade Inteligente.
    """
    try:
        from app.workers.retomada_fora_horario import processar_retomadas

        stats = await processar_retomadas()

        return JSONResponse({
            "status": "ok",
            "message": f"Processadas {stats.get('processadas', 0)} retomadas",
            **stats
        })
    except Exception as e:
        logger.error(f"Erro ao processar retomadas: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Jobs de Reconciliação de Touches (Sprint 24 P1)
# =============================================================================


@router.post("/reconcile-touches")
async def job_reconcile_touches(horas: int = 72, limite: int = 1000):
    """
    Job de reconciliação de doctor_state.last_touch_*.

    Sprint 24 P1: Repair loop para consistência.

    Corrige inconsistências causadas por falhas no _finalizar_envio(),
    garantindo que last_touch_* reflita o estado real dos envios.

    Características:
    - 100% determinístico (usa provider_message_id como chave)
    - Idempotente (log com PK em provider_message_id)
    - Monotônico (só avança, nunca retrocede)
    - Usa enviada_em como touch_at real (não created_at)

    Args:
        horas: Janela de busca em horas (default 72h)
        limite: Máximo de registros por execução (default 1000)

    Executar:
    - A cada 10-15 minutos (frequência recomendada)
    - Manualmente via Slack quando necessário
    """
    try:
        from app.services.touch_reconciliation import executar_reconciliacao

        result = await executar_reconciliacao(horas=horas, limite=limite)

        return JSONResponse({
            "status": "ok",
            "message": result.summary,
            "stats": {
                "total_candidates": result.total_candidates,
                "reconciled": result.reconciled,
                "skipped_already_processed": result.skipped_already_processed,
                "skipped_already_newer": result.skipped_already_newer,
                "skipped_no_change": result.skipped_no_change,
                "failed": result.failed,
            },
            "errors": result.errors[:10] if result.errors else [],
        })
    except Exception as e:
        logger.error(f"Erro na reconciliação de touches: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/limpar-logs-reconciliacao")
async def job_limpar_logs_reconciliacao(dias: int = 30):
    """
    Job para limpar logs antigos de reconciliação.

    Mantém logs dos últimos N dias para auditoria.

    Args:
        dias: Manter logs dos últimos X dias (default 30)
    """
    try:
        from app.services.touch_reconciliation import limpar_logs_antigos

        removidos = await limpar_logs_antigos(dias=dias)

        return JSONResponse({
            "status": "ok",
            "message": f"{removidos} log(s) removido(s)",
            "removidos": removidos,
        })
    except Exception as e:
        logger.error(f"Erro ao limpar logs de reconciliação: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/reclamar-processing-travado")
async def job_reclamar_processing_travado(minutos_timeout: int = 15):
    """
    P1.2: Reclama entries travadas em status='processing'.

    Se um worker crashar entre claim e atualização final,
    a entry fica em 'processing' eternamente. Este job
    marca essas entries como 'abandoned'.

    Args:
        minutos_timeout: Minutos após os quais 'processing' é considerado travado (default 15)
    """
    try:
        from app.services.touch_reconciliation import reclamar_processing_travado

        result = await reclamar_processing_travado(minutos_timeout=minutos_timeout)

        return JSONResponse({
            "status": "ok",
            "message": f"found={result.found}, reclaimed={result.reclaimed}",
            "stats": {
                "found": result.found,
                "reclaimed": result.reclaimed,
            },
            "errors": result.errors[:10] if result.errors else [],
        })
    except Exception as e:
        logger.error(f"Erro ao reclamar processing travado: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/reconciliacao-status")
async def job_reconciliacao_status(minutos_timeout: int = 15):
    """
    Retorna status de saúde do job de reconciliação.

    Útil para monitoramento/alertas.

    Returns:
        - processing_stuck: Entries travadas em 'processing'
    """
    try:
        from app.services.touch_reconciliation import contar_processing_stuck

        stuck_count = await contar_processing_stuck(minutos_timeout=minutos_timeout)

        status = "healthy" if stuck_count == 0 else "warning" if stuck_count < 10 else "critical"

        return JSONResponse({
            "status": status,
            "processing_stuck": stuck_count,
            "timeout_minutes": minutos_timeout,
        })
    except Exception as e:
        logger.error(f"Erro ao verificar status de reconciliação: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
