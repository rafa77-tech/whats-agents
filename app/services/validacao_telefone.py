"""
Serviço de validação de telefones via Evolution API.

Sprint 32 E04 - Validação prévia evita desperdício de mensagens.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.services.supabase import supabase
from app.services.whatsapp import evolution

logger = logging.getLogger(__name__)


async def buscar_telefones_pendentes(limit: int = 100) -> list[dict]:
    """
    Busca médicos com telefone pendente de validação.

    Args:
        limit: Máximo de registros a retornar

    Returns:
        Lista de dicts com id e telefone
    """
    response = (
        supabase.table("clientes")
        .select("id, telefone, nome")
        .eq("status_telefone", "pendente")
        .not_.is_("telefone", "null")
        .limit(limit)
        .execute()
    )

    return response.data or []


async def marcar_como_validando(cliente_id: str) -> bool:
    """
    Marca cliente como 'validando' para evitar processamento duplicado.

    Args:
        cliente_id: ID do cliente

    Returns:
        True se marcou, False se já estava em outro estado
    """
    try:
        response = (
            supabase.table("clientes")
            .update({"status_telefone": "validando"})
            .eq("id", cliente_id)
            .eq("status_telefone", "pendente")  # Só atualiza se ainda pendente
            .execute()
        )

        # Se não atualizou nenhum registro, já estava em outro estado
        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao marcar como validando: {e}")
        return False


async def atualizar_status_telefone(
    cliente_id: str, status: str, erro: Optional[str] = None
) -> bool:
    """
    Atualiza status do telefone após validação.

    Args:
        cliente_id: ID do cliente
        status: validado | invalido | erro
        erro: Mensagem de erro (se aplicável)

    Returns:
        True se atualizou
    """
    try:
        dados = {
            "status_telefone": status,
            "telefone_validado_em": datetime.now(timezone.utc).isoformat(),
        }

        if erro:
            dados["telefone_erro"] = erro[:500]  # Limitar tamanho

        response = supabase.table("clientes").update(dados).eq("id", cliente_id).execute()

        return len(response.data or []) > 0

    except Exception as e:
        logger.error(f"Erro ao atualizar status telefone: {e}")
        return False


async def validar_telefone(cliente_id: str, telefone: str) -> str:
    """
    Valida um telefone específico via Evolution API.

    Args:
        cliente_id: ID do cliente
        telefone: Número a validar

    Returns:
        Status final: validado | invalido | erro | skip
    """
    # Marcar como validando
    if not await marcar_como_validando(cliente_id):
        logger.debug(f"Cliente {cliente_id} já em processamento")
        return "skip"

    try:
        # Chamar Evolution API
        resultado = await evolution.check_number_status(telefone)

        if resultado.get("exists"):
            await atualizar_status_telefone(cliente_id, "validado")
            logger.debug(f"Telefone {telefone} validado - WhatsApp existe")
            return "validado"

        elif resultado.get("error"):
            # Erro de API - tentar novamente depois
            await atualizar_status_telefone(cliente_id, "erro", erro=resultado.get("error"))
            logger.warning(f"Erro ao validar {telefone}: {resultado.get('error')}")
            return "erro"

        else:
            # WhatsApp não existe
            await atualizar_status_telefone(cliente_id, "invalido")
            logger.debug(f"Telefone {telefone} inválido - WhatsApp não existe")
            return "invalido"

    except Exception as e:
        await atualizar_status_telefone(cliente_id, "erro", erro=str(e))
        logger.error(f"Exceção ao validar {telefone}: {e}")
        return "erro"


async def processar_lote_validacao(limit: int = 50) -> dict:
    """
    Processa um lote de telefones pendentes.

    Args:
        limit: Máximo de telefones a processar

    Returns:
        Dict com estatísticas do processamento
    """
    stats = {
        "processados": 0,
        "validados": 0,
        "invalidos": 0,
        "erros": 0,
        "skips": 0,
    }

    pendentes = await buscar_telefones_pendentes(limit)

    if not pendentes:
        logger.debug("Nenhum telefone pendente para validar")
        return stats

    logger.info(f"Processando {len(pendentes)} telefones pendentes")

    for cliente in pendentes:
        resultado = await validar_telefone(cliente["id"], cliente["telefone"])

        stats["processados"] += 1

        if resultado == "validado":
            stats["validados"] += 1
        elif resultado == "invalido":
            stats["invalidos"] += 1
        elif resultado == "erro":
            stats["erros"] += 1
        elif resultado == "skip":
            stats["skips"] += 1

    logger.info(
        f"Validação concluída: {stats['validados']} válidos, "
        f"{stats['invalidos']} inválidos, {stats['erros']} erros"
    )

    return stats


async def obter_estatisticas_validacao() -> dict:
    """
    Retorna estatísticas de validação de telefones.

    Returns:
        Dict com contagens por status
    """
    try:
        # Query agregada por status via RPC
        response = supabase.rpc("count_by_status_telefone").execute()

        if response.data:
            # Converter lista para dict
            return {item["status"]: item["count"] for item in response.data}

        # Fallback: queries separadas
        stats = {}
        for status in ["pendente", "validando", "validado", "invalido", "erro"]:
            count = (
                supabase.table("clientes")
                .select("id", count="exact")
                .eq("status_telefone", status)
                .execute()
            )
            stats[status] = count.count or 0

        return stats

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}


async def resetar_telefones_travados(horas: int = 1) -> int:
    """
    Reseta telefones que ficaram travados em 'validando'.

    Útil para casos onde o processo foi interrompido.

    Args:
        horas: Quantas horas atrás considerar como travado

    Returns:
        Número de registros resetados
    """
    try:
        from datetime import timedelta

        limite = datetime.now(timezone.utc) - timedelta(hours=horas)

        response = (
            supabase.table("clientes")
            .update({"status_telefone": "pendente"})
            .eq("status_telefone", "validando")
            .lt("updated_at", limite.isoformat())
            .execute()
        )

        count = len(response.data or [])
        if count > 0:
            logger.warning(f"Resetados {count} telefones travados em 'validando'")

        return count

    except Exception as e:
        logger.error(f"Erro ao resetar telefones travados: {e}")
        return 0
