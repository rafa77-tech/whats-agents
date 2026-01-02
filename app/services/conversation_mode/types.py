"""
Tipos do Conversation Mode.

Sprint 29 - Conversation Mode
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ConversationMode(Enum):
    """
    Modos de conversa.

    IMPORTANTE: Julia é INTERMEDIÁRIA em todos os modos.
    Ela conecta médico com responsável, não fecha vagas.
    """
    DISCOVERY = "discovery"      # Conhecer o médico
    OFERTA = "oferta"            # Intermediar (conectar com responsável)
    FOLLOWUP = "followup"        # Acompanhar desfecho
    REATIVACAO = "reativacao"    # Reativar inativo


@dataclass
class ModeInfo:
    """Informações do modo atual de uma conversa."""
    conversa_id: str
    mode: ConversationMode
    updated_at: Optional[datetime] = None
    updated_reason: Optional[str] = None
    mode_source: Optional[str] = None  # "inbound", "campaign:<id>", "manual"
    pending_transition: Optional[ConversationMode] = None
    pending_transition_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "ModeInfo":
        """Cria ModeInfo a partir de row do banco."""
        pending = row.get("pending_transition")
        return cls(
            conversa_id=row["id"],
            mode=ConversationMode(row.get("conversation_mode", "discovery")),
            updated_at=row.get("mode_updated_at"),
            updated_reason=row.get("mode_updated_reason"),
            mode_source=row.get("mode_source"),
            pending_transition=ConversationMode(pending) if pending else None,
            pending_transition_at=row.get("pending_transition_at"),
        )

    def has_pending(self) -> bool:
        """Verifica se há transição pendente."""
        return self.pending_transition is not None


@dataclass
class ModeTransition:
    """Representa uma transição de modo."""
    from_mode: ConversationMode
    to_mode: ConversationMode
    reason: str
    confidence: float  # 0.0 a 1.0
    evidence: str  # Texto/sinal que motivou

    # Transições permitidas (matriz determinística)
    ALLOWED_TRANSITIONS: dict = None  # Definido em proposer.py

    def is_valid(self) -> bool:
        """Verifica se transição é permitida."""
        # Transições proibidas (hardcoded para segurança)
        forbidden = [
            (ConversationMode.DISCOVERY, ConversationMode.FOLLOWUP),
            (ConversationMode.REATIVACAO, ConversationMode.REATIVACAO),
        ]
        return (self.from_mode, self.to_mode) not in forbidden
