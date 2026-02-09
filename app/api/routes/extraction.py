"""
Endpoints para o sistema de extracao de dados.

Sprint 53: Discovery Intelligence Pipeline.
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging

from app.services.supabase import supabase
from app.services.extraction import (
    buscar_insights_conversa,
    buscar_insights_cliente,
    buscar_insights_campanha,
    gerar_relatorio_campanha,
)
from app.workers.backfill_extraction import (
    executar_backfill,
    obter_status_backfill,
)

router = APIRouter(prefix="/extraction", tags=["Extraction"])
logger = logging.getLogger(__name__)


# =============================================================================
# Schemas
# =============================================================================

class BackfillRequest(BaseModel):
    """Request para disparar backfill."""
    dias: int = 30
    campanha_id: Optional[int] = None
    dry_run: bool = False
    max_interacoes: int = 1000


class BackfillResponse(BaseModel):
    """Response do backfill."""
    status: str
    message: str
    task_id: Optional[str] = None


class InsightSummary(BaseModel):
    """Resumo de um insight."""
    id: int
    interesse: Optional[str]
    interesse_score: Optional[float]
    proximo_passo: Optional[str]
    objecao_tipo: Optional[str]
    confianca: Optional[float]
    created_at: str


class CampaignInsightsSummary(BaseModel):
    """Resumo de insights de uma campanha."""
    campaign_id: int
    campanha_nome: Optional[str]
    total_interacoes: int
    total_medicos: int
    taxa_interesse_pct: Optional[float]
    interesse_score_medio: Optional[float]
    prontos_para_vagas: int
    para_followup: int


# =============================================================================
# Endpoints - Consultas
# =============================================================================

@router.get("/insights/conversation/{conversation_id}")
async def get_insights_conversa(
    conversation_id: str,
    limit: int = Query(default=10, le=50)
):
    """
    Busca insights de uma conversa especifica.

    Args:
        conversation_id: UUID da conversa
        limit: Numero maximo de resultados
    """
    try:
        insights = await buscar_insights_conversa(conversation_id, limit)
        return {
            "conversation_id": conversation_id,
            "total": len(insights),
            "insights": insights,
        }
    except Exception as e:
        logger.error(f"Erro ao buscar insights da conversa: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/cliente/{cliente_id}")
async def get_insights_cliente(
    cliente_id: str,
    limit: int = Query(default=20, le=100)
):
    """
    Busca historico de insights de um cliente/medico.

    Args:
        cliente_id: UUID do cliente
        limit: Numero maximo de resultados
    """
    try:
        insights = await buscar_insights_cliente(cliente_id, limit)

        # Calcular resumo
        if insights:
            positivos = sum(1 for i in insights if i.get("interesse") == "positivo")
            negativos = sum(1 for i in insights if i.get("interesse") == "negativo")
            score_medio = sum(i.get("interesse_score", 0) or 0 for i in insights) / len(insights)
        else:
            positivos = negativos = 0
            score_medio = 0

        return {
            "cliente_id": cliente_id,
            "total": len(insights),
            "resumo": {
                "interesse_positivo": positivos,
                "interesse_negativo": negativos,
                "interesse_score_medio": round(score_medio, 2),
            },
            "insights": insights,
        }
    except Exception as e:
        logger.error(f"Erro ao buscar insights do cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/campaign/{campaign_id}")
async def get_insights_campanha(
    campaign_id: int,
    limit: int = Query(default=100, le=500)
):
    """
    Busca insights de uma campanha especifica.

    Args:
        campaign_id: ID da campanha
        limit: Numero maximo de resultados
    """
    try:
        insights = await buscar_insights_campanha(campaign_id, limit)

        # Calcular metricas agregadas
        if insights:
            total = len(insights)
            positivos = sum(1 for i in insights if i.get("interesse") == "positivo")
            negativos = sum(1 for i in insights if i.get("interesse") == "negativo")
            prontos_vagas = sum(1 for i in insights if i.get("proximo_passo") == "enviar_vagas")
            clientes_unicos = len(set(i.get("cliente_id") for i in insights))
        else:
            total = positivos = negativos = prontos_vagas = clientes_unicos = 0

        return {
            "campaign_id": campaign_id,
            "total_insights": total,
            "metricas": {
                "clientes_unicos": clientes_unicos,
                "interesse_positivo": positivos,
                "interesse_negativo": negativos,
                "taxa_interesse_pct": round(positivos / total * 100, 1) if total > 0 else 0,
                "prontos_para_vagas": prontos_vagas,
            },
            "insights": insights,
        }
    except Exception as e:
        logger.error(f"Erro ao buscar insights da campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign/{campaign_id}/report")
async def get_campaign_report(
    campaign_id: int,
    force_refresh: bool = Query(default=False, description="Ignorar cache e regenerar")
):
    """
    Gera relatorio Julia para uma campanha.

    Retorna analise qualitativa com:
    - Metricas agregadas
    - Medicos em destaque
    - Objecoes encontradas
    - Preferencias comuns
    - Relatorio escrito pela Julia (LLM)

    Cache de 1 hora (use force_refresh=true para ignorar).
    """
    try:
        report = await gerar_relatorio_campanha(
            campaign_id=campaign_id,
            force_refresh=force_refresh,
        )
        return report.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar relatorio da campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/campaign-summary")
async def get_campaign_summary():
    """
    Retorna resumo agregado de todas as campanhas com insights.

    Usa a view materializada campaign_insights.
    """
    try:
        result = supabase.table("campaign_insights").select("*").execute()
        campaigns = result.data or []

        return {
            "total_campanhas": len(campaigns),
            "campanhas": campaigns,
        }
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de campanhas: {e}")
        # Se a view nao existir, retornar vazio
        return {
            "total_campanhas": 0,
            "campanhas": [],
            "erro": str(e),
        }


# =============================================================================
# Endpoints - Estatisticas
# =============================================================================

@router.get("/stats")
async def get_extraction_stats():
    """
    Retorna estatisticas gerais do sistema de extracao.
    """
    try:
        # Buscar status do backfill
        backfill_status = await obter_status_backfill()

        # Estatisticas adicionais
        # Total de insights
        insights_result = supabase.table("conversation_insights").select(
            "id", count="exact"
        ).execute()
        total_insights = insights_result.count or 0

        # Distribuicao de interesse
        dist_query = """
            SELECT interesse, COUNT(*) as total
            FROM conversation_insights
            WHERE interesse IS NOT NULL
            GROUP BY interesse
        """
        # Usar RPC ou query direta se disponivel
        dist_result = supabase.table("conversation_insights").select(
            "interesse"
        ).execute()

        interesse_dist = {}
        for row in (dist_result.data or []):
            interesse = row.get("interesse")
            if interesse:
                interesse_dist[interesse] = interesse_dist.get(interesse, 0) + 1

        # Proximo passo distribuicao
        passo_result = supabase.table("conversation_insights").select(
            "proximo_passo"
        ).execute()

        passo_dist = {}
        for row in (passo_result.data or []):
            passo = row.get("proximo_passo")
            if passo:
                passo_dist[passo] = passo_dist.get(passo, 0) + 1

        return {
            "total_insights": total_insights,
            "backfill": backfill_status,
            "distribuicao_interesse": interesse_dist,
            "distribuicao_proximo_passo": passo_dist,
        }

    except Exception as e:
        logger.error(f"Erro ao buscar estatisticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Endpoints - Backfill
# =============================================================================

@router.post("/backfill")
async def trigger_backfill(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
):
    """
    Dispara backfill de extracoes em background.

    CUIDADO: Pode consumir muitos tokens de LLM se processar muitas interacoes.
    Use dry_run=true para simular primeiro.
    """
    logger.info(
        f"[Backfill] Disparando backfill: dias={request.dias}, "
        f"campanha_id={request.campanha_id}, dry_run={request.dry_run}"
    )

    # Executar em background
    background_tasks.add_task(
        executar_backfill,
        dias=request.dias,
        campanha_id=request.campanha_id,
        dry_run=request.dry_run,
        max_interacoes=request.max_interacoes,
    )

    return BackfillResponse(
        status="started",
        message=f"Backfill iniciado para ultimos {request.dias} dias"
        + (f" (campanha {request.campanha_id})" if request.campanha_id else "")
        + (" [DRY RUN]" if request.dry_run else ""),
    )


@router.get("/backfill/status")
async def get_backfill_status():
    """
    Retorna status atual do backfill (cobertura, pendentes).
    """
    try:
        status = await obter_status_backfill()
        return status
    except Exception as e:
        logger.error(f"Erro ao obter status do backfill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Endpoints - Refresh View
# =============================================================================

@router.post("/refresh-campaign-view")
async def refresh_campaign_view():
    """
    Atualiza a view materializada campaign_insights.

    Deve ser chamado periodicamente (ex: diariamente) para manter dados atualizados.
    """
    try:
        supabase.rpc("refresh_campaign_insights").execute()
        return {"status": "success", "message": "View atualizada com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao atualizar view: {e}")
        raise HTTPException(status_code=500, detail=str(e))
