"""
Tool handler: buscar_vagas.

Processa busca de vagas disponiveis para o medico.

Sprint 58 - E5: Extraido de vagas.py monolitico.
"""

import logging
from typing import Any

from app.tools.vagas._helpers import (
    _buscar_vagas_base,
    _construir_resposta_com_vagas,
    _construir_resposta_sem_vagas,
    _limpar_especialidade_input,
    _preparar_medico_com_preferencias,
)

logger = logging.getLogger(__name__)


async def handle_buscar_vagas(tool_input: dict, medico: dict, conversa: dict) -> dict[str, Any]:
    """
    Processa chamada da tool buscar_vagas.

    Sprint 31 - Refatorado para usar services.

    Fluxo:
    1. Parse e validacao de input
    2. Resolucao de especialidade via EspecialidadeService
    3. Busca de vagas via service existente
    4. Aplicacao de filtros via modulo de filtros
    5. Formatacao de resposta via VagasResponseFormatter

    Args:
        tool_input: Input da tool (especialidade, regiao, periodo, valor_minimo, etc)
        medico: Dados do medico (incluindo especialidade_id, preferencias)
        conversa: Dados da conversa atual

    Returns:
        Dict com vagas encontradas e contexto formatado
    """
    # Import lazy para manter patch path via app.tools.vagas (package __init__)
    from app.tools.vagas import (
        aplicar_filtros,
        filtrar_por_conflitos,
        get_especialidade_service,
        get_vagas_formatter,
        verificar_conflito,
    )

    # Services
    especialidade_service = get_especialidade_service()
    formatter = get_vagas_formatter()

    # 1. Parse input
    especialidade_solicitada = _limpar_especialidade_input(tool_input.get("especialidade"))
    regiao = tool_input.get("regiao")
    periodo = tool_input.get("periodo", "qualquer")
    valor_minimo = tool_input.get("valor_minimo", 0)
    dias_semana = tool_input.get("dias_semana", [])
    limite = min(tool_input.get("limite", 5), 10)

    # 2. Resolver especialidade
    (
        especialidade_id,
        especialidade_nome,
        especialidade_diferente,
    ) = await especialidade_service.resolver_especialidade_medico(especialidade_solicitada, medico)

    # Validar especialidade
    if especialidade_solicitada and not especialidade_id:
        return {
            "success": False,
            "error": f"Especialidade '{especialidade_solicitada}' nao encontrada",
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_especialidade_nao_encontrada(
                especialidade_solicitada
            ),
        }

    if not especialidade_id:
        logger.warning(f"Medico {medico.get('id')} sem especialidade definida")
        return {
            "success": False,
            "error": "Especialidade nao identificada",
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_especialidade_nao_identificada(),
        }

    logger.info(
        f"Buscando vagas para medico {medico.get('id')}: "
        f"especialidade={especialidade_nome}, regiao={regiao}, periodo={periodo}"
    )

    # Atualizar medico dict
    medico["especialidade_id"] = especialidade_id
    medico_com_prefs = _preparar_medico_com_preferencias(medico, valor_minimo)

    try:
        # 3. Buscar vagas
        vagas = await _buscar_vagas_base(medico_com_prefs, regiao, limite)
        total_inicial = len(vagas)

        # 4. Aplicar filtros
        vagas, filtros_aplicados = aplicar_filtros(vagas, periodo, dias_semana)
        vagas = await filtrar_por_conflitos(vagas, medico["id"], verificar_conflito)
        vagas_final = vagas[:limite]

        # 5. Formatar resposta
        if not vagas_final:
            return _construir_resposta_sem_vagas(
                formatter,
                especialidade_nome,
                total_inicial,
                filtros_aplicados,
                especialidade_diferente,
                medico.get("especialidade"),
            )

        return _construir_resposta_com_vagas(
            formatter,
            vagas_final,
            especialidade_nome,
            especialidade_diferente,
            medico.get("especialidade"),
        )

    except Exception as e:
        logger.error(f"Erro ao buscar vagas: {e}")
        return {
            "success": False,
            "error": str(e),
            "vagas": [],
            "mensagem_sugerida": formatter.mensagem_erro_generico(),
        }
