"""
Tipos e estruturas do Policy Engine.

Sprint 15 - Policy Engine (Estado + Decisão Determinística)
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PermissionState(Enum):
    """Estado de permissão de contato."""
    NONE = "none"              # Nunca conversou
    INITIAL = "initial"        # Contato inicial estabelecido
    ACTIVE = "active"          # Conversa aberta e saudável
    COOLING_OFF = "cooling_off"  # Pausa por atrito
    OPTED_OUT = "opted_out"    # Não contatar (terminal)


class TemperatureBand(Enum):
    """Faixa de temperatura (derivada)."""
    COLD = "cold"    # < 0.33
    WARM = "warm"    # 0.33 - 0.66
    HOT = "hot"      # > 0.66


class TemperatureTrend(Enum):
    """Tendência de temperatura."""
    WARMING = "warming"
    COOLING = "cooling"
    STABLE = "stable"


class ObjectionSeverity(Enum):
    """Severidade de objeção."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    GRAVE = "grave"  # Aciona handoff


class RiskTolerance(Enum):
    """Tolerância a vagas de risco."""
    UNKNOWN = "unknown"  # Conservador por default
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LifecycleStage(Enum):
    """Estágio no ciclo de vida."""
    NOVO = "novo"
    PROSPECTING = "prospecting"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    CHURNED = "churned"


class PrimaryAction(Enum):
    """Ação principal decidida pela policy."""
    DISCOVERY = "discovery"        # Primeiro contato, conhecer médico
    OFFER = "offer"                # Oferecer vaga
    FOLLOWUP = "followup"          # Dar continuidade
    REACTIVATION = "reactivation"  # Reativar médico inativo
    HANDOFF = "handoff"            # Transferir para humano
    WAIT = "wait"                  # Não fazer nada


class Tone(Enum):
    """Tom da resposta."""
    LEVE = "leve"              # Descontraído, amigável
    DIRETO = "direto"          # Objetivo, sem rodeios
    CAUTELOSO = "cauteloso"    # Cuidado extra
    CRISE = "crise"            # Situação crítica


@dataclass
class DoctorState:
    """Estado atual do médico (lido do banco)."""
    cliente_id: str

    # Permissão
    permission_state: PermissionState = PermissionState.NONE
    cooling_off_until: Optional[datetime] = None

    # Temperatura
    temperature: float = 0.5
    temperature_trend: TemperatureTrend = TemperatureTrend.STABLE
    temperature_band: TemperatureBand = TemperatureBand.WARM

    # Risco
    risk_tolerance: RiskTolerance = RiskTolerance.UNKNOWN

    # Contato
    last_inbound_at: Optional[datetime] = None
    last_outbound_at: Optional[datetime] = None
    last_outbound_actor: Optional[str] = None
    next_allowed_at: Optional[datetime] = None
    contact_count_7d: int = 0

    # Objeção
    active_objection: Optional[str] = None
    objection_severity: Optional[ObjectionSeverity] = None
    objection_detected_at: Optional[datetime] = None
    objection_resolved_at: Optional[datetime] = None

    # Contexto
    pending_action: Optional[str] = None
    current_intent: Optional[str] = None
    lifecycle_stage: LifecycleStage = LifecycleStage.NOVO

    # Flags
    flags: dict = field(default_factory=dict)

    # Decay
    last_decay_at: Optional[datetime] = None

    def has_unresolved_objection(self) -> bool:
        """Verifica se há objeção ativa não resolvida."""
        return (
            self.active_objection is not None
            and self.objection_resolved_at is None
        )

    def is_contactable(self) -> bool:
        """Verifica se pode ser contatado."""
        if self.permission_state == PermissionState.OPTED_OUT:
            return False
        if self.permission_state == PermissionState.COOLING_OFF:
            if self.cooling_off_until and datetime.utcnow() < self.cooling_off_until:
                return False
        if self.next_allowed_at and datetime.utcnow() < self.next_allowed_at:
            return False
        return True

    def days_since_last_inbound(self) -> Optional[int]:
        """Retorna dias desde última mensagem do médico."""
        if not self.last_inbound_at:
            return None
        delta = datetime.utcnow() - self.last_inbound_at
        return delta.days

    def days_since_last_outbound(self) -> Optional[int]:
        """Retorna dias desde última mensagem da Julia."""
        if not self.last_outbound_at:
            return None
        delta = datetime.utcnow() - self.last_outbound_at
        return delta.days


@dataclass
class PolicyDecision:
    """Resultado do PolicyDecide - o que a Julia pode/não pode fazer."""
    primary_action: PrimaryAction
    allowed_actions: list[str]
    forbidden_actions: list[str]
    tone: Tone
    requires_human: bool
    constraints_text: str  # Bloco para injetar no prompt
    reasoning: str  # Para logs/debug

    def to_dict(self) -> dict:
        """Serializa para logging."""
        return {
            "primary_action": self.primary_action.value,
            "allowed_actions": self.allowed_actions,
            "forbidden_actions": self.forbidden_actions,
            "tone": self.tone.value,
            "requires_human": self.requires_human,
            "reasoning": self.reasoning,
        }
