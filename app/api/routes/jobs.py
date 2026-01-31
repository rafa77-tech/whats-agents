"""
Endpoints para jobs e tarefas agendadas.

Sprint 10 - S10.E3.1: Logica de negocio extraida para app/services/jobs/
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging

from datetime import datetime, timezone
from app.core.timezone import agora_brasilia, agora_utc
from app.services.supabase import supabase
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


@router.post("/heartbeat")
async def job_heartbeat():
    """
    Job de heartbeat para monitoramento de status da Julia.

    Insere um registro com status='online' na tabela julia_status.
    O dashboard verifica se o último heartbeat foi há menos de 5 minutos
    para determinar se a Julia está online.

    Schedule: * * * * * (a cada minuto)
    """
    try:
        supabase.table("julia_status").insert({
            "status": "ativo",
            "motivo": "Heartbeat automático",
            "alterado_por": "scheduler",
            "alterado_via": "sistema",
            "created_at": agora_utc().isoformat()
        }).execute()

        return JSONResponse({
            "status": "ok",
            "message": "Heartbeat registrado"
        })
    except Exception as e:
        logger.error(f"Erro ao registrar heartbeat: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


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
    """Job para atualizar prompt com feedback do gestor.

    Extrai exemplos bons e ruins das avaliações do gestor
    e salva na tabela 'prompts' para uso pelo sistema.
    """
    try:
        resultado = await atualizar_prompt_com_feedback()
        return JSONResponse({
            "status": "ok",
            "message": "Exemplos de feedback atualizados no banco",
            "exemplos_bons": resultado.get("exemplos_bons", 0),
            "exemplos_ruins": resultado.get("exemplos_ruins", 0),
        })
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


@router.post("/backfill-fila-grupos")
async def job_backfill_fila_grupos(limite: int = 1000):
    """
    Job para enfileirar mensagens pendentes que não foram enfileiradas.

    Corrige o problema do upsert com constraint parcial que não funcionava.
    Enfileira mensagens com status='pendente' que não estão na fila.

    Args:
        limite: Máximo de mensagens a enfileirar por execução
    """
    try:
        from app.services.supabase import supabase
        from app.services.grupos.fila import enfileirar_mensagem
        from uuid import UUID

        # Buscar mensagens pendentes que NÃO estão na fila
        result = supabase.rpc("buscar_mensagens_pendentes_sem_fila", {
            "p_limite": limite
        }).execute()

        if not result.data:
            return JSONResponse({
                "status": "ok",
                "message": "Nenhuma mensagem pendente para enfileirar",
                "enfileiradas": 0
            })

        enfileiradas = 0
        erros = 0

        for row in result.data:
            try:
                mensagem_id = UUID(row["id"])
                item_id = await enfileirar_mensagem(mensagem_id)
                if item_id:
                    enfileiradas += 1
            except Exception as e:
                logger.warning(f"Erro ao enfileirar {row['id']}: {e}")
                erros += 1

        return JSONResponse({
            "status": "ok",
            "message": f"{enfileiradas} mensagem(ns) enfileirada(s), {erros} erro(s)",
            "enfileiradas": enfileiradas,
            "erros": erros
        })

    except Exception as e:
        logger.error(f"Erro no backfill de fila de grupos: {e}")
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
        from app.services.campaign_behaviors import sincronizar_behaviors as sincronizar_templates

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

        data_hoje = agora_brasilia().strftime("%Y-%m-%d")
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


# =============================================================================
# Jobs de Validação de Telefones (Sprint 32 E04)
# =============================================================================


@router.post("/validar-telefones")
async def job_validar_telefones(limite: int = 50):
    """
    Job para validar telefones via checkNumberStatus.

    Valida números pendentes usando Evolution API para verificar
    se o WhatsApp existe no número antes de tentar contato.

    Sprint 32 E04 - Validação prévia evita desperdício de mensagens.

    Args:
        limite: Máximo de telefones a processar por execução (default: 50)

    Schedule:
        A cada 5 minutos, das 8h às 20h (*/5 8-19 * * *)

    Rate:
        50 números/5min = 600/hora = ~14k/dia
    """
    try:
        # Verificar horário comercial (horário de Brasília)
        hora_atual = agora_brasilia().hour
        if hora_atual < 8 or hora_atual >= 20:
            return JSONResponse({
                "status": "skipped",
                "reason": "fora_horario",
                "message": "Validação só ocorre das 8h às 20h"
            })

        from app.services.validacao_telefone import processar_lote_validacao

        stats = await processar_lote_validacao(limit=limite)

        return JSONResponse({
            "status": "ok",
            "processados": stats["processados"],
            "validados": stats["validados"],
            "invalidos": stats["invalidos"],
            "erros": stats["erros"],
            "skips": stats["skips"],
        })
    except Exception as e:
        logger.error(f"Erro ao validar telefones: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/resetar-telefones-travados")
async def job_resetar_telefones_travados(horas: int = 1):
    """
    Reseta telefones travados em status 'validando'.

    Útil quando o processo é interrompido e deixa registros
    em estado intermediário.

    Args:
        horas: Considerar travado se em 'validando' há mais de X horas
    """
    try:
        from app.services.validacao_telefone import resetar_telefones_travados

        resetados = await resetar_telefones_travados(horas=horas)

        return JSONResponse({
            "status": "ok",
            "message": f"{resetados} telefone(s) resetado(s)",
            "resetados": resetados,
        })
    except Exception as e:
        logger.error(f"Erro ao resetar telefones travados: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# =============================================================================
# Jobs de Gatilhos Automáticos Julia (Sprint 32 E05-E07)
# =============================================================================


@router.post("/executar-gatilhos-autonomos")
async def job_executar_gatilhos_autonomos():
    """
    Job para executar todos os gatilhos automáticos da Julia.

    Gatilhos incluídos:
    - Discovery: Médicos não-enriquecidos
    - Oferta: Vagas urgentes (< 20 dias)
    - Reativação: Médicos inativos (> 60 dias)
    - Feedback: Plantões realizados recentemente

    IMPORTANTE: Só executa se PILOT_MODE=False.

    Sprint 32 E05 - Gatilhos Automáticos.

    Schedule sugerido:
        - Discovery: 0 9,14 * * 1-5 (9h e 14h, seg-sex)
        - Oferta: 0 * * * * (a cada hora)
        - Reativação: 0 10 * * 1 (segundas às 10h)
        - Feedback: 0 11 * * * (diário às 11h)
    """
    try:
        from app.services.gatilhos_autonomos import executar_todos_gatilhos

        resultados = await executar_todos_gatilhos()

        if resultados.get("pilot_mode"):
            return JSONResponse({
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - gatilhos não executados"
            })

        return JSONResponse({
            "status": "ok",
            "discovery": resultados.get("discovery", {}),
            "oferta": resultados.get("oferta", {}),
            "reativacao": resultados.get("reativacao", {}),
            "feedback": resultados.get("feedback", {}),
        })
    except Exception as e:
        logger.error(f"Erro ao executar gatilhos autônomos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/executar-discovery-autonomo")
async def job_executar_discovery_autonomo():
    """
    Job específico para Discovery automático.

    Busca médicos não-enriquecidos (sem especialidade) e
    enfileira mensagens de Discovery para conhecê-los.

    Só executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    try:
        from app.services.gatilhos_autonomos import executar_discovery_automatico

        resultado = await executar_discovery_automatico()

        if resultado is None:
            return JSONResponse({
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - discovery não executado"
            })

        return JSONResponse({
            "status": "ok",
            **resultado
        })
    except Exception as e:
        logger.error(f"Erro no discovery autônomo: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/executar-oferta-autonoma")
async def job_executar_oferta_autonoma():
    """
    Job específico para Oferta automática (furo de escala).

    Busca vagas com menos de 20 dias até a data e sem médico
    confirmado. Seleciona médicos compatíveis e enfileira ofertas.

    Só executa se PILOT_MODE=False.

    Sprint 32 E05/E06.
    """
    try:
        from app.services.gatilhos_autonomos import executar_oferta_automatica

        resultado = await executar_oferta_automatica()

        if resultado is None:
            return JSONResponse({
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - oferta não executada"
            })

        return JSONResponse({
            "status": "ok",
            **resultado
        })
    except Exception as e:
        logger.error(f"Erro na oferta autônoma: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/executar-reativacao-autonoma")
async def job_executar_reativacao_autonoma():
    """
    Job específico para Reativação automática.

    Busca médicos inativos há mais de 60 dias e enfileira
    mensagens de reativação para retomar contato.

    Só executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    try:
        from app.services.gatilhos_autonomos import executar_reativacao_automatica

        resultado = await executar_reativacao_automatica()

        if resultado is None:
            return JSONResponse({
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - reativação não executada"
            })

        return JSONResponse({
            "status": "ok",
            **resultado
        })
    except Exception as e:
        logger.error(f"Erro na reativação autônoma: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/executar-feedback-autonomo")
async def job_executar_feedback_autonomo():
    """
    Job específico para Feedback automático.

    Busca plantões realizados nos últimos 2 dias e enfileira
    solicitações de feedback para os médicos.

    Só executa se PILOT_MODE=False.

    Sprint 32 E05.
    """
    try:
        from app.services.gatilhos_autonomos import executar_feedback_automatico

        resultado = await executar_feedback_automatico()

        if resultado is None:
            return JSONResponse({
                "status": "skipped",
                "reason": "pilot_mode",
                "message": "Modo piloto ativo - feedback não executado"
            })

        return JSONResponse({
            "status": "ok",
            **resultado
        })
    except Exception as e:
        logger.error(f"Erro no feedback autônomo: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/estatisticas-gatilhos")
async def job_estatisticas_gatilhos():
    """
    Retorna estatísticas atuais dos gatilhos automáticos.

    Útil para dashboard e monitoramento.

    Sprint 32 E05.
    """
    try:
        from app.services.gatilhos_autonomos import obter_estatisticas_gatilhos
        from app.workers.pilot_mode import is_pilot_mode

        stats = await obter_estatisticas_gatilhos()

        return JSONResponse({
            "status": "ok",
            "pilot_mode": is_pilot_mode(),
            "gatilhos": stats,
        })
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de gatilhos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de Trust Score (Sprint 36)
# ==========================================


@router.post("/atualizar-trust-scores")
async def job_atualizar_trust_scores():
    """
    Job para recalcular Trust Score de todos os chips ativos.

    O Trust Score é calculado dinamicamente baseado em:
    - Idade do chip (dias desde criação)
    - Taxa de resposta (mensagens recebidas / enviadas)
    - Taxa de delivery (mensagens entregues com sucesso)
    - Erros recentes (falhas nas últimas 24h)
    - Conversas bidirecionais (interações reais)
    - Dias sem incidente (estabilidade)

    Schedule: */15 * * * * (a cada 15 minutos)

    Sprint 36 - Descoberta: job nunca foi adicionado ao scheduler,
    resultando em trust scores fixos desde a criação dos chips.
    """
    try:
        from app.services.warmer.trust_score import calcular_trust_score

        # Buscar chips ativos
        chips = supabase.table("chips").select("id, telefone").in_(
            "status", ["active", "warming", "ready"]
        ).execute()

        if not chips.data:
            return JSONResponse({
                "status": "ok",
                "message": "Nenhum chip ativo para atualizar",
                "atualizados": 0,
                "erros": 0
            })

        atualizados = 0
        erros = 0
        detalhes = []

        for chip in chips.data:
            try:
                result = await calcular_trust_score(chip["id"])
                atualizados += 1
                detalhes.append({
                    "telefone": chip["telefone"][-4:],  # últimos 4 dígitos
                    "score": result["score"],
                    "nivel": result["nivel"],
                })
            except Exception as e:
                logger.error(f"Erro ao atualizar trust score de {chip['id']}: {e}")
                erros += 1

        # Log resumido
        logger.info(
            f"[TrustScore] Atualização concluída: {atualizados} chips, {erros} erros"
        )

        return JSONResponse({
            "status": "ok",
            "message": f"{atualizados} chip(s) atualizado(s), {erros} erro(s)",
            "atualizados": atualizados,
            "erros": erros,
            "detalhes": detalhes[:10],  # Limitar para não sobrecarregar resposta
        })
    except Exception as e:
        logger.error(f"Erro ao atualizar trust scores: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de sincronização de Chips (Sprint 25)
# ==========================================

@router.post("/sincronizar-chips")
async def job_sincronizar_chips():
    """
    Job para sincronizar chips com Evolution API.

    Sprint 25: Funcionalidade base
    Sprint 36 T11.2: Adicionado alerta de muitas instâncias desconectadas

    Atualiza a tabela chips com o estado atual das instâncias na Evolution API.
    - Atualiza status de conexão de chips existentes
    - Cria novos chips para instâncias desconhecidas
    - Marca chips sem instância como desconectados
    - Alerta se > 30% das instâncias estão desconectadas (Sprint 36)

    Schedule: */5 * * * * (a cada 5 minutos)
    """
    try:
        from app.services.chips import sincronizar_chips_com_evolution

        resultado = await sincronizar_chips_com_evolution()

        # Sprint 36 T11.2: Alertar se muitas instâncias desconectadas
        total = resultado.get("chips_conectados", 0) + resultado.get("chips_desconectados", 0)
        desconectadas = resultado.get("chips_desconectados", 0)

        if total > 0 and desconectadas > total * 0.3:
            from app.services.slack import enviar_mensagem_slack

            await enviar_mensagem_slack(
                canal="alertas",
                texto=(
                    f":rotating_light: *Alerta de Conexão Evolution*\n"
                    f"{desconectadas}/{total} instâncias desconectadas ({desconectadas/total*100:.0f}%)\n"
                    f"Verificar: Evolution API e QR codes dos chips"
                ),
            )
            logger.warning(
                f"[SyncChips] ALERTA: {desconectadas}/{total} instâncias desconectadas"
            )

        return JSONResponse({
            "status": "ok",
            "instancias_evolution": resultado["instancias_evolution"],
            "chips_atualizados": resultado["chips_atualizados"],
            "chips_criados": resultado["chips_criados"],
            "chips_conectados": resultado["chips_conectados"],
            "chips_desconectados": resultado["chips_desconectados"],
            "erros": resultado["erros"],
        })
    except Exception as e:
        logger.error(f"Erro ao sincronizar chips: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de Monitoramento de Fila (Sprint 36)
# ==========================================


@router.post("/monitorar-fila")
async def job_monitorar_fila(
    limite_pendentes: int = 50,
    limite_idade_minutos: int = 30,
):
    """
    Sprint 36 - T01.5: Monitora saúde da fila de mensagens.

    Verifica:
    - Quantidade de mensagens pendentes
    - Idade da mensagem mais antiga
    - Erros nas últimas 24h

    Alerta via Slack se:
    - Mais de `limite_pendentes` mensagens pendentes
    - Mensagem mais antiga há mais de `limite_idade_minutos` minutos

    Args:
        limite_pendentes: Máximo de mensagens pendentes (default: 50)
        limite_idade_minutos: Minutos máx da mensagem mais antiga (default: 30)

    Schedule: */10 * * * * (a cada 10 minutos)
    """
    try:
        from app.services.fila import fila_service
        from app.services.slack import enviar_mensagem_slack

        metricas = await fila_service.obter_metricas_fila()

        pendentes = metricas["pendentes"]
        idade = metricas["mensagem_mais_antiga_min"]
        erros_24h = metricas["erros_ultimas_24h"]

        alertas = []

        # Verificar fila acumulando
        if pendentes > limite_pendentes:
            alertas.append(
                f":warning: Fila com {pendentes} mensagens pendentes "
                f"(limite: {limite_pendentes})"
            )

        # Verificar mensagens travadas
        if idade and idade > limite_idade_minutos:
            alertas.append(
                f":hourglass: Mensagem mais antiga há {idade:.0f} minutos "
                f"(limite: {limite_idade_minutos})"
            )

        # Verificar muitos erros
        if erros_24h > 20:
            alertas.append(
                f":x: {erros_24h} erros nas últimas 24h"
            )

        # Enviar alerta se houver problemas
        if alertas:
            await enviar_mensagem_slack(
                canal="alertas",
                texto=(
                    f":rotating_light: *Alerta de Fila de Mensagens*\n\n"
                    + "\n".join(alertas)
                    + f"\n\nMétricas:\n"
                    f"- Pendentes: {pendentes}\n"
                    f"- Processando: {metricas['processando']}\n"
                    f"- Idade mais antiga: {idade:.0f if idade else 0} min\n"
                    f"- Erros 24h: {erros_24h}\n\n"
                    f"Ação: Verificar fila_worker e circuit breaker"
                ),
            )
            logger.warning(f"[MonitorFila] Alertas: {alertas}")

        status = "warning" if alertas else "ok"

        return JSONResponse({
            "status": status,
            "pendentes": pendentes,
            "processando": metricas["processando"],
            "mensagem_mais_antiga_min": idade,
            "erros_24h": erros_24h,
            "alertas": alertas,
        })
    except Exception as e:
        logger.error(f"Erro ao monitorar fila: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# ==========================================
# Jobs de Snapshot de Chips (Sprint 41)
# ==========================================


@router.post("/snapshot-chips-diario")
async def job_snapshot_chips_diario():
    """
    Job para criar snapshots diários das métricas de chips.

    Captura o estado dos contadores de cada chip antes do reset diário.
    Deve ser executado às 23:55 (antes do reset às 00:05).

    Sprint 41 - Rastreamento de Chips e Status de Entrega.

    Schedule: 55 23 * * * (23:55 todos os dias)
    """
    try:
        # Usar RPC para criar snapshots de todos os chips
        result = supabase.rpc("chip_criar_snapshots_todos").execute()

        if not result.data:
            return JSONResponse({
                "status": "error",
                "message": "RPC retornou vazio"
            }, status_code=500)

        row = result.data[0] if isinstance(result.data, list) else result.data

        logger.info(
            f"[SnapshotChips] Concluído: {row.get('snapshots_criados', 0)} criados, "
            f"{row.get('snapshots_existentes', 0)} existentes, {row.get('erros', 0)} erros"
        )

        return JSONResponse({
            "status": "ok",
            "total_chips": row.get("total_chips", 0),
            "snapshots_criados": row.get("snapshots_criados", 0),
            "snapshots_existentes": row.get("snapshots_existentes", 0),
            "erros": row.get("erros", 0),
        })
    except Exception as e:
        logger.error(f"Erro ao criar snapshots de chips: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/resetar-contadores-chips")
async def job_resetar_contadores_chips():
    """
    Job para resetar contadores diários dos chips.

    Reseta msgs_enviadas_hoje e msgs_recebidas_hoje para 0.
    Deve ser executado às 00:05 (após o snapshot às 23:55).

    Sprint 41 - Rastreamento de Chips e Status de Entrega.

    Schedule: 5 0 * * * (00:05 todos os dias)
    """
    try:
        # Usar RPC para resetar contadores
        result = supabase.rpc("chip_resetar_contadores_diarios").execute()

        if not result.data:
            return JSONResponse({
                "status": "error",
                "message": "RPC retornou vazio"
            }, status_code=500)

        row = result.data[0] if isinstance(result.data, list) else result.data
        chips_resetados = row.get("chips_resetados", 0)

        logger.info(f"[ResetChips] {chips_resetados} chips resetados")

        return JSONResponse({
            "status": "ok",
            "chips_resetados": chips_resetados,
        })
    except Exception as e:
        logger.error(f"Erro ao resetar contadores de chips: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/fila-worker-health")
async def job_fila_worker_health():
    """
    Sprint 36 - T01.6: Health check do fila_worker.

    Verifica:
    - Status do circuit breaker
    - Se há mensagens sendo processadas (não travadas)
    - Métricas gerais da fila

    Retorna status:
    - healthy: Tudo funcionando
    - warning: Problemas detectados mas operacional
    - critical: Worker possivelmente parado/travado

    Útil para monitoramento externo e dashboards.
    """
    try:
        from app.services.fila import fila_service
        from app.services.circuit_breaker import circuit_evolution, CircuitState

        metricas = await fila_service.obter_metricas_fila()

        pendentes = metricas["pendentes"]
        processando = metricas["processando"]
        idade = metricas["mensagem_mais_antiga_min"]
        erros_24h = metricas["erros_ultimas_24h"]

        # Status do circuit breaker
        circuit_status = circuit_evolution.status()
        circuit_estado = circuit_status["estado"]

        # Determinar status geral
        issues = []

        # Circuit breaker aberto é crítico
        if circuit_estado == "open":
            issues.append("circuit_breaker_open")

        # Mensagem muito antiga indica worker travado
        if idade and idade > 60:
            issues.append("message_stuck_60min")

        # Muitos erros é preocupante
        if erros_24h > 50:
            issues.append("high_error_rate")

        # Muitas mensagens acumulando
        if pendentes > 100:
            issues.append("queue_backlog")

        # Determinar status final
        if "circuit_breaker_open" in issues or "message_stuck_60min" in issues:
            status = "critical"
        elif issues:
            status = "warning"
        else:
            status = "healthy"

        return JSONResponse({
            "status": status,
            "circuit_breaker": {
                "estado": circuit_estado,
                "falhas_consecutivas": circuit_status["falhas_consecutivas"],
                "ultima_falha": circuit_status["ultima_falha"],
            },
            "fila": {
                "pendentes": pendentes,
                "processando": processando,
                "mensagem_mais_antiga_min": round(idade, 1) if idade else None,
                "erros_24h": erros_24h,
            },
            "issues": issues,
        })
    except Exception as e:
        logger.error(f"Erro no health check do fila_worker: {e}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "issues": ["health_check_failed"],
        }, status_code=500)
