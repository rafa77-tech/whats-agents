"""
Tipos para o sistema de guardrails de outbound.

Sprint 17 - Contrato único para todo envio outbound.

Este módulo define o OutboundContext que TODO envio outbound deve passar.
O guardrail decide ALLOW/BLOCK e sempre emite business_event quando
bloquear (e quando permitir por bypass humano).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any


class OutboundChannel(str, Enum):
    """Canal de envio da mensagem."""
    WHATSAPP = "whatsapp"
    SLACK = "slack"
    API = "api"
    JOB = "job"


class OutboundMethod(str, Enum):
    """Método/intenção do envio."""
    CAMPAIGN = "campaign"           # disparo em massa
    FOLLOWUP = "followup"           # automação baseada em state/policy
    REACTIVATION = "reactivation"   # silêncio + quente
    BUTTON = "button"               # clique Slack
    COMMAND = "command"             # slash command Slack
    MANUAL = "manual"               # console/ops
    REPLY = "reply"                 # resposta a mensagem inbound


class ActorType(str, Enum):
    """Tipo de ator que está tentando enviar."""
    HUMAN = "human"     # Gestor/ops via Slack ou console
    BOT = "bot"         # Julia (agente)
    SYSTEM = "system"   # Jobs automáticos (cron, campanhas)


@dataclass(frozen=True)
class OutboundContext:
    """
    Contexto obrigatório para todo envio outbound.

    Este objeto deve ser criado antes de qualquer tentativa de envio
    e passado para check_outbound_guardrails().

    Attributes:
        cliente_id: UUID do médico destinatário (obrigatório)
        actor_type: Quem está tentando enviar (human/bot/system)
        channel: Canal de origem do comando (whatsapp/slack/api/job)
        method: Intenção operacional (campaign/followup/reply/etc)
        is_proactive: True para campanhas, reativações; False para replies
        conversation_id: UUID da conversa (se houver)
        actor_id: Identificador do ator (ex: "rafael", "julia")
        campaign_id: UUID da campanha (se aplicável)
        policy_decision_id: Link com decisão do policy engine
        extra: Dados extras para auditoria
    """
    # Obrigatórios
    cliente_id: str
    actor_type: ActorType
    channel: OutboundChannel
    method: OutboundMethod
    is_proactive: bool

    # Opcionais para rastreio
    conversation_id: Optional[str] = None
    actor_id: Optional[str] = None
    campaign_id: Optional[str] = None
    policy_decision_id: Optional[str] = None

    # Extras para auditoria
    extra: Optional[Dict[str, Any]] = None


class GuardrailDecision(str, Enum):
    """Decisão do guardrail."""
    ALLOW = "allow"
    BLOCK = "block"


@dataclass
class GuardrailResult:
    """
    Resultado da verificação do guardrail.

    Attributes:
        decision: ALLOW ou BLOCK
        reason_code: Código da razão (opted_out, cooling_off, etc)
        human_bypass: True quando liberou por override humano
        details: Detalhes extras (ex: until, cap, count)
    """
    decision: GuardrailDecision
    reason_code: str
    human_bypass: bool = False
    details: Optional[Dict[str, Any]] = None

    @property
    def is_allowed(self) -> bool:
        """Atalho para verificar se foi permitido."""
        return self.decision == GuardrailDecision.ALLOW

    @property
    def is_blocked(self) -> bool:
        """Atalho para verificar se foi bloqueado."""
        return self.decision == GuardrailDecision.BLOCK
