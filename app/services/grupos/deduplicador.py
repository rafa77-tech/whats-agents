"""
Deduplicação de vagas de grupos WhatsApp.

Sprint 14 - E08 - Deduplicação

A mesma vaga pode ser postada em múltiplos grupos.
Este módulo identifica duplicatas e agrupa fontes.
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID

from app.core.logging import get_logger
from app.services.supabase import supabase

logger = get_logger(__name__)


# Janela temporal para considerar duplicatas (em horas)
JANELA_DEDUP_HORAS = 48


# =============================================================================
# S08.1 - Cálculo de Hash de Deduplicação
# =============================================================================


def calcular_hash_dedup(
    hospital_id: UUID,
    data: Optional[str],  # YYYY-MM-DD
    periodo_id: Optional[UUID],
    especialidade_id: UUID,
) -> str:
    """
    Calcula hash para deduplicação.

    A chave de deduplicação é: hospital + data + período + especialidade

    Args:
        hospital_id: ID do hospital normalizado
        data: Data da vaga (YYYY-MM-DD)
        periodo_id: ID do período (opcional)
        especialidade_id: ID da especialidade normalizada

    Returns:
        Hash MD5 de 32 caracteres
    """
    componentes = [
        str(hospital_id),
        data or "sem_data",
        str(periodo_id) if periodo_id else "sem_periodo",
        str(especialidade_id),
    ]

    texto = "|".join(componentes)
    return hashlib.md5(texto.encode()).hexdigest()


# =============================================================================
# S08.2 - Verificar Duplicatas Existentes
# =============================================================================


async def buscar_vaga_duplicada(
    hash_dedup: str, excluir_id: Optional[UUID] = None
) -> Optional[dict]:
    """
    Busca vaga existente com mesmo hash na janela temporal.

    Args:
        hash_dedup: Hash calculado
        excluir_id: ID para excluir da busca (a própria vaga)

    Returns:
        Vaga existente ou None
    """
    limite_tempo = datetime.now(UTC) - timedelta(hours=JANELA_DEDUP_HORAS)

    query = (
        supabase.table("vagas_grupo")
        .select("id, qtd_fontes, hospital_raw, especialidade_raw")
        .eq("hash_dedup", hash_dedup)
        .eq("eh_duplicada", False)
        .gte("created_at", limite_tempo.isoformat())
    )

    if excluir_id:
        query = query.neq("id", str(excluir_id))

    result = query.order("created_at").limit(1).execute()

    return result.data[0] if result.data else None


# =============================================================================
# S08.3 - Registrar Fonte de Vaga
# =============================================================================


async def registrar_fonte_vaga(
    vaga_principal_id: UUID,
    mensagem_id: UUID,
    grupo_id: UUID,
    contato_id: Optional[UUID] = None,
    texto_original: str = "",
    valor_informado: Optional[int] = None,
) -> UUID:
    """
    Registra uma fonte adicional para a vaga.

    Cada vez que a mesma vaga aparece em outro grupo,
    registramos como uma fonte adicional.

    Args:
        vaga_principal_id: ID da vaga principal
        mensagem_id: ID da mensagem fonte
        grupo_id: ID do grupo onde apareceu
        contato_id: ID do contato que postou
        texto_original: Texto original da mensagem
        valor_informado: Valor se diferente do principal

    Returns:
        UUID da fonte criada
    """
    # Verificar se já existe esta fonte (evitar duplicatas)
    existente = (
        supabase.table("vagas_grupo_fontes")
        .select("id")
        .eq("vaga_grupo_id", str(vaga_principal_id))
        .eq("mensagem_id", str(mensagem_id))
        .limit(1)
        .execute()
    )

    if existente.data:
        return UUID(existente.data[0]["id"])

    # Contar fontes existentes para determinar ordem
    count_result = (
        supabase.table("vagas_grupo_fontes")
        .select("id", count="exact")
        .eq("vaga_grupo_id", str(vaga_principal_id))
        .execute()
    )

    ordem = (count_result.count or 0) + 1

    dados = {
        "vaga_grupo_id": str(vaga_principal_id),
        "mensagem_id": str(mensagem_id),
        "grupo_id": str(grupo_id),
        "contato_id": str(contato_id) if contato_id else None,
        "ordem": ordem,
        "texto_original": texto_original[:500] if texto_original else None,
        "valor_informado": valor_informado,
    }

    result = supabase.table("vagas_grupo_fontes").insert(dados).execute()

    # Atualizar contador na vaga principal
    supabase.table("vagas_grupo").update({"qtd_fontes": ordem}).eq(
        "id", str(vaga_principal_id)
    ).execute()

    logger.debug(f"Fonte {ordem} registrada para vaga {vaga_principal_id}")

    return UUID(result.data[0]["id"])


# =============================================================================
# S08.4 - Marcar Vaga como Duplicada
# =============================================================================


async def marcar_como_duplicada(vaga_id: UUID, duplicada_de: UUID) -> None:
    """
    Marca vaga como duplicada de outra.

    Args:
        vaga_id: ID da vaga duplicada
        duplicada_de: ID da vaga principal
    """
    supabase.table("vagas_grupo").update(
        {
            "status": "duplicada",
            "eh_duplicada": True,
            "duplicada_de": str(duplicada_de),
            "motivo_status": "duplicata_detectada",
        }
    ).eq("id", str(vaga_id)).execute()

    logger.debug(f"Vaga {vaga_id} marcada como duplicada de {duplicada_de}")


# =============================================================================
# S08.5 - Processador de Deduplicação
# =============================================================================


@dataclass
class ResultadoDedup:
    """Resultado do processamento de deduplicação."""

    duplicada: bool
    principal_id: Optional[UUID] = None
    hash_dedup: Optional[str] = None
    erro: Optional[str] = None


async def processar_deduplicacao(vaga_id: UUID) -> ResultadoDedup:
    """
    Processa deduplicação para uma vaga.

    Usa RPC com advisory lock para garantir atomicidade (evita race condition
    quando vagas com mesmo hash chegam no mesmo ciclo do worker).

    Args:
        vaga_id: ID da vaga a processar

    Returns:
        ResultadoDedup com status da deduplicação
    """
    # Buscar vaga
    vaga = supabase.table("vagas_grupo").select("*").eq("id", str(vaga_id)).single().execute()

    if not vaga.data:
        return ResultadoDedup(duplicada=False, erro="vaga_nao_encontrada")

    dados = vaga.data

    # Verificar se tem dados para hash
    if not dados.get("hospital_id") or not dados.get("especialidade_id"):
        return ResultadoDedup(duplicada=False, erro="dados_insuficientes")

    # Calcular hash
    hash_dedup = calcular_hash_dedup(
        hospital_id=UUID(dados["hospital_id"]),
        data=dados.get("data"),
        periodo_id=UUID(dados["periodo_id"]) if dados.get("periodo_id") else None,
        especialidade_id=UUID(dados["especialidade_id"]),
    )

    # Deduplicação atômica via RPC (advisory lock no banco)
    result = supabase.rpc(
        "dedup_vaga_grupo",
        {"p_vaga_id": str(vaga_id), "p_hash": hash_dedup},
    ).execute()

    if not result.data:
        return ResultadoDedup(duplicada=False, erro="rpc_sem_resultado")

    row = result.data[0]
    duplicada = row["eh_duplicada"]
    principal_id = UUID(row["principal_id"]) if row.get("principal_id") else None

    # Registrar fonte (tracking multi-grupo)
    if duplicada and principal_id:
        await registrar_fonte_vaga(
            vaga_principal_id=principal_id,
            mensagem_id=UUID(dados["mensagem_id"]),
            grupo_id=UUID(dados["grupo_origem_id"]),
            contato_id=UUID(dados["contato_responsavel_id"])
            if dados.get("contato_responsavel_id")
            else None,
            valor_informado=dados.get("valor"),
        )
        logger.info(f"Vaga {vaga_id} é duplicata de {principal_id}")
    else:
        # Registrar como fonte principal (primeira)
        await registrar_fonte_vaga(
            vaga_principal_id=vaga_id,
            mensagem_id=UUID(dados["mensagem_id"]),
            grupo_id=UUID(dados["grupo_origem_id"]),
            contato_id=UUID(dados["contato_responsavel_id"])
            if dados.get("contato_responsavel_id")
            else None,
            valor_informado=dados.get("valor"),
        )
        logger.debug(f"Vaga {vaga_id} processada - nova (não duplicata)")

    return ResultadoDedup(
        duplicada=duplicada,
        principal_id=principal_id,
        hash_dedup=hash_dedup,
    )


# =============================================================================
# Funções de Consulta
# =============================================================================


async def listar_fontes_vaga(vaga_id: UUID) -> list:
    """
    Lista todas as fontes de uma vaga.

    Args:
        vaga_id: ID da vaga principal

    Returns:
        Lista de fontes ordenadas
    """
    result = (
        supabase.table("vagas_grupo_fontes")
        .select("*, grupos_whatsapp(nome), contatos_grupo(nome)")
        .eq("vaga_grupo_id", str(vaga_id))
        .order("ordem")
        .execute()
    )

    return result.data


async def obter_estatisticas_dedup() -> dict:
    """
    Obtém estatísticas de deduplicação.

    Returns:
        Estatísticas gerais
    """
    # Total de vagas
    total = supabase.table("vagas_grupo").select("id", count="exact").execute()

    # Vagas únicas (não duplicadas)
    unicas = (
        supabase.table("vagas_grupo")
        .select("id", count="exact")
        .eq("eh_duplicada", False)
        .execute()
    )

    # Vagas duplicadas
    duplicadas = (
        supabase.table("vagas_grupo").select("id", count="exact").eq("eh_duplicada", True).execute()
    )

    # Vagas com múltiplas fontes
    multi_fonte = (
        supabase.table("vagas_grupo").select("id", count="exact").gt("qtd_fontes", 1).execute()
    )

    return {
        "total_vagas": total.count or 0,
        "vagas_unicas": unicas.count or 0,
        "vagas_duplicadas": duplicadas.count or 0,
        "vagas_multi_fonte": multi_fonte.count or 0,
        "taxa_duplicacao": ((duplicadas.count or 0) / (total.count or 1) * 100),
    }
