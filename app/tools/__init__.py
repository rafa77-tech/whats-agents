"""
Tools para o agente Julia.
"""

from app.tools.vagas import (
    TOOL_RESERVAR_PLANTAO,
    handle_reservar_plantao,
)
from app.tools.lembrete import (
    TOOL_AGENDAR_LEMBRETE,
    handle_agendar_lembrete,
)

__all__ = [
    "TOOL_RESERVAR_PLANTAO",
    "handle_reservar_plantao",
    "TOOL_AGENDAR_LEMBRETE",
    "handle_agendar_lembrete",
]
