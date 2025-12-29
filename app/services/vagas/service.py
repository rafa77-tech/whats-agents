"""
Service principal de vagas.

Sprint 10 - S10.E3.2
Sprint 17 - E01: Adicao de status 'realizada'
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config.regioes import detectar_regiao_por_telefone
from app.services.supabase import supabase
from . import repository, cache, preferencias

logger = logging.getLogger(__name__)


# Status validos para transicao para 'realizada'
# Inclui 'fechada' por compatibilidade com registros legados
STATUS_VALIDOS_PARA_REALIZADA = ("reservada", "fechada")


async def buscar_vagas_compativeis(
    especialidade_id: str = None,
    cliente_id: str = None,
    medico: dict = None,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas compativeis com o medico.

    Args:
        especialidade_id: ID da especialidade
        cliente_id: ID do medico
        medico: Dados completos do medico
        limite: Maximo de vagas a retornar

    Returns:
        Lista de vagas ordenadas
    """
    # Obter especialidade_id do medico se nao fornecido
    if medico and not especialidade_id:
        especialidade_id = medico.get("especialidade_id")

    if not especialidade_id:
        logger.warning("Nenhuma especialidade fornecida para buscar vagas")
        return []

    # Tentar cache primeiro
    cached = await cache.get_cached(especialidade_id, limite)
    if cached:
        if medico:
            prefs = medico.get("preferencias_detectadas") or {}
            cached = preferencias.filtrar_por_preferencias(cached, prefs)
        return cached[:limite]

    # Buscar do banco
    vagas = await repository.listar_disponiveis(especialidade_id, limite * 2)

    # Aplicar filtros de preferencias
    if medico:
        prefs = medico.get("preferencias_detectadas") or {}
        vagas = preferencias.filtrar_por_preferencias(vagas, prefs)

    vagas_finais = vagas[:limite]

    # Salvar no cache
    await cache.set_cached(especialidade_id, limite, vagas_finais)

    return vagas_finais


async def buscar_vagas_por_regiao(medico: dict, limite: int = 5) -> list[dict]:
    """
    Busca vagas priorizando regiao do medico.

    Args:
        medico: Dados do medico
        limite: Maximo de vagas a retornar

    Returns:
        Lista ordenada por prioridade de regiao
    """
    vagas = await buscar_vagas_compativeis(medico=medico, limite=limite * 2)

    telefone = medico.get("telefone", "")
    regiao_medico = detectar_regiao_por_telefone(telefone)

    if not regiao_medico:
        return vagas[:limite]

    vagas_ordenadas = preferencias.ordenar_por_regiao(vagas, regiao_medico)
    return vagas_ordenadas[:limite]


async def reservar_vaga(
    vaga_id: str,
    cliente_id: str,
    medico: dict = None,
    notificar_gestor: bool = True
) -> dict:
    """
    Reserva vaga para o medico.

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do medico
        medico: Dados do medico (para notificacao)
        notificar_gestor: Se deve notificar via Slack

    Returns:
        Dados da vaga atualizada

    Raises:
        ValueError: Se vaga nao disponivel ou ha conflito
    """
    # Buscar vaga
    vaga = await repository.buscar_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    # Verificar disponibilidade
    if vaga["status"] != "aberta":
        raise ValueError(f"Vaga nao esta mais disponivel (status: {vaga['status']})")

    # Verificar conflito
    if vaga.get("periodo_id"):
        conflito = await repository.verificar_conflito(
            cliente_id=cliente_id,
            data=vaga["data"],
            periodo_id=vaga["periodo_id"]
        )
        if conflito["conflito"]:
            raise ValueError("Voce ja tem um plantao neste dia e periodo")

    # Reservar
    vaga_atualizada = await repository.reservar(vaga_id, cliente_id)
    if not vaga_atualizada:
        raise ValueError("Vaga foi reservada por outro medico")

    # Invalidar cache
    if vaga.get("especialidade_id"):
        await cache.invalidar(vaga["especialidade_id"])

    # Notificar gestor
    if notificar_gestor and medico:
        try:
            from app.services.slack import notificar_plantao_reservado
            await notificar_plantao_reservado(medico, vaga)
        except Exception as e:
            logger.error(f"Erro ao notificar Slack: {e}")

    return vaga_atualizada


async def cancelar_reserva(vaga_id: str, cliente_id: str) -> dict:
    """
    Cancela reserva de uma vaga.

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do medico

    Returns:
        Vaga atualizada

    Raises:
        ValueError: Se vaga nao pertence ao medico
    """
    vaga = await repository.buscar_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    if vaga.get("cliente_id") != cliente_id:
        raise ValueError("Vaga nao pertence a este medico")

    if vaga["status"] not in ["reservada"]:
        raise ValueError(f"Vaga nao pode ser cancelada (status: {vaga['status']})")

    resultado = await repository.cancelar_reserva(vaga_id)
    logger.info(f"Reserva da vaga {vaga_id} cancelada pelo medico {cliente_id}")

    return resultado


async def marcar_vaga_realizada(
    vaga_id: str,
    realizada_por: str = "ops",
) -> bool:
    """
    Marca uma vaga como realizada (plantao executado).

    Aceita vagas com status 'reservada' ou 'fechada' (legado).

    Sprint 17 - E01.3

    Args:
        vaga_id: UUID da vaga
        realizada_por: Quem esta marcando (user_id ou "ops")

    Returns:
        True se sucesso

    Raises:
        ValueError: Se vaga nao existe ou status invalido
    """
    # Buscar vaga atual
    response = (
        supabase.table("vagas")
        .select("id, status")
        .eq("id", vaga_id)
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise ValueError(f"Vaga nao encontrada: {vaga_id}")

    status_atual = response.data["status"]

    # Aceita 'reservada' (novo) ou 'fechada' (legado)
    if status_atual not in STATUS_VALIDOS_PARA_REALIZADA:
        raise ValueError(
            f"Vaga deve estar reservada ou fechada para ser realizada. "
            f"Status atual: {status_atual}"
        )

    # Atualizar para 'realizada'
    supabase.table("vagas").update({
        "status": "realizada",
        "realizada_em": datetime.now(timezone.utc).isoformat(),
        "realizada_por": realizada_por,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", vaga_id).execute()

    logger.info(
        f"Vaga {vaga_id} marcada como realizada por {realizada_por} "
        f"(status anterior: {status_atual})"
    )
    return True
