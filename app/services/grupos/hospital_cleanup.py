"""
Limpeza e merge de hospitais.

Sprint 60 - Épico 3: Limpeza de dados existentes.
"""

from typing import Optional

from app.core.logging import get_logger
from app.services.grupos.hospital_validator import validar_nome_hospital
from app.services.supabase import supabase
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event

logger = get_logger(__name__)


async def mesclar_hospitais(
    principal_id: str, duplicado_id: str, executado_por: str = "system"
) -> Optional[dict]:
    """
    Merge de hospital duplicado no principal via RPC atômica.

    Args:
        principal_id: UUID do hospital que permanece
        duplicado_id: UUID do hospital que será absorvido e deletado
        executado_por: Identificador de quem executou

    Returns:
        Dict com contagens de registros migrados, ou None em caso de erro
    """
    try:
        result = supabase.rpc(
            "mesclar_hospitais",
            {
                "p_principal_id": principal_id,
                "p_duplicado_id": duplicado_id,
                "p_executado_por": executado_por,
            },
        ).execute()

        if result.data:
            logger.info(
                "Hospital merge concluido",
                extra={
                    "principal_id": principal_id,
                    "duplicado_id": duplicado_id,
                    "resultado": result.data,
                },
            )
            try:
                await emit_event(
                    BusinessEvent(
                        event_type=EventType.HOSPITAL_MERGED,
                        source=EventSource.SYSTEM,
                        hospital_id=principal_id,
                        event_props={
                            "duplicado_id": duplicado_id,
                            "executado_por": executado_por,
                            "resultado": result.data if isinstance(result.data, dict) else {},
                        },
                    )
                )
            except Exception as e:
                logger.warning(f"Erro ao emitir evento de merge: {e}")
            return result.data
        return None
    except Exception as e:
        logger.error(
            "Erro ao mesclar hospitais",
            extra={
                "principal_id": principal_id,
                "duplicado_id": duplicado_id,
                "erro": str(e),
            },
        )
        raise


async def deletar_hospital_seguro(hospital_id: str) -> bool:
    """
    Deleta hospital somente se não tem referências em nenhuma tabela FK.

    Args:
        hospital_id: UUID do hospital

    Returns:
        True se deletado, False se tem referências
    """
    try:
        result = supabase.rpc(
            "deletar_hospital_sem_referencias",
            {"p_hospital_id": hospital_id},
        ).execute()

        deletado = result.data is True
        if deletado:
            logger.info(
                "Hospital deletado (sem referencias)",
                extra={"hospital_id": hospital_id},
            )
        return deletado
    except Exception as e:
        logger.error(
            "Erro ao deletar hospital",
            extra={"hospital_id": hospital_id, "erro": str(e)},
        )
        return False


async def listar_candidatos_limpeza_tier1(limite: int = 500) -> list:
    """
    Lista hospitais candidatos a auto-delete (Tier 1).

    Critério: criado_automaticamente=true, precisa_revisao=true,
    e nome falha no validador (blocklist).

    Returns:
        Lista de dicts com id e nome dos candidatos
    """
    result = (
        supabase.table("hospitais")
        .select("id, nome")
        .eq("criado_automaticamente", True)
        .eq("precisa_revisao", True)
        .limit(limite)
        .execute()
    )

    candidatos = []
    for hospital in result.data or []:
        validacao = validar_nome_hospital(hospital["nome"])
        if not validacao.valido:
            candidatos.append(hospital)

    logger.info(
        "Candidatos tier 1 identificados",
        extra={"total_verificados": len(result.data or []), "candidatos": len(candidatos)},
    )
    return candidatos


async def executar_limpeza_tier1(limite: int = 200) -> dict:
    """
    Executa limpeza automática Tier 1: deleta hospitais sem referências
    cujos nomes falham na validação.

    Returns:
        Dict com contagens: candidatos, deletados, falhas
    """
    candidatos = await listar_candidatos_limpeza_tier1(limite=limite)
    deletados = 0
    falhas = 0

    for hospital in candidatos:
        try:
            sucesso = await deletar_hospital_seguro(hospital["id"])
            if sucesso:
                deletados += 1
                try:
                    await emit_event(
                        BusinessEvent(
                            event_type=EventType.HOSPITAL_CLEANED,
                            source=EventSource.SYSTEM,
                            hospital_id=hospital["id"],
                            event_props={"nome": hospital["nome"], "tier": "tier1_auto"},
                        )
                    )
                except Exception:
                    pass  # Evento é best-effort
            else:
                falhas += 1  # Tem referências, não pode deletar
        except Exception as e:
            logger.warning(f"Erro ao deletar hospital {hospital['id']}: {e}")
            falhas += 1

    logger.info(
        "Limpeza tier 1 concluida",
        extra={"candidatos": len(candidatos), "deletados": deletados, "falhas": falhas},
    )
    return {"candidatos": len(candidatos), "deletados": deletados, "falhas": falhas}
