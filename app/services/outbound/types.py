"""
Tipos e dataclasses do modulo outbound.

Sprint 58 E04 - Extraido de outbound.py monolitico.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.guardrails import SendOutcome


@dataclass
class OutboundResult:
    """
    Resultado do envio outbound.

    Sprint 23 E01 - Campos padronizados para rastreamento completo.

    Attributes:
        success: True se mensagem foi enviada com sucesso
        outcome: Enum com resultado detalhado (SENT, BLOCKED_*, DEDUPED, FAILED_*)
        outcome_reason_code: Codigo detalhado do motivo
        outcome_at: Timestamp de quando o outcome foi determinado
        blocked: True APENAS para guardrails (BLOCKED_*)
        deduped: True para deduplicacao (DEDUPED)
        human_bypass: True quando liberou por override humano
        provider_message_id: ID da mensagem no Evolution API quando SENT
        dedupe_key: Chave de deduplicacao usada
        error: Mensagem de erro quando FAILED_*
        evolution_response: Resposta completa do Evolution API
    """

    success: bool
    outcome: SendOutcome
    outcome_reason_code: Optional[str] = None
    outcome_at: Optional[datetime] = None
    blocked: bool = False  # True APENAS para guardrails
    deduped: bool = False  # True para deduplicacao (NAO e blocked)
    human_bypass: bool = False
    provider_message_id: Optional[str] = None
    dedupe_key: Optional[str] = None
    error: Optional[str] = None
    evolution_response: Optional[dict] = None
    chip_id: Optional[str] = None  # Sprint 41: ID do chip que enviou

    # Alias para compatibilidade (deprecated)
    @property
    def block_reason(self) -> Optional[str]:
        """Alias para outcome_reason_code (deprecated)."""
        return self.outcome_reason_code
