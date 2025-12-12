"""
[DEPRECATED] Modulo de compatibilidade para slack tools.

Este arquivo foi reorganizado em:
- app/tools/slack/metricas.py
- app/tools/slack/medicos.py
- app/tools/slack/mensagens.py
- app/tools/slack/vagas.py
- app/tools/slack/sistema.py
- app/tools/slack/__init__.py

Use: from app.tools.slack import SLACK_TOOLS, executar_tool
Sprint 10 - S10.E2.3
"""
import warnings

warnings.warn(
    "slack_tools.py is deprecated. Use app.tools.slack instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-exportar tudo do novo modulo para manter compatibilidade
from app.tools.slack import (
    # Listas agregadas
    SLACK_TOOLS,
    TOOLS_CRITICAS,
    executar_tool,
    # Tools individuais - Metricas
    TOOL_BUSCAR_METRICAS,
    TOOL_COMPARAR_PERIODOS,
    # Tools individuais - Medicos
    TOOL_BUSCAR_MEDICO,
    TOOL_LISTAR_MEDICOS,
    TOOL_BLOQUEAR_MEDICO,
    TOOL_DESBLOQUEAR_MEDICO,
    # Tools individuais - Mensagens
    TOOL_ENVIAR_MENSAGEM,
    TOOL_BUSCAR_HISTORICO,
    # Tools individuais - Vagas
    TOOL_BUSCAR_VAGAS,
    TOOL_RESERVAR_VAGA,
    # Tools individuais - Sistema
    TOOL_STATUS_SISTEMA,
    TOOL_BUSCAR_HANDOFFS,
    TOOL_PAUSAR_JULIA,
    TOOL_RETOMAR_JULIA,
    # Tools individuais - Briefing
    TOOL_PROCESSAR_BRIEFING,
    # Helpers
    _calcular_datas_periodo,
    _buscar_medico_por_identificador,
)

__all__ = [
    "SLACK_TOOLS",
    "TOOLS_CRITICAS",
    "executar_tool",
    "TOOL_BUSCAR_METRICAS",
    "TOOL_COMPARAR_PERIODOS",
    "TOOL_BUSCAR_MEDICO",
    "TOOL_LISTAR_MEDICOS",
    "TOOL_BLOQUEAR_MEDICO",
    "TOOL_DESBLOQUEAR_MEDICO",
    "TOOL_ENVIAR_MENSAGEM",
    "TOOL_BUSCAR_HISTORICO",
    "TOOL_BUSCAR_VAGAS",
    "TOOL_RESERVAR_VAGA",
    "TOOL_STATUS_SISTEMA",
    "TOOL_BUSCAR_HANDOFFS",
    "TOOL_PAUSAR_JULIA",
    "TOOL_RETOMAR_JULIA",
    "TOOL_PROCESSAR_BRIEFING",
    "_calcular_datas_periodo",
    "_buscar_medico_por_identificador",
]
