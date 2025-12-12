"""
DEPRECATED: Use app.services.slack

Este arquivo eh mantido para backward compatibility.
Novos codigos devem usar:

    from app.services.slack import AgenteSlack, processar_mensagem_slack

Sprint 10 - S10.E2.2
"""
import warnings

warnings.warn(
    "agente_slack is deprecated. Use app.services.slack instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export para backward compatibility
from app.services.slack import AgenteSlack, processar_mensagem_slack

# Re-export SYSTEM_PROMPT para compatibilidade
from app.services.slack.prompts import SYSTEM_PROMPT_AGENTE as SYSTEM_PROMPT

# Re-exports para testes (patches precisam encontrar no modulo deprecated)
from app.services.supabase import supabase
from app.tools.slack_tools import executar_tool

__all__ = [
    "AgenteSlack",
    "processar_mensagem_slack",
    "SYSTEM_PROMPT",
    "supabase",
    "executar_tool",
]
