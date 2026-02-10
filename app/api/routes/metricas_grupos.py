"""
Endpoints para métricas do pipeline de grupos.

Sprint 14 - E12 - Métricas e Monitoramento
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Query

from app.core.logging import get_logger
from app.services.grupos.metricas import (
    obter_metricas_dia,
    obter_metricas_periodo,
    obter_top_grupos,
    obter_status_fila,
    consolidar_metricas_dia,
    coletor_metricas,
)

router = APIRouter(prefix="/metricas/grupos", tags=["Métricas Grupos"])
logger = get_logger(__name__)


# =============================================================================
# Endpoints de Métricas
# =============================================================================


@router.get("/resumo")
async def resumo_metricas(
    dias: int = Query(default=7, ge=1, le=90, description="Quantidade de dias"),
):
    """
    Retorna resumo de métricas do pipeline de grupos.

    Inclui:
    - Total de mensagens processadas
    - Vagas importadas/revisão/duplicadas
    - Custo estimado em USD
    - Taxa de conversão
    """
    try:
        metricas = await obter_metricas_periodo(dias)

        return {
            "sucesso": True,
            "periodo": metricas.get("periodo"),
            "data_inicio": metricas.get("data_inicio"),
            "totais": metricas.get("totais", {}),
            "detalhes_diarios": metricas.get("por_dia", []),
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo de métricas: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.get("/hoje")
async def metricas_hoje():
    """
    Retorna métricas do dia atual.
    """
    try:
        metricas = await obter_metricas_dia()

        return {
            "sucesso": True,
            "data": date.today().isoformat(),
            "metricas": metricas,
        }
    except Exception as e:
        logger.error(f"Erro ao obter métricas de hoje: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.get("/top-grupos")
async def top_grupos(
    dias: int = Query(default=7, ge=1, le=90, description="Período em dias"),
    limite: int = Query(default=10, ge=1, le=50, description="Máximo de grupos"),
):
    """
    Retorna os grupos com mais vagas importadas.
    """
    try:
        grupos = await obter_top_grupos(dias=dias, limite=limite)

        return {
            "sucesso": True,
            "periodo_dias": dias,
            "grupos": grupos,
        }
    except Exception as e:
        logger.error(f"Erro ao obter top grupos: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.get("/fila")
async def status_fila():
    """
    Retorna status atual da fila de processamento.

    Inclui contagem por estágio e itens travados.
    """
    try:
        status = await obter_status_fila()

        return {
            "sucesso": True,
            "status": status,
        }
    except Exception as e:
        logger.error(f"Erro ao obter status da fila: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.get("/custos")
async def custos_periodo(dias: int = Query(default=7, ge=1, le=90, description="Período em dias")):
    """
    Retorna detalhamento de custos LLM do período.
    """
    try:
        metricas = await obter_metricas_periodo(dias)
        totais = metricas.get("totais", {})
        por_dia = metricas.get("por_dia", [])

        # Extrair custos por dia
        custos_diarios = []
        for dia in por_dia:
            custos_diarios.append(
                {
                    "data": dia.get("data"),
                    "custo_usd": float(dia.get("custo_total_usd", 0) or 0),
                    "tokens_input": dia.get("tokens_input", 0) or 0,
                    "tokens_output": dia.get("tokens_output", 0) or 0,
                    "mensagens": dia.get("mensagens_processadas", 0) or 0,
                }
            )

        # Calcular média
        total_mensagens = totais.get("mensagens", 0)
        custo_total = totais.get("custo_usd", 0)
        custo_por_mensagem = custo_total / total_mensagens if total_mensagens > 0 else 0

        return {
            "sucesso": True,
            "periodo_dias": dias,
            "custo_total_usd": custo_total,
            "total_mensagens": total_mensagens,
            "custo_medio_por_mensagem": custo_por_mensagem,
            "custos_diarios": custos_diarios,
        }
    except Exception as e:
        logger.error(f"Erro ao obter custos: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.post("/consolidar")
async def consolidar_dia(
    data: Optional[str] = Query(default=None, description="Data para consolidar (YYYY-MM-DD)"),
):
    """
    Consolida métricas de grupos para métricas de pipeline.

    Por padrão consolida o dia anterior.
    """
    try:
        data_consolidar = None
        if data:
            data_consolidar = date.fromisoformat(data)

        sucesso = await consolidar_metricas_dia(data_consolidar)

        return {
            "sucesso": sucesso,
            "data_consolidada": (data_consolidar or (date.today())).isoformat(),
        }
    except ValueError:
        return {
            "sucesso": False,
            "erro": "Formato de data inválido. Use YYYY-MM-DD",
        }
    except Exception as e:
        logger.error(f"Erro ao consolidar métricas: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }


@router.post("/flush")
async def flush_metricas():
    """
    Força flush das métricas pendentes no coletor.

    Útil para testes ou antes de parar o serviço.
    """
    try:
        count = await coletor_metricas.flush()

        return {
            "sucesso": True,
            "grupos_atualizados": count,
        }
    except Exception as e:
        logger.error(f"Erro ao fazer flush de métricas: {e}")
        return {
            "sucesso": False,
            "erro": str(e),
        }
