"""
Classificador de mensagens de grupos.

Sprint 14 - E03/E04

Processa mensagens aplicando:
1. Heurística (E03) - filtro rápido por keywords
2. LLM (E04) - classificação precisa por IA
"""

import asyncio
from datetime import datetime, UTC
from typing import TYPE_CHECKING, List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.heuristica import calcular_score_heuristica, ResultadoHeuristica

if TYPE_CHECKING:
    from app.services.grupos.classificador_llm import ResultadoClassificacaoLLM

logger = get_logger(__name__)

# Rate limiting para LLM
MAX_REQUESTS_POR_MINUTO = 60
DELAY_ENTRE_REQUESTS = 1.0  # segundos


async def buscar_mensagens_pendentes(limite: int = 100) -> List[dict]:
    """
    Busca mensagens com status pendente para classificação.

    Args:
        limite: Máximo de mensagens a buscar

    Returns:
        Lista de mensagens pendentes
    """
    result = (
        supabase.table("mensagens_grupo")
        .select("id, texto")
        .eq("status", "pendente")
        .order("created_at")
        .limit(limite)
        .execute()
    )

    return result.data


async def atualizar_resultado_heuristica(mensagem_id: UUID, resultado: ResultadoHeuristica) -> None:
    """
    Atualiza mensagem com resultado da heurística.

    Args:
        mensagem_id: ID da mensagem
        resultado: Resultado da análise
    """
    novo_status = "heuristica_passou" if resultado.passou else "heuristica_rejeitou"

    supabase.table("mensagens_grupo").update(
        {
            "status": novo_status,
            "passou_heuristica": resultado.passou,
            "score_heuristica": resultado.score,
            "keywords_encontradas": resultado.keywords_encontradas,
            "motivo_descarte": resultado.motivo_rejeicao,
            "processado_em": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(mensagem_id)).execute()


async def classificar_batch_heuristica(limite: int = 100) -> dict:
    """
    Processa um batch de mensagens com heurística.

    Args:
        limite: Tamanho do batch

    Returns:
        Estatísticas do processamento
    """
    mensagens = await buscar_mensagens_pendentes(limite)

    stats = {
        "total": len(mensagens),
        "passou": 0,
        "rejeitou": 0,
        "erros": 0,
    }

    for msg in mensagens:
        try:
            resultado = calcular_score_heuristica(msg.get("texto", ""))

            await atualizar_resultado_heuristica(mensagem_id=UUID(msg["id"]), resultado=resultado)

            if resultado.passou:
                stats["passou"] += 1
            else:
                stats["rejeitou"] += 1

        except Exception as e:
            logger.error(f"Erro ao classificar mensagem {msg['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Heurística processou {stats['total']} mensagens: "
        f"{stats['passou']} passaram, {stats['rejeitou']} rejeitadas"
    )

    return stats


async def classificar_mensagem_individual(mensagem_id: UUID, texto: str) -> ResultadoHeuristica:
    """
    Classifica uma mensagem individual com heurística.

    Args:
        mensagem_id: ID da mensagem
        texto: Texto da mensagem

    Returns:
        Resultado da heurística
    """
    resultado = calcular_score_heuristica(texto)

    await atualizar_resultado_heuristica(mensagem_id, resultado)

    return resultado


# =============================================================================
# E04 - Classificação LLM
# =============================================================================


async def buscar_mensagens_para_classificacao_llm(limite: int = 50) -> List[dict]:
    """
    Busca mensagens que passaram na heurística para classificação LLM.
    """
    result = (
        supabase.table("mensagens_grupo")
        .select("id, texto, grupo_id, contato_id")
        .eq("status", "heuristica_passou")
        .order("created_at")
        .limit(limite)
        .execute()
    )

    return result.data


async def buscar_contexto_mensagem(grupo_id: str, contato_id: str) -> tuple:
    """Busca nome do grupo e contato para contexto."""
    nome_grupo = ""
    nome_contato = ""

    try:
        if grupo_id:
            grupo = (
                supabase.table("grupos_whatsapp")
                .select("nome")
                .eq("id", grupo_id)
                .single()
                .execute()
            )
            nome_grupo = grupo.data.get("nome", "") if grupo.data else ""

        if contato_id:
            contato = (
                supabase.table("contatos_grupo")
                .select("nome")
                .eq("id", contato_id)
                .single()
                .execute()
            )
            nome_contato = contato.data.get("nome", "") if contato.data else ""
    except Exception:
        pass

    return nome_grupo, nome_contato


async def atualizar_resultado_classificacao_llm(
    mensagem_id: UUID, resultado: "ResultadoClassificacaoLLM"
) -> None:
    """Atualiza mensagem com resultado da classificação LLM."""

    novo_status = "classificada_oferta" if resultado.eh_oferta else "classificada_nao_oferta"

    if resultado.erro:
        novo_status = "erro_classificacao"

    supabase.table("mensagens_grupo").update(
        {
            "status": novo_status,
            "eh_oferta": resultado.eh_oferta,
            "confianca_classificacao": resultado.confianca,
            "processado_em": datetime.now(UTC).isoformat(),
        }
    ).eq("id", str(mensagem_id)).execute()


async def classificar_batch_llm(limite: int = 50) -> dict:
    """
    Processa batch de mensagens com LLM.

    Args:
        limite: Tamanho do batch

    Returns:
        Estatísticas do processamento
    """
    from app.services.grupos.classificador_llm import classificar_com_llm

    mensagens = await buscar_mensagens_para_classificacao_llm(limite)

    stats = {
        "total": len(mensagens),
        "ofertas": 0,
        "nao_ofertas": 0,
        "erros": 0,
        "tokens_total": 0,
        "do_cache": 0,
    }

    for msg in mensagens:
        try:
            # Buscar contexto
            nome_grupo, nome_contato = await buscar_contexto_mensagem(
                msg.get("grupo_id"), msg.get("contato_id")
            )

            # Classificar
            resultado = await classificar_com_llm(
                texto=msg.get("texto", ""), nome_grupo=nome_grupo, nome_contato=nome_contato
            )

            # Atualizar banco
            await atualizar_resultado_classificacao_llm(
                mensagem_id=UUID(msg["id"]), resultado=resultado
            )

            if resultado.eh_oferta:
                stats["ofertas"] += 1
            else:
                stats["nao_ofertas"] += 1

            stats["tokens_total"] += resultado.tokens_usados

            if resultado.do_cache:
                stats["do_cache"] += 1

            # Rate limiting (apenas se não veio do cache)
            if not resultado.do_cache:
                await asyncio.sleep(DELAY_ENTRE_REQUESTS)

        except Exception as e:
            logger.error(f"Erro ao classificar mensagem {msg['id']}: {e}")
            stats["erros"] += 1

    logger.info(
        f"Classificação LLM processou {stats['total']} mensagens: "
        f"{stats['ofertas']} ofertas, {stats['nao_ofertas']} não-ofertas, "
        f"{stats['tokens_total']} tokens usados, {stats['do_cache']} do cache"
    )

    return stats
