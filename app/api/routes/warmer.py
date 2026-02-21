"""
Warmer API - Endpoints para gerenciamento do sistema de aquecimento.

Endpoints para:
- Gerenciamento de chips e warmup
- Monitoramento de trust score
- Alertas e early warning
- Status do pool
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from app.services.warmer import (
    # Orchestrator
    iniciar_warmup,
    pausar_warmup,
    executar_ciclo,
    status_pool,
    FaseWarmup,
    # Trust Score
    calcular_trust_score,
    obter_trust_score_cached,
    obter_permissoes,
    TrustLevel,
    # Early Warning
    analisar_chip,
    monitorar_pool,
    SeveridadeAlerta,
    # Scheduler
    planejar_dia_chip,
    consultar_politicas,
    verificar_conformidade,
    seed_politicas,
)
from app.services.warmer.orchestrator import orchestrator
from app.services.warmer.scheduler import scheduler
from app.services.warmer.early_warning import early_warning

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warmer", tags=["warmer"])


# ============================================================================
# Request/Response Models
# ============================================================================


class IniciarWarmupRequest(BaseModel):
    """Request para iniciar warmup."""

    chip_id: str


class IniciarWarmupResponse(BaseModel):
    """Response de iniciar warmup."""

    success: bool
    fase: Optional[str] = None
    trust_score: Optional[int] = None
    atividades_agendadas: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PausarWarmupRequest(BaseModel):
    """Request para pausar warmup."""

    chip_id: str
    motivo: str = "pausa_manual"


class TrustScoreResponse(BaseModel):
    """Response com trust score."""

    chip_id: str
    score: int
    nivel: str
    permissoes: dict
    factors: dict


class PermissoesResponse(BaseModel):
    """Response com permissões."""

    pode_prospectar: bool
    pode_followup: bool
    pode_responder: bool
    limite_hora: int
    limite_dia: int
    delay_minimo_segundos: int


class AlertaResponse(BaseModel):
    """Response de alerta."""

    chip_id: str
    tipo: str
    severidade: str
    mensagem: str
    recomendacao: str
    dados: dict
    created_at: Optional[datetime] = None


class StatusPoolResponse(BaseModel):
    """Response com status do pool."""

    total: int
    por_fase: dict
    por_status: dict
    trust_medio: float
    prontos_operacao: int


class PoliticaResponse(BaseModel):
    """Response de política Meta."""

    id: Optional[str] = None
    categoria: str
    titulo: str
    conteudo: str
    fonte_url: Optional[str] = None
    similarity: Optional[float] = None


class ConformidadeResponse(BaseModel):
    """Response de verificação de conformidade."""

    permitido: bool
    riscos: List[str]
    recomendacoes: List[str]
    politicas_relacionadas: List[dict]


class TransicaoRequest(BaseModel):
    """Request para transição manual de fase."""

    chip_id: str
    nova_fase: str


class VerificarConformidadeRequest(BaseModel):
    """Request para verificar conformidade de ação."""

    acao: str


# ============================================================================
# Health Check (Sprint 65)
# ============================================================================


@router.get("/health")
async def api_warmer_health():
    """
    Health check do sistema de warmup.

    Retorna diagnóstico completo: health_status, pool summary,
    taxa de sucesso por tipo de atividade, alertas ativos.

    health_status:
    - healthy: CONVERSA_PAR >80% sucesso e chips ativos
    - degraded: CONVERSA_PAR 50-80% ou sem dados hoje
    - critical: CONVERSA_PAR <50% ou sem chips ativos
    """
    from app.services.warmer.health import diagnostico_warmup

    try:
        return await diagnostico_warmup()
    except Exception as e:
        logger.error(f"[Warmer API] Erro no health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chip Warmup Endpoints
# ============================================================================


@router.post("/iniciar", response_model=IniciarWarmupResponse)
async def api_iniciar_warmup(request: IniciarWarmupRequest):
    """
    Inicia processo de warmup para um chip.

    O chip deve estar conectado na Evolution API.
    """
    try:
        resultado = await iniciar_warmup(request.chip_id)
        return IniciarWarmupResponse(**resultado)
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao iniciar warmup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pausar")
async def api_pausar_warmup(request: PausarWarmupRequest):
    """
    Pausa processo de warmup de um chip.

    Cancela atividades agendadas e coloca chip em repouso.
    """
    try:
        resultado = await pausar_warmup(request.chip_id, request.motivo)
        return resultado
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao pausar warmup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transicao")
async def api_transicao_fase(request: TransicaoRequest):
    """
    Força transição de fase de um chip.

    Use com cuidado - transições manuais podem afetar o warmup.
    """
    try:
        # Validar fase
        try:
            FaseWarmup(request.nova_fase)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Fase inválida: {request.nova_fase}")

        resultado = await orchestrator.executar_transicao(
            request.chip_id,
            request.nova_fase,
            automatico=False,
        )
        return resultado
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Warmer API] Erro na transição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ciclo")
async def api_executar_ciclo(background_tasks: BackgroundTasks):
    """
    Executa ciclo de warmup em background.

    Processa atividades pendentes e verifica transições.
    """
    background_tasks.add_task(executar_ciclo)
    return {"message": "Ciclo iniciado em background"}


# ============================================================================
# Trust Score Endpoints
# ============================================================================


@router.get("/trust/{chip_id}", response_model=TrustScoreResponse)
async def api_obter_trust_score(chip_id: str, recalcular: bool = False):
    """
    Obtém trust score de um chip.

    Args:
        chip_id: ID do chip
        recalcular: Se True, recalcula o score antes de retornar
    """
    try:
        if recalcular:
            resultado = await calcular_trust_score(chip_id)
        else:
            resultado = await obter_trust_score_cached(chip_id)
            if not resultado:
                raise HTTPException(status_code=404, detail="Chip não encontrado")

        return TrustScoreResponse(**resultado)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao obter trust: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/permissoes/{chip_id}", response_model=PermissoesResponse)
async def api_obter_permissoes(chip_id: str):
    """Obtém permissões atuais de um chip."""
    try:
        permissoes = await obter_permissoes(chip_id)
        return PermissoesResponse(
            pode_prospectar=permissoes.pode_prospectar,
            pode_followup=permissoes.pode_followup,
            pode_responder=permissoes.pode_responder,
            limite_hora=permissoes.limite_hora,
            limite_dia=permissoes.limite_dia,
            delay_minimo_segundos=permissoes.delay_minimo_segundos,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao obter permissões: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Early Warning Endpoints
# ============================================================================


@router.get("/alertas", response_model=List[AlertaResponse])
async def api_listar_alertas(
    chip_id: Optional[str] = None,
    severidade: Optional[str] = None,
):
    """
    Lista alertas ativos.

    Args:
        chip_id: Filtrar por chip
        severidade: Filtrar por severidade mínima (info, atencao, alerta, critico)
    """
    try:
        sev_filter = None
        if severidade:
            try:
                sev_filter = SeveridadeAlerta(severidade)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Severidade inválida: {severidade}")

        alertas = await early_warning.obter_alertas_ativos(chip_id, sev_filter)

        return [
            AlertaResponse(
                chip_id=a.chip_id,
                tipo=a.tipo.value,
                severidade=a.severidade.value,
                mensagem=a.mensagem,
                recomendacao=a.recomendacao,
                dados=a.dados,
                created_at=a.created_at,
            )
            for a in alertas
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao listar alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alertas/{chip_id}/analisar", response_model=List[AlertaResponse])
async def api_analisar_chip(chip_id: str):
    """
    Analisa um chip e retorna alertas encontrados.

    Executa verificações em tempo real, não usa cache.
    """
    try:
        alertas = await analisar_chip(chip_id)

        return [
            AlertaResponse(
                chip_id=a.chip_id,
                tipo=a.tipo.value,
                severidade=a.severidade.value,
                mensagem=a.mensagem,
                recomendacao=a.recomendacao,
                dados=a.dados,
                created_at=a.created_at,
            )
            for a in alertas
        ]
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao analisar chip: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alertas/monitorar")
async def api_monitorar_pool(background_tasks: BackgroundTasks):
    """
    Executa monitoramento completo do pool em background.

    Analisa todos os chips ativos e gera alertas.
    """
    background_tasks.add_task(monitorar_pool)
    return {"message": "Monitoramento iniciado em background"}


@router.post("/alertas/{alerta_id}/resolver")
async def api_resolver_alerta(alerta_id: str, resolucao: str = "resolvido_manual"):
    """Marca um alerta como resolvido."""
    try:
        await early_warning.resolver_alerta(alerta_id, resolucao)
        return {"success": True}
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao resolver alerta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Pool Status Endpoints
# ============================================================================


@router.get("/status", response_model=StatusPoolResponse)
async def api_status_pool():
    """Obtém status geral do pool de chips."""
    try:
        status = await status_pool()
        return StatusPoolResponse(**status)
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/estatisticas/{chip_id}")
async def api_estatisticas_chip(chip_id: str):
    """Obtém estatísticas de atividades de um chip."""
    try:
        stats = await scheduler.obter_estatisticas(chip_id)
        return stats
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Scheduler Endpoints
# ============================================================================


@router.post("/agenda/{chip_id}/planejar")
async def api_planejar_dia(chip_id: str):
    """
    Planeja atividades do dia para um chip.

    Cancela atividades anteriores e cria nova agenda.
    """
    try:
        # Cancelar atividades existentes
        await scheduler.cancelar_atividades(chip_id, "replanejamento")

        # Planejar novo dia
        atividades = await planejar_dia_chip(chip_id)
        await scheduler.salvar_agenda(atividades)

        return {
            "success": True,
            "atividades_agendadas": len(atividades),
        }
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao planejar dia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agenda/proximas")
async def api_proximas_atividades(
    limite: int = Query(10, ge=1, le=50),
    chip_id: Optional[str] = None,
):
    """Lista próximas atividades agendadas."""
    try:
        atividades = await scheduler.obter_proximas_atividades(limite, chip_id)

        return [
            {
                "id": a.id,
                "chip_id": a.chip_id,
                "tipo": a.tipo.value,
                "horario": a.horario.isoformat(),
                "prioridade": a.prioridade,
                "status": a.status,
            }
            for a in atividades
        ]
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao listar atividades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Meta RAG Endpoints
# ============================================================================


@router.get("/politicas", response_model=List[PoliticaResponse])
async def api_consultar_politicas(
    pergunta: str = Query(..., min_length=3),
    categoria: Optional[str] = None,
    limite: int = Query(5, ge=1, le=20),
):
    """
    Consulta políticas Meta/WhatsApp via RAG.

    Args:
        pergunta: Texto da consulta
        categoria: Filtrar por categoria (limites, quality_rating, motivos_ban, boas_praticas, proibicoes)
        limite: Número máximo de resultados
    """
    try:
        politicas = await consultar_politicas(pergunta, categoria, limite)

        return [
            PoliticaResponse(
                id=p.get("id"),
                categoria=p.get("categoria", ""),
                titulo=p.get("titulo", ""),
                conteudo=p.get("conteudo", ""),
                fonte_url=p.get("fonte_url"),
                similarity=p.get("similarity"),
            )
            for p in politicas
        ]
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao consultar políticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/politicas/verificar", response_model=ConformidadeResponse)
async def api_verificar_conformidade(body: VerificarConformidadeRequest):
    """
    Verifica se uma ação está em conformidade com políticas.

    Args:
        body: Request com a ação a verificar
    """
    try:
        resultado = await verificar_conformidade(body.acao)
        return ConformidadeResponse(**resultado)
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao verificar conformidade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/politicas/seed")
async def api_seed_politicas():
    """
    Popula banco com políticas iniciais.

    Use apenas na primeira configuração ou para atualizar políticas.
    """
    try:
        count = await seed_politicas()
        return {"success": True, "politicas_inseridas": count}
    except Exception as e:
        logger.error(f"[Warmer API] Erro ao seed políticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Fases Endpoints
# ============================================================================


@router.get("/fases")
async def api_listar_fases():
    """Lista todas as fases de warmup disponíveis."""
    return {
        "fases": [f.value for f in FaseWarmup],
        "descricoes": {
            "repouso": "Chip inativo, sem warmup",
            "setup": "Configuração inicial (1-3 dias)",
            "primeiros_contatos": "Primeiras conversas (3-7 dias)",
            "expansao": "Aumentando volume (7-14 dias)",
            "pre_operacao": "Preparação final (14-21 dias)",
            "teste_graduacao": "Teste antes de produção (21-28 dias)",
            "operacao": "Pronto para uso comercial",
        },
    }


@router.get("/trust-levels")
async def api_listar_trust_levels():
    """Lista níveis de trust score."""
    return {
        "levels": [level.value for level in TrustLevel],
        "descricoes": {
            "verde": "Excelente (80-100) - Todas permissões",
            "amarelo": "Bom (60-79) - Maioria das permissões",
            "laranja": "Atenção (40-59) - Permissões reduzidas",
            "vermelho": "Alerta (20-39) - Modo restrito",
            "critico": "Crítico (0-19) - Apenas resposta",
        },
    }
