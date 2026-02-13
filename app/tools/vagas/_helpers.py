"""
Funcoes auxiliares compartilhadas pelas tools de vagas.

Sprint 58 - E5: Extraido de vagas.py monolitico.

Inclui helpers ativos e wrappers deprecated para compatibilidade.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers ativos
# =============================================================================


def _limpar_especialidade_input(especialidade: str | None) -> str | None:
    """Limpa input de especialidade (bug do LLM envia como array)."""
    if not especialidade:
        return None

    if especialidade.startswith("["):
        import json

        try:
            parsed = json.loads(especialidade)
            if isinstance(parsed, list) and parsed:
                return parsed[0]
        except json.JSONDecodeError:
            return especialidade.strip("[]\"'")

    return especialidade


def _preparar_medico_com_preferencias(medico: dict, valor_minimo: float) -> dict:
    """Prepara dict do medico com preferencias para busca."""
    preferencias_extras: dict[str, Any] = {}
    if valor_minimo > 0:
        preferencias_extras["valor_minimo"] = valor_minimo

    preferencias_medico = medico.get("preferencias_detectadas") or {}
    preferencias_combinadas = {**preferencias_medico, **preferencias_extras}

    return {**medico, "preferencias_detectadas": preferencias_combinadas}


async def _buscar_vagas_base(medico: dict, regiao: str | None, limite: int) -> list[dict]:
    """Busca vagas base (com ou sem priorizacao por regiao)."""
    # Import lazy para manter patch path via __init__
    from app.tools.vagas import buscar_vagas_compativeis, buscar_vagas_por_regiao

    if regiao:
        return await buscar_vagas_por_regiao(medico=medico, limite=limite * 2)
    return await buscar_vagas_compativeis(medico=medico, limite=limite * 2)


def _construir_resposta_sem_vagas(
    formatter,
    especialidade_nome: str,
    total_inicial: int,
    filtros_aplicados: list[str],
    especialidade_diferente: bool,
    especialidade_cadastrada: str | None,
) -> dict:
    """Constroi resposta quando nao ha vagas."""
    logger.info(f"Nenhuma vaga encontrada para especialidade {especialidade_nome}")

    mensagem = formatter.mensagem_sem_vagas(
        especialidade_nome=especialidade_nome,
        total_sem_filtros=total_inicial,
        filtros_aplicados=filtros_aplicados if filtros_aplicados else None,
        especialidade_diferente=especialidade_diferente,
        especialidade_cadastrada=especialidade_cadastrada,
    )

    result: dict[str, Any] = {
        "success": True,
        "vagas": [],
        "total_encontradas": 0,
        "especialidade_buscada": especialidade_nome,
        "mensagem_sugerida": mensagem,
    }

    if filtros_aplicados:
        result["total_sem_filtros"] = total_inicial
        result["filtros_aplicados"] = filtros_aplicados

    if especialidade_diferente:
        result["especialidade_cadastrada"] = especialidade_cadastrada

    return result


def _construir_resposta_com_vagas(
    formatter,
    vagas: list[dict],
    especialidade_nome: str,
    especialidade_diferente: bool,
    especialidade_cadastrada: str | None,
) -> dict:
    """Constroi resposta com vagas encontradas."""
    from app.tools.vagas import formatar_vagas_contexto

    logger.info(f"Encontradas {len(vagas)} vagas")

    # Formatar vagas
    vagas_resumo = formatter.formatar_vagas_resumo(vagas, especialidade_nome)
    contexto_formatado = formatar_vagas_contexto(vagas, especialidade_nome)

    # Construir instrucao
    instrucao = formatter.construir_instrucao_vagas(
        especialidade_nome=especialidade_nome,
        especialidade_diferente=especialidade_diferente,
        especialidade_cadastrada=especialidade_cadastrada,
    )

    return {
        "success": True,
        "vagas": vagas_resumo,
        "total_encontradas": len(vagas),
        "especialidade_buscada": especialidade_nome,
        "especialidade_cadastrada": especialidade_cadastrada,
        "especialidade_diferente": especialidade_diferente,
        "contexto": contexto_formatado,
        "instrucao": instrucao,
    }


# =============================================================================
# Deprecated wrappers (compatibilidade com codigo legado)
# =============================================================================


async def _buscar_especialidade_id_por_nome(nome: str) -> str | None:
    """
    Busca ID da especialidade pelo nome (com cache).

    DEPRECATED: Use get_especialidade_service().buscar_por_nome() diretamente.
    Mantido para compatibilidade com codigo legado.
    """
    from app.services.vagas import get_especialidade_service

    service = get_especialidade_service()
    return await service.buscar_por_nome(nome)


def _formatar_valor_display(vaga: dict) -> str:
    """
    Formata valor para exibicao na resposta da tool.

    DEPRECATED: Use get_vagas_formatter().formatar_valor_display() diretamente.
    Mantido para compatibilidade com codigo legado.
    """
    from app.tools.response_formatter import get_vagas_formatter

    formatter = get_vagas_formatter()
    return formatter.formatar_valor_display(vaga)


def _construir_instrucao_confirmacao(vaga: dict, hospital_data: dict) -> str:
    """
    Constroi instrucao de confirmacao baseada no tipo de valor.

    DEPRECATED: Use get_reserva_formatter().construir_instrucao_confirmacao() diretamente.
    Mantido para compatibilidade com codigo legado.
    """
    from app.tools.response_formatter import get_reserva_formatter

    formatter = get_reserva_formatter()
    return formatter.construir_instrucao_confirmacao(vaga, hospital_data)


def _construir_instrucao_ponte_externa(
    vaga: dict,
    hospital_data: dict,
    ponte_externa: dict,
    medico: dict,
) -> str:
    """
    Constroi instrucao de confirmacao para vaga com ponte externa.

    DEPRECATED: Use get_reserva_formatter().construir_instrucao_ponte_externa() diretamente.
    Mantido para compatibilidade com codigo legado.
    """
    from app.tools.response_formatter import get_reserva_formatter

    formatter = get_reserva_formatter()
    return formatter.construir_instrucao_ponte_externa(vaga, hospital_data, ponte_externa, medico)


def _filtrar_por_periodo(vagas: list[dict], periodo_desejado: str) -> list[dict]:
    """
    Filtra vagas por tipo de periodo.

    DEPRECATED: Use app.services.vagas.filtrar_por_periodo() diretamente.
    Mantido para compatibilidade com codigo legado.

    Note: Retorna lista vazia se nao houver match (comportamento original).
    """
    from app.services.vagas.filtros import filtrar_por_periodo

    resultado, _ = filtrar_por_periodo(vagas, periodo_desejado)
    return resultado


def _filtrar_por_dias_semana(vagas: list[dict], dias_desejados: list[str]) -> list[dict]:
    """
    Filtra vagas por dias da semana.

    DEPRECATED: Use app.services.vagas.filtrar_por_dias_semana() diretamente.
    Mantido para compatibilidade com codigo legado.

    Note: Retorna lista vazia se nao houver match (comportamento original).
    """
    from app.services.vagas.filtros import filtrar_por_dias_semana

    resultado, _ = filtrar_por_dias_semana(vagas, dias_desejados)
    return resultado
