"""
Sistema de matching de preferencias do medico.

Sprint 10 - S10.E3.2
"""

import logging

logger = logging.getLogger(__name__)


def filtrar_por_preferencias(vagas: list[dict], preferencias: dict) -> list[dict]:
    """
    Remove vagas incompativeis com preferencias do medico.

    Args:
        vagas: Lista de vagas do banco
        preferencias: Dict com hospitais_bloqueados, setores_bloqueados, valor_minimo

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


def ordenar_por_regiao(vagas: list[dict], regiao_medico: str) -> list[dict]:
    """
    Ordena vagas priorizando regiao do medico.

    Args:
        vagas: Lista de vagas
        regiao_medico: Regiao do medico

    Returns:
        Lista ordenada (vagas da regiao primeiro)
    """
    if not regiao_medico:
        return vagas

    def prioridade_regiao(vaga):
        hospital = vaga.get("hospitais", {})
        hospital_regiao = hospital.get("regiao")
        if hospital_regiao == regiao_medico:
            return 0  # Alta prioridade
        return 1

    return sorted(vagas, key=prioridade_regiao)
