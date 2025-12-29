"""
Tipos para eventos de negocio.

Sprint 17 - E02
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventType(Enum):
    """Tipos de eventos de negocio."""

    DOCTOR_INBOUND = "doctor_inbound"
    DOCTOR_OUTBOUND = "doctor_outbound"
    OFFER_TEASER_SENT = "offer_teaser_sent"
    OFFER_MADE = "offer_made"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    HANDOFF_CREATED = "handoff_created"

    # Confirmação de plantão (Sprint 17)
    SHIFT_CONFIRMATION_DUE = "shift_confirmation_due"  # Plantão terminou, aguarda confirmação
    SHIFT_COMPLETED = "shift_completed"                 # Confirmado: plantão realizado
    SHIFT_NOT_COMPLETED = "shift_not_completed"         # Confirmado: não ocorreu


class EventSource(Enum):
    """Origens validas de eventos."""

    PIPELINE = "pipeline"    # Pipeline de processamento
    BACKEND = "backend"      # Codigo de aplicacao
    DB = "db"                # Trigger de banco
    HEURISTIC = "heuristic"  # Detector heuristico
    OPS = "ops"              # Manual por operacoes


@dataclass
class BusinessEvent:
    """Evento de negocio."""

    event_type: EventType
    source: EventSource  # Obrigatorio (CHECK constraint no DB)
    event_props: dict = field(default_factory=dict)

    # Entidades (opcionais)
    cliente_id: Optional[str] = None
    vaga_id: Optional[str] = None
    hospital_id: Optional[str] = None
    conversation_id: Optional[str] = None
    interaction_id: Optional[int] = None

    # Link com policy
    policy_decision_id: Optional[str] = None

    # Idempotência: chave para deduplicação
    # Padrão: {event_type}:{entity_id}:{ref}
    # Se None, permite duplicatas (eventos sem necessidade de dedupe)
    dedupe_key: Optional[str] = None

    def to_dict(self) -> dict:
        """Serializa para insercao no banco."""
        return {
            "event_type": self.event_type.value,
            "source": self.source.value,
            "event_props": self.event_props,
            "cliente_id": self.cliente_id,
            "vaga_id": self.vaga_id,
            "hospital_id": self.hospital_id,
            "conversation_id": self.conversation_id,
            "interaction_id": self.interaction_id,
            "policy_decision_id": self.policy_decision_id,
            "dedupe_key": self.dedupe_key,
        }
