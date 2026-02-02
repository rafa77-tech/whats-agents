"""
Tools da Helena - Agente de Gestão.

Sprint 47: Tools pré-definidas + SQL dinâmico.
"""
from app.tools.helena.metricas import (
    TOOL_METRICAS_PERIODO,
    TOOL_METRICAS_CONVERSAO,
    TOOL_METRICAS_CAMPANHAS,
    handle_metricas_periodo,
    handle_metricas_conversao,
    handle_metricas_campanhas,
)
from app.tools.helena.sistema import (
    TOOL_STATUS_SISTEMA,
    TOOL_LISTAR_HANDOFFS,
    handle_status_sistema,
    handle_listar_handoffs,
)
from app.tools.helena.sql import (
    TOOL_CONSULTA_SQL,
    handle_consulta_sql,
)

# Lista de todas as tools
HELENA_TOOLS = [
    TOOL_METRICAS_PERIODO,
    TOOL_METRICAS_CONVERSAO,
    TOOL_METRICAS_CAMPANHAS,
    TOOL_STATUS_SISTEMA,
    TOOL_LISTAR_HANDOFFS,
    TOOL_CONSULTA_SQL,
]


async def executar_tool(
    nome: str,
    params: dict,
    user_id: str,
    channel_id: str,
) -> dict:
    """
    Executa uma tool Helena.

    Args:
        nome: Nome da tool
        params: Parâmetros da tool
        user_id: ID do usuário Slack
        channel_id: ID do canal Slack

    Returns:
        Resultado da tool
    """
    handlers = {
        "metricas_periodo": handle_metricas_periodo,
        "metricas_conversao": handle_metricas_conversao,
        "metricas_campanhas": handle_metricas_campanhas,
        "status_sistema": handle_status_sistema,
        "listar_handoffs": handle_listar_handoffs,
        "consulta_sql": handle_consulta_sql,
    }

    handler = handlers.get(nome)
    if not handler:
        return {"success": False, "error": f"Tool desconhecida: {nome}"}

    try:
        return await handler(params, user_id, channel_id)
    except Exception as e:
        return {"success": False, "error": str(e)}


__all__ = [
    "HELENA_TOOLS",
    "executar_tool",
    # Tools
    "TOOL_METRICAS_PERIODO",
    "TOOL_METRICAS_CONVERSAO",
    "TOOL_METRICAS_CAMPANHAS",
    "TOOL_STATUS_SISTEMA",
    "TOOL_LISTAR_HANDOFFS",
    "TOOL_CONSULTA_SQL",
    # Handlers
    "handle_metricas_periodo",
    "handle_metricas_conversao",
    "handle_metricas_campanhas",
    "handle_status_sistema",
    "handle_listar_handoffs",
    "handle_consulta_sql",
]
