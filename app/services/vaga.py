"""
Servico de gestao de vagas.
"""
from datetime import date, datetime, timezone
from typing import Optional
import logging

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def buscar_vagas_compativeis(
    especialidade_id: str,
    cliente_id: str = None,
    limite: int = 5
) -> list[dict]:
    """
    Busca vagas compativeis com o medico.

    Filtros:
    - Especialidade do medico
    - Status = aberta
    - Data >= hoje
    - Nao oferece vaga ja reservada pelo mesmo medico

    Ordenacao:
    - Data mais proxima primeiro

    Args:
        especialidade_id: ID da especialidade do medico
        cliente_id: ID do medico (para excluir vagas dele)
        limite: Maximo de vagas a retornar

    Returns:
        Lista de vagas com dados de hospital, periodo e setor
    """
    hoje = date.today().isoformat()

    query = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("especialidade_id", especialidade_id)
        .eq("status", "aberta")
        .gte("data", hoje)
        .is_("deleted_at", "null")
        .order("data")
        .limit(limite)
    )

    response = query.execute()
    vagas = response.data or []

    logger.info(f"Encontradas {len(vagas)} vagas para especialidade {especialidade_id}")

    return vagas


def filtrar_por_preferencias(vagas: list[dict], preferencias: dict) -> list[dict]:
    """
    Remove vagas incompativeis com preferencias do medico.

    Args:
        vagas: Lista de vagas do banco
        preferencias: Dict com preferencias (hospitais_bloqueados, setores_bloqueados, valor_minimo)

    Returns:
        Lista filtrada de vagas
    """
    if not preferencias:
        return vagas

    resultado = []

    hospitais_bloqueados = preferencias.get("hospitais_bloqueados", [])
    setores_bloqueados = preferencias.get("setores_bloqueados", [])
    valor_minimo = preferencias.get("valor_minimo", 0)

    for v in vagas:
        # Pular hospital bloqueado
        if v.get("hospital_id") in hospitais_bloqueados:
            logger.debug(f"Vaga {v['id']} ignorada: hospital bloqueado")
            continue

        # Pular setor bloqueado
        if v.get("setor_id") in setores_bloqueados:
            logger.debug(f"Vaga {v['id']} ignorada: setor bloqueado")
            continue

        # Pular se valor abaixo do minimo
        valor = v.get("valor") or 0
        if valor < valor_minimo:
            logger.debug(f"Vaga {v['id']} ignorada: valor {valor} < {valor_minimo}")
            continue

        resultado.append(v)

    logger.info(f"Filtro de preferencias: {len(vagas)} -> {len(resultado)} vagas")

    return resultado


async def buscar_vaga_por_id(vaga_id: str) -> dict | None:
    """
    Busca vaga pelo ID com dados relacionados.

    Args:
        vaga_id: ID da vaga

    Returns:
        Dados da vaga ou None
    """
    response = (
        supabase.table("vagas")
        .select("*, hospitais(*), periodos(*), setores(*), especialidades(*)")
        .eq("id", vaga_id)
        .is_("deleted_at", "null")
        .execute()
    )
    return response.data[0] if response.data else None


async def verificar_conflito(
    cliente_id: str,
    data: str,
    periodo_id: str
) -> bool:
    """
    Verifica se medico ja tem plantao no mesmo dia/periodo.

    Args:
        cliente_id: ID do medico
        data: Data do plantao (YYYY-MM-DD)
        periodo_id: ID do periodo

    Returns:
        True se ha conflito, False se pode agendar
    """
    response = (
        supabase.table("vagas")
        .select("id")
        .eq("cliente_id", cliente_id)
        .eq("data", data)
        .eq("periodo_id", periodo_id)
        .in_("status", ["reservada", "confirmada"])
        .is_("deleted_at", "null")
        .execute()
    )

    tem_conflito = len(response.data) > 0

    if tem_conflito:
        logger.info(f"Conflito encontrado: medico {cliente_id} ja tem plantao em {data}")

    return tem_conflito


async def reservar_vaga(
    vaga_id: str,
    cliente_id: str,
    medico: dict = None,
    notificar_gestor: bool = True
) -> dict:
    """
    Reserva vaga para o medico.

    1. Verificar se vaga ainda esta aberta
    2. Verificar conflito de horario
    3. Atualizar status para 'reservada'
    4. Associar cliente_id
    5. Notificar gestor via Slack
    6. Retornar vaga atualizada

    Args:
        vaga_id: ID da vaga
        cliente_id: ID do medico
        medico: Dados do medico (para notificacao)
        notificar_gestor: Se deve notificar gestor via Slack

    Returns:
        Dados da vaga atualizada

    Raises:
        ValueError: Se vaga nao disponivel ou ha conflito
    """
    # Buscar vaga
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    # Verificar disponibilidade
    if vaga["status"] != "aberta":
        raise ValueError(f"Vaga nao esta mais disponivel (status: {vaga['status']})")

    # Verificar conflito
    if vaga.get("periodo_id"):
        conflito = await verificar_conflito(
            cliente_id=cliente_id,
            data=vaga["data"],
            periodo_id=vaga["periodo_id"]
        )
        if conflito:
            raise ValueError("Voce ja tem um plantao neste dia e periodo")

    # Reservar
    response = (
        supabase.table("vagas")
        .update({
            "status": "reservada",
            "cliente_id": cliente_id,
            "fechada_em": datetime.now(timezone.utc).isoformat(),
            "fechada_por": "julia",
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .eq("status", "aberta")  # Optimistic locking
        .execute()
    )

    if not response.data:
        raise ValueError("Vaga foi reservada por outro medico")

    vaga_atualizada = response.data[0]
    logger.info(f"Vaga {vaga_id} reservada para medico {cliente_id}")

    # Notificar gestor via Slack
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
        cliente_id: ID do medico (para verificar propriedade)

    Returns:
        Vaga atualizada

    Raises:
        ValueError: Se vaga nao pertence ao medico
    """
    vaga = await buscar_vaga_por_id(vaga_id)
    if not vaga:
        raise ValueError("Vaga nao encontrada")

    if vaga.get("cliente_id") != cliente_id:
        raise ValueError("Vaga nao pertence a este medico")

    if vaga["status"] not in ["reservada"]:
        raise ValueError(f"Vaga nao pode ser cancelada (status: {vaga['status']})")

    response = (
        supabase.table("vagas")
        .update({
            "status": "aberta",
            "cliente_id": None,
            "fechada_em": None,
            "fechada_por": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        .eq("id", vaga_id)
        .execute()
    )

    logger.info(f"Reserva da vaga {vaga_id} cancelada pelo medico {cliente_id}")

    return response.data[0] if response.data else None


def formatar_vaga_para_mensagem(vaga: dict) -> str:
    """
    Formata vaga para mensagem natural da Julia.

    Args:
        vaga: Dados da vaga com relacionamentos

    Returns:
        String formatada para mensagem
    """
    hospital = vaga.get("hospitais", {}).get("nome", "Hospital")
    data = vaga.get("data", "")
    periodo = vaga.get("periodos", {}).get("nome", "")
    valor = vaga.get("valor") or 0
    setor = vaga.get("setores", {}).get("nome", "")

    # Formatar data para PT-BR
    if data:
        try:
            data_obj = datetime.strptime(data, "%Y-%m-%d")
            dias_semana = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
            dia_semana = dias_semana[data_obj.weekday()]
            data = f"{dia_semana}, {data_obj.strftime('%d/%m')}"
        except ValueError:
            pass

    partes = [hospital]
    if data:
        partes.append(data)
    if periodo:
        partes.append(periodo.lower())
    if setor:
        partes.append(setor)
    if valor:
        partes.append(f"R$ {valor:,.0f}".replace(",", "."))

    return ", ".join(partes)
