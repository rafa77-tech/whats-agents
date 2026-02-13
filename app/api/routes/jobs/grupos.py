"""
Jobs de processamento de grupos WhatsApp (Sprint 14).

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/processar-grupos")
@job_endpoint("processar-grupos")
async def job_processar_grupos(batch_size: int = 50, max_workers: int = 20):
    """
    Job para processar mensagens de grupos WhatsApp.

    Processa um ciclo do pipeline:
    Pendente -> Heuristica -> Classificacao -> Extracao -> Normalizacao -> Deduplicacao -> Importacao

    Args:
        batch_size: Quantidade de itens a processar por estagio
        max_workers: Processamentos paralelos
    """
    from app.workers.grupos_worker import processar_ciclo_grupos

    resultado = await processar_ciclo_grupos(batch_size, max_workers)
    return JSONResponse(
        {
            "status": "ok" if resultado["sucesso"] else "error",
            "ciclo": resultado.get("ciclo", {}),
            "fila": resultado.get("fila", {}),
        }
    )


@router.get("/status-grupos")
@job_endpoint("status-grupos")
async def job_status_grupos():
    """
    Retorna status do processamento de grupos.

    Inclui estatisticas da fila e itens travados.
    """
    from app.workers.grupos_worker import obter_status_worker

    status = await obter_status_worker()
    return JSONResponse(status)


@router.post("/limpar-grupos-finalizados")
@job_endpoint("limpar-grupos-finalizados")
async def job_limpar_grupos_finalizados(dias: int = 7):
    """
    Job para limpar itens finalizados antigos da fila.

    Args:
        dias: Manter itens dos ultimos N dias
    """
    from app.services.grupos.fila import limpar_finalizados

    removidos = await limpar_finalizados(dias)
    return {
        "status": "ok",
        "message": f"{removidos} item(ns) removido(s)",
        "removidos": removidos,
    }


@router.post("/reprocessar-grupos-erro")
@job_endpoint("reprocessar-grupos-erro")
async def job_reprocessar_grupos_erro(limite: int = 100):
    """
    Job para reprocessar itens com erro.

    Args:
        limite: Maximo de itens a reprocessar
    """
    from app.services.grupos.fila import reprocessar_erros

    reprocessados = await reprocessar_erros(limite)
    return {
        "status": "ok",
        "message": f"{reprocessados} item(ns) enviado(s) para reprocessamento",
        "reprocessados": reprocessados,
    }


@router.post("/backfill-fila-grupos")
async def job_backfill_fila_grupos(limite: int = 1000):
    """
    Job para enfileirar mensagens pendentes que nao foram enfileiradas.

    Corrige o problema do upsert com constraint parcial que nao funcionava.
    Enfileira mensagens com status='pendente' que nao estao na fila.

    Args:
        limite: Maximo de mensagens a enfileirar por execucao
    """
    try:
        from app.services.supabase import supabase
        from app.services.grupos.fila import enfileirar_mensagem

        # Buscar mensagens pendentes que NAO estao na fila
        result = supabase.rpc("buscar_mensagens_pendentes_sem_fila", {"p_limite": limite}).execute()

        if not result.data:
            return JSONResponse(
                {
                    "status": "ok",
                    "message": "Nenhuma mensagem pendente para enfileirar",
                    "enfileiradas": 0,
                }
            )

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

        return JSONResponse(
            {
                "status": "ok",
                "message": f"{enfileiradas} mensagem(ns) enfileirada(s), {erros} erro(s)",
                "enfileiradas": enfileiradas,
                "erros": erros,
            }
        )

    except Exception as e:
        logger.error(f"Erro no backfill de fila de grupos: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/verificar-alertas-grupos")
@job_endpoint("verificar-alertas-grupos")
async def job_verificar_alertas_grupos():
    """
    Job para verificar alertas do pipeline de grupos.

    Verifica:
    - Fila travada (muitos erros)
    - Taxa de conversao baixa
    - Custo acima do orcamento
    - Itens pendentes antigos
    - Taxa de duplicacao alta
    """
    from app.services.grupos.alertas import executar_verificacao_alertas_grupos

    alertas = await executar_verificacao_alertas_grupos()
    return {
        "status": "ok",
        "message": f"{len(alertas)} alerta(s) encontrado(s)",
        "alertas": alertas,
    }


@router.post("/consolidar-metricas-grupos")
@job_endpoint("consolidar-metricas-grupos")
async def job_consolidar_metricas_grupos():
    """
    Job para consolidar metricas do pipeline de grupos.

    Consolida metricas do dia anterior para a tabela agregada.
    Executar diariamente (recomendado: 1h da manha).
    """
    from app.services.grupos.metricas import consolidar_metricas_dia, coletor_metricas

    # Primeiro, flush das metricas pendentes
    await coletor_metricas.flush()

    # Depois, consolidar dia anterior
    sucesso = await consolidar_metricas_dia()

    return JSONResponse(
        {
            "status": "ok" if sucesso else "error",
            "message": "Métricas consolidadas" if sucesso else "Erro na consolidação",
        }
    )
