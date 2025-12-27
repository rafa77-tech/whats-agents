"""
Classificador heurístico de mensagens de grupos.

Sprint 14 - E03 - S03.4

Processa mensagens pendentes aplicando heurística para filtrar
mensagens que claramente não são ofertas de plantão.
"""

from datetime import datetime, UTC
from typing import List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase
from app.services.grupos.heuristica import calcular_score_heuristica, ResultadoHeuristica

logger = get_logger(__name__)


async def buscar_mensagens_pendentes(limite: int = 100) -> List[dict]:
    """
    Busca mensagens com status pendente para classificação.

    Args:
        limite: Máximo de mensagens a buscar

    Returns:
        Lista de mensagens pendentes
    """
    result = supabase.table("mensagens_grupo") \
        .select("id, texto") \
        .eq("status", "pendente") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def atualizar_resultado_heuristica(
    mensagem_id: UUID,
    resultado: ResultadoHeuristica
) -> None:
    """
    Atualiza mensagem com resultado da heurística.

    Args:
        mensagem_id: ID da mensagem
        resultado: Resultado da análise
    """
    novo_status = "heuristica_passou" if resultado.passou else "heuristica_rejeitou"

    supabase.table("mensagens_grupo") \
        .update({
            "status": novo_status,
            "passou_heuristica": resultado.passou,
            "score_heuristica": resultado.score,
            "keywords_encontradas": resultado.keywords_encontradas,
            "motivo_descarte": resultado.motivo_rejeicao,
            "processado_em": datetime.now(UTC).isoformat(),
        }) \
        .eq("id", str(mensagem_id)) \
        .execute()


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

            await atualizar_resultado_heuristica(
                mensagem_id=UUID(msg["id"]),
                resultado=resultado
            )

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
