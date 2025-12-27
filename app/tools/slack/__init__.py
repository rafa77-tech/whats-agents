"""
Tools para o agente Julia no Slack.

Modulo reorganizado com tools separadas por categoria.
Sprint 10 - S10.E2.3
"""
import logging
from typing import Any

# Importar tools de cada modulo
from .metricas import (
    TOOL_BUSCAR_METRICAS,
    TOOL_COMPARAR_PERIODOS,
    handle_buscar_metricas,
    handle_comparar_periodos,
    _calcular_datas_periodo,
)

from .medicos import (
    TOOL_BUSCAR_MEDICO,
    TOOL_LISTAR_MEDICOS,
    TOOL_BLOQUEAR_MEDICO,
    TOOL_DESBLOQUEAR_MEDICO,
    handle_buscar_medico,
    handle_listar_medicos,
    handle_bloquear_medico,
    handle_desbloquear_medico,
    _buscar_medico_por_identificador,
)

from .mensagens import (
    TOOL_ENVIAR_MENSAGEM,
    TOOL_BUSCAR_HISTORICO,
    handle_enviar_mensagem,
    handle_buscar_historico,
)

from .vagas import (
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_VAGA,
    handle_buscar_vagas,
    handle_reservar_vaga,
)

from .sistema import (
    TOOL_STATUS_SISTEMA,
    TOOL_BUSCAR_HANDOFFS,
    TOOL_PAUSAR_JULIA,
    TOOL_RETOMAR_JULIA,
    handle_status_sistema,
    handle_buscar_handoffs,
    handle_pausar_julia,
    handle_retomar_julia,
)

from .briefing import (
    TOOL_PROCESSAR_BRIEFING,
    handle_processar_briefing,
)

from .grupos import (
    TOOL_LISTAR_VAGAS_REVISAO,
    TOOL_APROVAR_VAGA_GRUPO,
    TOOL_REJEITAR_VAGA_GRUPO,
    TOOL_DETALHES_VAGA_GRUPO,
    TOOL_ESTATISTICAS_GRUPOS,
    TOOL_ADICIONAR_ALIAS_HOSPITAL,
    TOOL_BUSCAR_HOSPITAL,
    handle_listar_vagas_revisao,
    handle_aprovar_vaga_grupo,
    handle_rejeitar_vaga_grupo,
    handle_detalhes_vaga_grupo,
    handle_estatisticas_grupos,
    handle_adicionar_alias_hospital,
    handle_buscar_hospital_grupos,
)

logger = logging.getLogger(__name__)


# =============================================================================
# AGREGACAO DE TOOLS
# =============================================================================

SLACK_TOOLS = [
    TOOL_ENVIAR_MENSAGEM,
    TOOL_BUSCAR_METRICAS,
    TOOL_COMPARAR_PERIODOS,
    TOOL_BUSCAR_MEDICO,
    TOOL_LISTAR_MEDICOS,
    TOOL_BLOQUEAR_MEDICO,
    TOOL_DESBLOQUEAR_MEDICO,
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_VAGA,
    TOOL_STATUS_SISTEMA,
    TOOL_BUSCAR_HANDOFFS,
    TOOL_BUSCAR_HISTORICO,
    TOOL_PAUSAR_JULIA,
    TOOL_RETOMAR_JULIA,
    TOOL_PROCESSAR_BRIEFING,
    # Grupos WhatsApp (Sprint 14)
    TOOL_LISTAR_VAGAS_REVISAO,
    TOOL_APROVAR_VAGA_GRUPO,
    TOOL_REJEITAR_VAGA_GRUPO,
    TOOL_DETALHES_VAGA_GRUPO,
    TOOL_ESTATISTICAS_GRUPOS,
    TOOL_ADICIONAR_ALIAS_HOSPITAL,
    TOOL_BUSCAR_HOSPITAL,
]

# Tools que requerem confirmacao
TOOLS_CRITICAS = {
    "enviar_mensagem",
    "bloquear_medico",
    "desbloquear_medico",
    "reservar_vaga",
    "pausar_julia",
    "retomar_julia",
    # Grupos WhatsApp (Sprint 14)
    "aprovar_vaga_grupo",
    "rejeitar_vaga_grupo",
    "adicionar_alias_hospital",
}


# =============================================================================
# EXECUTOR CENTRAL
# =============================================================================

async def executar_tool(nome: str, params: dict, user_id: str, channel_id: str = "") -> dict[str, Any]:
    """
    Executa uma tool pelo nome.

    Args:
        nome: Nome da tool
        params: Parametros da tool
        user_id: ID do usuario Slack
        channel_id: ID do canal Slack (opcional, usado por algumas tools)

    Returns:
        Resultado da execucao
    """
    handlers = {
        "enviar_mensagem": handle_enviar_mensagem,
        "buscar_metricas": handle_buscar_metricas,
        "comparar_periodos": handle_comparar_periodos,
        "buscar_medico": handle_buscar_medico,
        "listar_medicos": handle_listar_medicos,
        "bloquear_medico": handle_bloquear_medico,
        "desbloquear_medico": handle_desbloquear_medico,
        "buscar_vagas": handle_buscar_vagas,
        "reservar_vaga": handle_reservar_vaga,
        "status_sistema": handle_status_sistema,
        "buscar_handoffs": handle_buscar_handoffs,
        "buscar_historico": handle_buscar_historico,
        "pausar_julia": lambda p: handle_pausar_julia(p, user_id),
        "retomar_julia": lambda p: handle_retomar_julia(p, user_id),
        "processar_briefing": lambda p: handle_processar_briefing(p, channel_id, user_id),
        # Grupos WhatsApp (Sprint 14)
        "listar_vagas_revisao": handle_listar_vagas_revisao,
        "aprovar_vaga_grupo": handle_aprovar_vaga_grupo,
        "rejeitar_vaga_grupo": handle_rejeitar_vaga_grupo,
        "detalhes_vaga_grupo": handle_detalhes_vaga_grupo,
        "estatisticas_grupos": handle_estatisticas_grupos,
        "adicionar_alias_hospital": handle_adicionar_alias_hospital,
        "buscar_hospital_grupos": handle_buscar_hospital_grupos,
    }

    handler = handlers.get(nome)
    if not handler:
        return {"success": False, "error": f"Tool '{nome}' nao encontrada"}

    try:
        return await handler(params)
    except Exception as e:
        logger.error(f"Erro ao executar tool {nome}: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Listas agregadas
    "SLACK_TOOLS",
    "TOOLS_CRITICAS",
    "executar_tool",
    # Tools individuais - Metricas
    "TOOL_BUSCAR_METRICAS",
    "TOOL_COMPARAR_PERIODOS",
    # Tools individuais - Medicos
    "TOOL_BUSCAR_MEDICO",
    "TOOL_LISTAR_MEDICOS",
    "TOOL_BLOQUEAR_MEDICO",
    "TOOL_DESBLOQUEAR_MEDICO",
    # Tools individuais - Mensagens
    "TOOL_ENVIAR_MENSAGEM",
    "TOOL_BUSCAR_HISTORICO",
    # Tools individuais - Vagas
    "TOOL_BUSCAR_VAGAS",
    "TOOL_RESERVAR_VAGA",
    # Tools individuais - Sistema
    "TOOL_STATUS_SISTEMA",
    "TOOL_BUSCAR_HANDOFFS",
    "TOOL_PAUSAR_JULIA",
    "TOOL_RETOMAR_JULIA",
    # Tools individuais - Briefing (Sprint 11)
    "TOOL_PROCESSAR_BRIEFING",
    # Tools individuais - Grupos WhatsApp (Sprint 14)
    "TOOL_LISTAR_VAGAS_REVISAO",
    "TOOL_APROVAR_VAGA_GRUPO",
    "TOOL_REJEITAR_VAGA_GRUPO",
    "TOOL_DETALHES_VAGA_GRUPO",
    "TOOL_ESTATISTICAS_GRUPOS",
    "TOOL_ADICIONAR_ALIAS_HOSPITAL",
    "TOOL_BUSCAR_HOSPITAL",
    # Helpers exportados para testes
    "_calcular_datas_periodo",
    "_buscar_medico_por_identificador",
]
