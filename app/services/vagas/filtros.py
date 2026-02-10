"""
Filtros adicionais para vagas.

Sprint 31 - S31.E5.2

Filtros de período e dias da semana extraídos do handler
para reutilização e testabilidade.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# Mapeamento de períodos
MAPEAMENTO_PERIODOS = {
    "diurno": ["diurno", "dia", "manha", "tarde", "meio período (manhã)"],
    "noturno": ["noturno", "noite", "cinderela"],
    "vespertino": ["vespertino", "tarde", "meio período (tarde)"],
    "12h": ["12h", "12 horas"],
    "24h": ["24h", "24 horas"],
}

# Mapeamento de dias da semana
DIAS_SEMANA_MAP = {
    "segunda": 0,
    "seg": 0,
    "terca": 1,
    "ter": 1,
    "quarta": 2,
    "qua": 2,
    "quinta": 3,
    "qui": 3,
    "sexta": 4,
    "sex": 4,
    "sabado": 5,
    "sab": 5,
    "domingo": 6,
    "dom": 6,
}


def filtrar_por_periodo(vagas: list[dict], periodo_desejado: str) -> tuple[list[dict], int]:
    """
    Filtra vagas por tipo de período.

    Args:
        vagas: Lista de vagas
        periodo_desejado: 'diurno', 'noturno', '12h', '24h'

    Returns:
        Tupla (vagas_filtradas, total_antes_filtro)
    """
    termos = MAPEAMENTO_PERIODOS.get(periodo_desejado.lower(), [periodo_desejado.lower()])
    total_antes = len(vagas)

    resultado = []
    for v in vagas:
        periodo_nome = ((v.get("periodos") or {}).get("nome") or "").lower()
        if any(termo in periodo_nome for termo in termos):
            resultado.append(v)

    if not resultado and total_antes > 0:
        logger.info(
            f"Filtro de período '{periodo_desejado}' não encontrou vagas "
            f"(havia {total_antes} antes do filtro)"
        )

    return resultado, total_antes


def filtrar_por_dias_semana(vagas: list[dict], dias_desejados: list[str]) -> tuple[list[dict], int]:
    """
    Filtra vagas por dias da semana.

    Args:
        vagas: Lista de vagas
        dias_desejados: Lista de dias (ex: ['segunda', 'terca'])

    Returns:
        Tupla (vagas_filtradas, total_antes_filtro)
    """
    total_antes = len(vagas)

    # Converter dias para índices
    dias_indices = set()
    for d in dias_desejados:
        d_lower = d.lower().replace("ç", "c").replace("-feira", "")
        if d_lower in DIAS_SEMANA_MAP:
            dias_indices.add(DIAS_SEMANA_MAP[d_lower])

    if not dias_indices:
        return vagas, total_antes

    resultado = []
    for v in vagas:
        data_str = v.get("data")
        if data_str:
            try:
                data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                if data_obj.weekday() in dias_indices:
                    resultado.append(v)
            except ValueError:
                logger.debug(f"Vaga com data inválida ignorada: {data_str}")
        # Vagas sem data não são incluídas

    if not resultado and total_antes > 0:
        logger.info(
            f"Filtro de dias '{dias_desejados}' não encontrou vagas "
            f"(havia {total_antes} antes do filtro)"
        )

    return resultado, total_antes


async def filtrar_por_conflitos(
    vagas: list[dict], medico_id: str, verificar_conflito_fn
) -> list[dict]:
    """
    Filtra vagas que conflitam com reservas existentes.

    Args:
        vagas: Lista de vagas
        medico_id: ID do médico
        verificar_conflito_fn: Função async para verificar conflito

    Returns:
        Lista de vagas sem conflito
    """
    vagas_sem_conflito = []

    for vaga in vagas:
        data = vaga.get("data")
        periodo_id = vaga.get("periodo_id")

        if data and periodo_id:
            tem_conflito = await verificar_conflito_fn(
                cliente_id=medico_id, data=data, periodo_id=periodo_id
            )
            if not tem_conflito:
                vagas_sem_conflito.append(vaga)
            else:
                logger.debug(f"Vaga {vaga['id']} filtrada: conflito de horário")
        else:
            vagas_sem_conflito.append(vaga)

    return vagas_sem_conflito


def aplicar_filtros(
    vagas: list[dict], periodo: Optional[str] = None, dias_semana: Optional[list[str]] = None
) -> tuple[list[dict], list[str]]:
    """
    Aplica múltiplos filtros às vagas.

    Args:
        vagas: Lista de vagas
        periodo: Período desejado (opcional)
        dias_semana: Dias da semana (opcional)

    Returns:
        Tupla (vagas_filtradas, lista_de_filtros_aplicados)
    """
    filtros_aplicados = []

    # Filtrar por período
    if periodo and periodo != "qualquer":
        total_antes = len(vagas)
        vagas, _ = filtrar_por_periodo(vagas, periodo)
        if len(vagas) < total_antes:
            filtros_aplicados.append(f"período {periodo}")

    # Filtrar por dias da semana
    if dias_semana:
        total_antes = len(vagas)
        vagas, _ = filtrar_por_dias_semana(vagas, dias_semana)
        if len(vagas) < total_antes:
            filtros_aplicados.append(f"dias {', '.join(dias_semana)}")

    return vagas, filtros_aplicados
