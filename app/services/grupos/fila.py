"""
Gerenciamento de fila de processamento de mensagens de grupos.

Sprint 14 - E11 - Worker e Orquestração
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from enum import Enum
from typing import Optional, List
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# =============================================================================
# S11.1 - Definição de Estágios e Estruturas
# =============================================================================

class EstagioPipeline(Enum):
    """Estágios do pipeline de processamento."""
    PENDENTE = "pendente"
    HEURISTICA = "heuristica"
    CLASSIFICACAO = "classificacao"
    EXTRACAO = "extracao"
    NORMALIZACAO = "normalizacao"
    DEDUPLICACAO = "deduplicacao"
    IMPORTACAO = "importacao"
    FINALIZADO = "finalizado"
    ERRO = "erro"
    DESCARTADO = "descartado"


@dataclass
class ItemFila:
    """Item na fila de processamento."""
    id: UUID
    mensagem_id: UUID
    estagio: EstagioPipeline
    tentativas: int = 0
    max_tentativas: int = 3
    ultimo_erro: Optional[str] = None
    proximo_retry: Optional[datetime] = None
    vaga_grupo_id: Optional[UUID] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None


# Delays para retry exponencial (em minutos)
RETRY_DELAYS = [1, 5, 15]


# =============================================================================
# S11.2 - Funções de Enfileiramento
# =============================================================================

async def enfileirar_mensagem(mensagem_id: UUID) -> Optional[UUID]:
    """
    Adiciona mensagem à fila de processamento.

    Usa INSERT simples porque:
    1. Deduplicação já acontece no webhook via Redis
    2. O constraint parcial (mensagem_id WHERE vaga_grupo_id IS NULL) não funciona
       com upsert do cliente Supabase Python

    Args:
        mensagem_id: ID da mensagem a processar

    Returns:
        ID do item na fila, ou None se já existir
    """
    try:
        result = supabase.table("fila_processamento_grupos").insert({
            "mensagem_id": str(mensagem_id),
            "estagio": EstagioPipeline.PENDENTE.value,
            "tentativas": 0,
        }).execute()

        item_id = UUID(result.data[0]["id"])
        logger.debug(f"Mensagem {mensagem_id} enfileirada: {item_id}")
        return item_id

    except Exception as e:
        # Constraint violation (duplicata) - mensagem já está na fila
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            logger.debug(f"Mensagem {mensagem_id} já está na fila (ignorando duplicata)")
            return None
        # Outro erro - propagar
        logger.error(f"Erro ao enfileirar mensagem {mensagem_id}: {e}")
        raise


async def criar_itens_para_vagas(
    mensagem_id: UUID,
    vagas_ids: List[str],
    estagio: EstagioPipeline = EstagioPipeline.NORMALIZACAO
) -> int:
    """
    Cria itens na fila para cada vaga extraída de uma mensagem.

    Quando a extração gera múltiplas vagas, cada uma precisa de
    seu próprio item na fila para os estágios seguintes.

    Args:
        mensagem_id: ID da mensagem original
        vagas_ids: Lista de IDs de vagas_grupo criadas
        estagio: Estágio inicial (padrão: normalização)

    Returns:
        Quantidade de itens criados
    """
    if not vagas_ids:
        return 0

    dados = [
        {
            "mensagem_id": str(mensagem_id),
            "vaga_grupo_id": vaga_id,
            "estagio": estagio.value,
            "tentativas": 0,
        }
        for vaga_id in vagas_ids
    ]

    result = supabase.table("fila_processamento_grupos") \
        .insert(dados) \
        .execute()

    count = len(result.data) if result.data else 0
    logger.info(f"Criados {count} itens para vagas da mensagem {mensagem_id}")

    return count


async def enfileirar_batch(mensagens_ids: List[UUID]) -> int:
    """
    Enfileira várias mensagens de uma vez.

    Args:
        mensagens_ids: Lista de IDs de mensagens

    Returns:
        Quantidade de itens enfileirados
    """
    if not mensagens_ids:
        return 0

    dados = [
        {
            "mensagem_id": str(mid),
            "estagio": EstagioPipeline.PENDENTE.value,
            "tentativas": 0,
        }
        for mid in mensagens_ids
    ]

    result = supabase.table("fila_processamento_grupos") \
        .upsert(dados, on_conflict="mensagem_id") \
        .execute()

    count = len(result.data)
    logger.info(f"Enfileiradas {count} mensagens")

    return count


# =============================================================================
# S11.3 - Funções de Busca
# =============================================================================

async def buscar_proximos_pendentes(
    estagio: EstagioPipeline,
    limite: int = 50
) -> List[dict]:
    """
    Busca próximos itens para processar em um estágio.

    Prioriza itens sem erro, depois com retry disponível.

    Args:
        estagio: Estágio do pipeline
        limite: Máximo de itens a retornar

    Returns:
        Lista de itens para processar
    """
    agora = datetime.now(UTC).isoformat()

    result = supabase.table("fila_processamento_grupos") \
        .select("id, mensagem_id, vaga_grupo_id, tentativas") \
        .eq("estagio", estagio.value) \
        .lt("tentativas", 3) \
        .or_(f"proximo_retry.is.null,proximo_retry.lte.{agora}") \
        .order("created_at") \
        .limit(limite) \
        .execute()

    return result.data


async def buscar_item_por_mensagem(mensagem_id: UUID) -> Optional[dict]:
    """
    Busca item da fila por ID da mensagem.

    Args:
        mensagem_id: ID da mensagem

    Returns:
        Item da fila ou None
    """
    result = supabase.table("fila_processamento_grupos") \
        .select("*") \
        .eq("mensagem_id", str(mensagem_id)) \
        .limit(1) \
        .execute()

    return result.data[0] if result.data else None


# =============================================================================
# S11.4 - Funções de Atualização
# =============================================================================

async def atualizar_estagio(
    item_id: UUID,
    novo_estagio: EstagioPipeline,
    erro: Optional[str] = None,
    vaga_grupo_id: Optional[UUID] = None
) -> None:
    """
    Atualiza estágio de um item na fila.

    Args:
        item_id: ID do item na fila
        novo_estagio: Novo estágio
        erro: Mensagem de erro (se houver)
        vaga_grupo_id: ID da vaga criada (se aplicável)
    """
    updates = {
        "estagio": novo_estagio.value,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    if vaga_grupo_id:
        updates["vaga_grupo_id"] = str(vaga_grupo_id)

    if erro:
        updates["ultimo_erro"] = erro[:500]  # Limitar tamanho

        # Buscar tentativas atuais
        result = supabase.table("fila_processamento_grupos") \
            .select("tentativas") \
            .eq("id", str(item_id)) \
            .single() \
            .execute()

        tentativas = (result.data.get("tentativas", 0) if result.data else 0) + 1
        updates["tentativas"] = tentativas

        # Calcular próximo retry (backoff exponencial)
        if tentativas < len(RETRY_DELAYS):
            delay_minutos = RETRY_DELAYS[tentativas - 1]
        else:
            delay_minutos = RETRY_DELAYS[-1]  # Usar último delay

        updates["proximo_retry"] = (
            datetime.now(UTC) + timedelta(minutes=delay_minutos)
        ).isoformat()

        logger.warning(f"Item {item_id} com erro, retry em {delay_minutos}min: {erro[:100]}")
    else:
        # Sucesso - limpar erro
        updates["ultimo_erro"] = None
        updates["proximo_retry"] = None

    supabase.table("fila_processamento_grupos") \
        .update(updates) \
        .eq("id", str(item_id)) \
        .execute()


async def marcar_como_finalizado(item_id: UUID) -> None:
    """Marca item como finalizado."""
    await atualizar_estagio(item_id, EstagioPipeline.FINALIZADO)


async def marcar_como_descartado(item_id: UUID, motivo: str) -> None:
    """Marca item como descartado."""
    supabase.table("fila_processamento_grupos") \
        .update({
            "estagio": EstagioPipeline.DESCARTADO.value,
            "ultimo_erro": f"descartado: {motivo}",
            "updated_at": datetime.now(UTC).isoformat(),
        }) \
        .eq("id", str(item_id)) \
        .execute()


# =============================================================================
# S11.5 - Funções de Estatísticas
# =============================================================================

async def obter_estatisticas_fila() -> dict:
    """
    Obtém estatísticas da fila de processamento.

    Returns:
        Estatísticas por estágio
    """
    stats = {}

    for estagio in EstagioPipeline:
        result = supabase.table("fila_processamento_grupos") \
            .select("id", count="exact") \
            .eq("estagio", estagio.value) \
            .execute()

        stats[estagio.value] = result.count or 0

    # Itens com erro (tentativas >= max)
    erros_max = supabase.table("fila_processamento_grupos") \
        .select("id", count="exact") \
        .gte("tentativas", 3) \
        .execute()

    stats["erros_max_tentativas"] = erros_max.count or 0

    return stats


async def obter_itens_travados(horas: int = 1) -> List[dict]:
    """
    Obtém itens que estão travados (muito tempo sem atualização).

    Args:
        horas: Limite de horas sem atualização

    Returns:
        Lista de itens travados
    """
    limite = (datetime.now(UTC) - timedelta(hours=horas)).isoformat()

    result = supabase.table("fila_processamento_grupos") \
        .select("id, mensagem_id, estagio, tentativas, ultimo_erro, updated_at") \
        .not_.in_("estagio", [
            EstagioPipeline.FINALIZADO.value,
            EstagioPipeline.DESCARTADO.value,
            EstagioPipeline.ERRO.value
        ]) \
        .lt("updated_at", limite) \
        .order("updated_at") \
        .limit(100) \
        .execute()

    return result.data


# =============================================================================
# S11.6 - Reprocessamento
# =============================================================================

async def reprocessar_erros(limite: int = 100) -> int:
    """
    Reenvia itens com erro para reprocessamento.

    Args:
        limite: Máximo de itens a reprocessar

    Returns:
        Quantidade de itens reprocessados
    """
    # Buscar itens com erro que ainda não atingiram max tentativas
    result = supabase.table("fila_processamento_grupos") \
        .select("id") \
        .eq("estagio", EstagioPipeline.ERRO.value) \
        .lt("tentativas", 3) \
        .limit(limite) \
        .execute()

    count = 0
    for item in result.data:
        supabase.table("fila_processamento_grupos") \
            .update({
                "estagio": EstagioPipeline.PENDENTE.value,
                "proximo_retry": None,
                "updated_at": datetime.now(UTC).isoformat(),
            }) \
            .eq("id", item["id"]) \
            .execute()
        count += 1

    logger.info(f"Reprocessados {count} itens com erro")
    return count


async def limpar_finalizados(dias: int = 7) -> int:
    """
    Remove itens finalizados antigos.

    Args:
        dias: Manter itens dos últimos N dias

    Returns:
        Quantidade de itens removidos
    """
    limite = (datetime.now(UTC) - timedelta(days=dias)).isoformat()

    result = supabase.table("fila_processamento_grupos") \
        .delete() \
        .in_("estagio", [
            EstagioPipeline.FINALIZADO.value,
            EstagioPipeline.DESCARTADO.value
        ]) \
        .lt("updated_at", limite) \
        .execute()

    count = len(result.data) if result.data else 0
    logger.info(f"Removidos {count} itens finalizados antigos")

    return count
