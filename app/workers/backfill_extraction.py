"""
Worker de backfill para extrair dados de conversas historicas.

Sprint 53: Discovery Intelligence Pipeline.

Processa conversas dos ultimos N dias para popular conversation_insights.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase
from app.services.extraction import (
    extrair_dados_conversa,
    ExtractionContext,
    salvar_insight,
    salvar_memorias_extraidas,
)

logger = logging.getLogger(__name__)

# Configuracoes
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 5  # segundos
MAX_INTERACOES = 1000
DELAY_BETWEEN_CALLS = 0.5  # segundos (rate limit LLM)


async def executar_backfill(
    dias: int = 30,
    campanha_id: Optional[int] = None,
    dry_run: bool = False,
    max_interacoes: int = MAX_INTERACOES,
) -> dict:
    """
    Executa backfill de extracoes para conversas historicas.

    Args:
        dias: Quantos dias para tras processar
        campanha_id: Opcional - processar apenas uma campanha
        dry_run: Se True, nao salva (apenas simula)
        max_interacoes: Limite maximo de interacoes a processar

    Returns:
        Estatisticas do backfill
    """
    stats = {
        "total_interacoes": 0,
        "processadas": 0,
        "erros": 0,
        "ja_processadas": 0,
        "sem_resposta": 0,
        "inicio": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
    }

    data_inicio = datetime.now(timezone.utc) - timedelta(days=dias)

    logger.info(
        f"[Backfill] Iniciando backfill: dias={dias}, campanha_id={campanha_id}, dry_run={dry_run}"
    )

    # Buscar interacoes elegiveis (mensagens de medicos)
    try:
        query = (
            supabase.table("interacoes")
            .select("""
                id,
                conversation_id,
                cliente_id,
                conteudo,
                created_at
            """)
            .eq("tipo", "entrada")
            .eq("autor_tipo", "medico")
            .gte("created_at", data_inicio.isoformat())
            .order("created_at", desc=False)
            .limit(max_interacoes)
        )

        result = query.execute()
        interacoes = result.data or []

    except Exception as e:
        logger.error(f"[Backfill] Erro ao buscar interacoes: {e}")
        stats["erro_fatal"] = str(e)
        return stats

    stats["total_interacoes"] = len(interacoes)
    logger.info(f"[Backfill] Encontradas {len(interacoes)} interacoes para processar")

    if not interacoes:
        stats["fim"] = datetime.now(timezone.utc).isoformat()
        return stats

    # Processar em batches
    for i in range(0, len(interacoes), BATCH_SIZE):
        batch = interacoes[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(interacoes) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(f"[Backfill] Processando batch {batch_num}/{total_batches}")

        for interacao in batch:
            try:
                result = await _processar_interacao(
                    interacao=interacao,
                    campanha_id=campanha_id,
                    dry_run=dry_run,
                )

                if result == "processada":
                    stats["processadas"] += 1
                elif result == "ja_processada":
                    stats["ja_processadas"] += 1
                elif result == "sem_resposta":
                    stats["sem_resposta"] += 1
                elif result == "erro":
                    stats["erros"] += 1

                # Rate limit
                await asyncio.sleep(DELAY_BETWEEN_CALLS)

            except Exception as e:
                logger.error(f"[Backfill] Erro ao processar interacao {interacao['id']}: {e}")
                stats["erros"] += 1

        # Log de progresso
        logger.info(
            f"[Backfill] Batch {batch_num} concluido. "
            f"Processadas: {stats['processadas']}, "
            f"Ja processadas: {stats['ja_processadas']}, "
            f"Erros: {stats['erros']}"
        )

        # Delay entre batches
        if i + BATCH_SIZE < len(interacoes):
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    stats["fim"] = datetime.now(timezone.utc).isoformat()
    logger.info(f"[Backfill] Concluido: {stats}")

    return stats


async def _processar_interacao(
    interacao: dict,
    campanha_id: Optional[int],
    dry_run: bool,
) -> str:
    """
    Processa uma interacao individual.

    Returns:
        "processada", "ja_processada", "sem_resposta", ou "erro"
    """
    interaction_id = interacao["id"]
    conversation_id = interacao["conversation_id"]
    cliente_id = interacao["cliente_id"]

    # Verificar se ja foi processada
    try:
        existing = (
            supabase.table("conversation_insights")
            .select("id")
            .eq("interaction_id", interaction_id)
            .execute()
        )

        if existing.data:
            return "ja_processada"
    except Exception:
        pass  # Continua se erro na verificacao

    # Buscar resposta da Julia
    resposta = await _buscar_resposta_julia(
        conversation_id,
        interacao["created_at"],
    )

    if not resposta:
        return "sem_resposta"

    # Buscar dados do cliente
    cliente = await _buscar_cliente(cliente_id)
    if not cliente:
        return "erro"

    # Criar contexto
    context = ExtractionContext(
        mensagem_medico=interacao["conteudo"] or "",
        resposta_julia=resposta,
        nome_medico=cliente.get("primeiro_nome", "Medico"),
        especialidade_cadastrada=cliente.get("especialidade"),
        regiao_cadastrada=cliente.get("cidade"),
        campanha_id=campanha_id,
        conversa_id=conversation_id,
        cliente_id=cliente_id,
    )

    # Extrair
    extraction = await extrair_dados_conversa(context)

    if dry_run:
        logger.debug(
            f"[Backfill] DRY RUN - Interacao {interaction_id}: "
            f"interesse={extraction.interesse.value}"
        )
        return "processada"

    # Salvar insight
    await salvar_insight(
        conversation_id=conversation_id,
        interaction_id=interaction_id,
        campaign_id=campanha_id,
        cliente_id=cliente_id,
        extraction=extraction,
    )

    # Salvar memorias se houver
    if extraction.preferencias or extraction.restricoes:
        await salvar_memorias_extraidas(
            cliente_id=cliente_id,
            extraction=extraction,
            conversa_id=conversation_id,
        )

    return "processada"


async def _buscar_resposta_julia(
    conversation_id: str,
    after_timestamp: str,
) -> Optional[str]:
    """Busca a resposta da Julia imediatamente apos a mensagem do medico."""
    try:
        result = (
            supabase.table("interacoes")
            .select("conteudo")
            .eq("conversation_id", conversation_id)
            .eq("autor_tipo", "julia")
            .gt("created_at", after_timestamp)
            .order("created_at")
            .limit(1)
            .execute()
        )

        if result.data:
            return result.data[0]["conteudo"]
    except Exception as e:
        logger.warning(f"[Backfill] Erro ao buscar resposta Julia: {e}")

    return None


async def _buscar_cliente(cliente_id: str) -> Optional[dict]:
    """Busca dados do cliente."""
    try:
        result = (
            supabase.table("clientes")
            .select("id, primeiro_nome, especialidade, cidade")
            .eq("id", cliente_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.warning(f"[Backfill] Erro ao buscar cliente {cliente_id}: {e}")
        return None


async def obter_status_backfill() -> dict:
    """
    Retorna estatisticas do backfill.

    Returns:
        Dict com metricas de cobertura
    """
    try:
        # Total de interacoes de medicos nos ultimos 30 dias
        data_inicio = datetime.now(timezone.utc) - timedelta(days=30)

        total_result = (
            supabase.table("interacoes")
            .select("id", count="exact")
            .eq("tipo", "entrada")
            .eq("autor_tipo", "medico")
            .gte("created_at", data_inicio.isoformat())
            .execute()
        )
        total_interacoes = total_result.count or 0

        # Total de insights nos ultimos 30 dias
        insights_result = (
            supabase.table("conversation_insights")
            .select("id", count="exact")
            .gte("created_at", data_inicio.isoformat())
            .execute()
        )
        total_insights = insights_result.count or 0

        # Cobertura
        cobertura = (total_insights / total_interacoes * 100) if total_interacoes > 0 else 0

        return {
            "total_interacoes_30d": total_interacoes,
            "total_insights_30d": total_insights,
            "cobertura_pct": round(cobertura, 1),
            "pendentes": total_interacoes - total_insights,
        }

    except Exception as e:
        logger.error(f"[Backfill] Erro ao obter status: {e}")
        return {"erro": str(e)}
