"""
Tipos, constantes e helpers do agente Julia.

Sprint 58 - Epic 2: Extraido de app/services/agente.py
"""

import logging
from dataclasses import dataclass
from typing import Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# Sprint 44 T02.1: Timeout global para geração de resposta
TIMEOUT_GERACAO_RESPOSTA = settings.LLM_LOOP_TIMEOUT_SEGUNDOS
RESPOSTA_TIMEOUT_FALLBACK = "Desculpa, tive um probleminha aqui. Pode repetir?"

# Padrões que indicam resposta incompleta (mesma lógica do Slack)
PADROES_RESPOSTA_INCOMPLETA = [
    ":",  # "Vou verificar o que temos:"
    "...",  # Reticências no final
    "vou verificar",
    "deixa eu ver",
    "um momento",
    "vou buscar",
    "vou checar",
    "deixa eu buscar",
]
MAX_RETRIES_INCOMPLETO = 2


def _resposta_parece_incompleta(texto: str, stop_reason: str = None) -> bool:
    """
    Detecta se resposta parece incompleta e deveria ter chamado uma tool.

    Args:
        texto: Texto da resposta
        stop_reason: Motivo de parada do LLM (tool_use, end_turn, etc)

    Returns:
        True se resposta parece incompleta
    """
    if not texto:
        return False

    # Se parou por tool_use, não é incompleta (a tool vai ser executada)
    if stop_reason == "tool_use":
        return False

    texto_lower = texto.lower().strip()

    for padrao in PADROES_RESPOSTA_INCOMPLETA:
        if texto_lower.endswith(padrao):
            logger.warning(
                f"Resposta parece incompleta: termina com '{padrao}' (stop_reason={stop_reason})"
            )
            return True

    return False


@dataclass
class ProcessamentoResult:
    """Resultado do processamento de mensagem (Sprint 16)."""

    resposta: Optional[str] = None
    policy_decision_id: Optional[str] = None
    rule_matched: Optional[str] = None
