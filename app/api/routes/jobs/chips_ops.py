"""
Operacoes de chips: trust score, sincronizacao, snapshots, reset.

Sprint 58 - Epic 1: Decomposicao de jobs.py
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.supabase import supabase

from ._helpers import job_endpoint

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# Trust Score (Sprint 36)
# =============================================================================


@router.post("/atualizar-trust-scores")
@job_endpoint("atualizar-trust-scores")
async def job_atualizar_trust_scores():
    """
    Job para recalcular Trust Score de todos os chips ativos.

    O Trust Score e calculado dinamicamente baseado em:
    - Idade do chip (dias desde criacao)
    - Taxa de resposta (mensagens recebidas / enviadas)
    - Taxa de delivery (mensagens entregues com sucesso)
    - Erros recentes (falhas nas ultimas 24h)
    - Conversas bidirecionais (interacoes reais)
    - Dias sem incidente (estabilidade)

    Schedule: */15 * * * * (a cada 15 minutos)
    """
    from app.services.warmer.trust_score import calcular_trust_score

    # Buscar chips ativos
    chips = (
        supabase.table("chips")
        .select("id, telefone")
        .in_("status", ["active", "warming", "ready"])
        .execute()
    )

    if not chips.data:
        return {
            "status": "ok",
            "message": "Nenhum chip ativo para atualizar",
            "atualizados": 0,
            "erros": 0,
        }

    atualizados = 0
    erros = 0
    detalhes = []

    for chip in chips.data:
        try:
            result = await calcular_trust_score(chip["id"])
            atualizados += 1
            detalhes.append(
                {
                    "telefone": chip["telefone"][-4:],  # ultimos 4 digitos
                    "score": result["score"],
                    "nivel": result["nivel"],
                }
            )
        except Exception as e:
            logger.error(f"Erro ao atualizar trust score de {chip['id']}: {e}")
            erros += 1

    # Log resumido
    logger.info(f"[TrustScore] Atualização concluída: {atualizados} chips, {erros} erros")

    return {
        "status": "ok",
        "message": f"{atualizados} chip(s) atualizado(s), {erros} erro(s)",
        "atualizados": atualizados,
        "erros": erros,
        "detalhes": detalhes[:10],  # Limitar para nao sobrecarregar resposta
    }


# =============================================================================
# Sincronizacao de Chips (Sprint 25)
# =============================================================================


@router.post("/sincronizar-chips")
@job_endpoint("sincronizar-chips")
async def job_sincronizar_chips():
    """
    Job para sincronizar chips com Evolution API.

    Sprint 25: Funcionalidade base
    Sprint 36 T11.2: Adicionado alerta de muitas instancias desconectadas

    Atualiza a tabela chips com o estado atual das instancias na Evolution API.
    - Atualiza status de conexao de chips existentes
    - Cria novos chips para instancias desconhecidas
    - Marca chips sem instancia como desconectados
    - Alerta se > 30% das instancias estao desconectadas (Sprint 36)

    Schedule: */5 * * * * (a cada 5 minutos)
    """
    from app.services.chips import sincronizar_chips_com_evolution

    resultado = await sincronizar_chips_com_evolution()

    # Sprint 36 T11.2: Alertar se muitas instancias desconectadas
    # Sprint 47: Removida notificacao Slack (dashboard monitora isso agora)
    total = resultado.get("chips_conectados", 0) + resultado.get("chips_desconectados", 0)
    desconectadas = resultado.get("chips_desconectados", 0)

    if total > 0 and desconectadas > total * 0.3:
        logger.warning(f"[SyncChips] ALERTA: {desconectadas}/{total} instâncias desconectadas")

    return {
        "status": "ok",
        "instancias_evolution": resultado["instancias_evolution"],
        "chips_atualizados": resultado["chips_atualizados"],
        "chips_criados": resultado["chips_criados"],
        "chips_conectados": resultado["chips_conectados"],
        "chips_desconectados": resultado["chips_desconectados"],
        "erros": resultado["erros"],
    }


# =============================================================================
# Snapshot de Chips (Sprint 41)
# =============================================================================


@router.post("/snapshot-chips-diario")
@job_endpoint("snapshot-chips-diario")
async def job_snapshot_chips_diario():
    """
    Job para criar snapshots diarios das metricas de chips.

    Captura o estado dos contadores de cada chip antes do reset diario.
    Deve ser executado as 23:55 (antes do reset as 00:05).

    Sprint 41 - Rastreamento de Chips e Status de Entrega.

    Schedule: 55 23 * * * (23:55 todos os dias)
    """
    # Usar RPC para criar snapshots de todos os chips
    result = supabase.rpc("chip_criar_snapshots_todos").execute()

    if not result.data:
        return JSONResponse({"status": "error", "message": "RPC retornou vazio"}, status_code=500)

    row = result.data[0] if isinstance(result.data, list) else result.data

    logger.info(
        f"[SnapshotChips] Concluído: {row.get('snapshots_criados', 0)} criados, "
        f"{row.get('snapshots_existentes', 0)} existentes, {row.get('erros', 0)} erros"
    )

    return {
        "status": "ok",
        "total_chips": row.get("total_chips", 0),
        "snapshots_criados": row.get("snapshots_criados", 0),
        "snapshots_existentes": row.get("snapshots_existentes", 0),
        "erros": row.get("erros", 0),
    }


@router.post("/resetar-contadores-chips")
@job_endpoint("resetar-contadores-chips")
async def job_resetar_contadores_chips():
    """
    Job para resetar contadores diarios dos chips.

    Reseta msgs_enviadas_hoje e msgs_recebidas_hoje para 0.
    Deve ser executado as 00:05 (apos o snapshot as 23:55).

    Sprint 41 - Rastreamento de Chips e Status de Entrega.

    Schedule: 5 0 * * * (00:05 todos os dias)
    """
    # Usar RPC para resetar contadores
    result = supabase.rpc("chip_resetar_contadores_diarios").execute()

    if not result.data:
        return JSONResponse({"status": "error", "message": "RPC retornou vazio"}, status_code=500)

    row = result.data[0] if isinstance(result.data, list) else result.data
    chips_resetados = row.get("chips_resetados", 0)

    logger.info(f"[ResetChips] {chips_resetados} chips resetados")

    return {
        "status": "ok",
        "chips_resetados": chips_resetados,
    }
