"""
Tipos para o sistema de guardrails de outbound.

Sprint 17 - Contrato único para todo envio outbound.
Sprint 23 E01 - SendOutcome enum para rastreamento detalhado.

Este módulo define o OutboundContext que TODO envio outbound deve passar.
O guardrail decide ALLOW/BLOCK e sempre emite business_event quando
bloquear (e quando permitir por bypass humano).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class SendOutcome(str, Enum):
    """
    Outcome padronizado para envios outbound.

    Sprint 23 E01 - Semantica clara para cada resultado.

    Categorias:
    - SENT: Sucesso
    - BLOCKED_*: Guardrail impediu (permissao/regra)
    - DEDUPED: Protecao anti-spam (nao e bloqueio por permissao)
    - FAILED_*: Erro tecnico
    - BYPASS: Override manual via Slack
    """

    # Sucesso
    SENT = "SENT"

    # Bloqueios por guardrail
    BLOCKED_DEV_ALLOWLIST = "BLOCKED_DEV_ALLOWLIST"  # DEV: número não está na allowlist
    BLOCKED_OPTED_OUT = "BLOCKED_OPTED_OUT"
    BLOCKED_COOLING_OFF = "BLOCKED_COOLING_OFF"
    BLOCKED_NEXT_ALLOWED = "BLOCKED_NEXT_ALLOWED"
    BLOCKED_CONTACT_CAP = "BLOCKED_CONTACT_CAP"
    BLOCKED_CAMPAIGNS_DISABLED = "BLOCKED_CAMPAIGNS_DISABLED"
    BLOCKED_SAFE_MODE = "BLOCKED_SAFE_MODE"
    BLOCKED_CAMPAIGN_COOLDOWN = "BLOCKED_CAMPAIGN_COOLDOWN"
    BLOCKED_QUIET_HOURS = "BLOCKED_QUIET_HOURS"  # Proativo fora do horário comercial

    # Deduplicacao (NAO e bloqueio por permissao)
    DEDUPED = "DEDUPED"

    # Erros tecnicos
    FAILED_PROVIDER = "FAILED_PROVIDER"  # Erro de infra (timeout, 5xx, rede)
    FAILED_VALIDATION = "FAILED_VALIDATION"  # Número inválido/inexistente
    FAILED_BANNED = "FAILED_BANNED"  # Número banido/bloqueado pelo WhatsApp
    FAILED_RATE_LIMIT = "FAILED_RATE_LIMIT"
    FAILED_CIRCUIT_OPEN = "FAILED_CIRCUIT_OPEN"
    FAILED_NO_CAPACITY = "FAILED_NO_CAPACITY"  # Sem chip disponível (temporário)

    # Override manual
    BYPASS = "BYPASS"

    @property
    def is_success(self) -> bool:
        """Retorna True se o envio foi bem sucedido."""
        return self == SendOutcome.SENT

    @property
    def is_blocked(self) -> bool:
        """Retorna True se foi bloqueado por guardrail."""
        return self.value.startswith("BLOCKED_")

    @property
    def is_deduped(self) -> bool:
        """Retorna True se foi deduplicado."""
        return self == SendOutcome.DEDUPED

    @property
    def is_failed(self) -> bool:
        """Retorna True se houve erro tecnico."""
        return self.value.startswith("FAILED_")

    @property
    def is_no_capacity(self) -> bool:
        """Retorna True se falhou por falta de capacidade temporária."""
        return self == SendOutcome.FAILED_NO_CAPACITY


# Mapeamento de reason_code do guardrail para SendOutcome
_GUARDRAIL_TO_OUTCOME: Dict[str, SendOutcome] = {
    "dev_allowlist": SendOutcome.BLOCKED_DEV_ALLOWLIST,
    "dev_allowlist_empty": SendOutcome.BLOCKED_DEV_ALLOWLIST,
    "opted_out": SendOutcome.BLOCKED_OPTED_OUT,
    "opted_out_bypass_no_reason": SendOutcome.BLOCKED_OPTED_OUT,
    "cooling_off": SendOutcome.BLOCKED_COOLING_OFF,
    "next_allowed_at": SendOutcome.BLOCKED_NEXT_ALLOWED,
    "contact_cap": SendOutcome.BLOCKED_CONTACT_CAP,
    "campaigns_disabled": SendOutcome.BLOCKED_CAMPAIGNS_DISABLED,
    "safe_mode": SendOutcome.BLOCKED_SAFE_MODE,
    "campaign_cooldown": SendOutcome.BLOCKED_CAMPAIGN_COOLDOWN,
    "quiet_hours": SendOutcome.BLOCKED_QUIET_HOURS,
}


def map_guardrail_to_outcome(reason_code: str) -> SendOutcome:
    """
    Mapeia reason_code do guardrail para SendOutcome.

    Args:
        reason_code: Codigo retornado pelo guardrail (ex: "opted_out", "cooling_off")

    Returns:
        SendOutcome correspondente

    Raises:
        ValueError: Se reason_code nao for reconhecido
    """
    outcome = _GUARDRAIL_TO_OUTCOME.get(reason_code)
    if outcome is None:
        # Fallback generico para bloqueios nao mapeados
        if reason_code.startswith("blocked"):
            return SendOutcome.BLOCKED_OPTED_OUT  # fallback seguro
        raise ValueError(f"reason_code nao mapeado: {reason_code}")
    return outcome


class OutboundChannel(str, Enum):
    """Canal de envio da mensagem."""

    WHATSAPP = "whatsapp"
    SLACK = "slack"
    API = "api"
    JOB = "job"


class OutboundMethod(str, Enum):
    """Método/intenção do envio."""

    CAMPAIGN = "campaign"  # disparo em massa
    FOLLOWUP = "followup"  # automação baseada em state/policy
    REACTIVATION = "reactivation"  # silêncio + quente
    BUTTON = "button"  # clique Slack
    COMMAND = "command"  # slash command Slack
    MANUAL = "manual"  # console/ops
    REPLY = "reply"  # resposta a mensagem inbound


class ActorType(str, Enum):
    """Tipo de ator que está tentando enviar."""

    HUMAN = "human"  # Gestor/ops via Slack ou console
    BOT = "bot"  # Julia (agente)
    SYSTEM = "system"  # Jobs automáticos (cron, campanhas)


@dataclass(frozen=True)
class OutboundContext:
    """
    Contexto obrigatório para todo envio outbound.

    Este objeto deve ser criado antes de qualquer tentativa de envio
    e passado para check_outbound_guardrails().

    IMPORTANTE sobre REPLY:
    - method=REPLY só é válido com inbound_proof preenchido
    - inbound_proof = (inbound_interaction_id, last_inbound_at recente)
    - Sem prova de inbound, cai nas regras R0-R4 como proativo

    IMPORTANTE sobre BYPASS:
    - Bypass só funciona para channel=SLACK
    - bypass_reason é obrigatório para opted_out

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
        inbound_interaction_id: ID da interação inbound (prova de reply)
        last_inbound_at: Timestamp da última msg inbound (prova de reply)
        bypass_reason: Motivo do bypass humano (obrigatório para opted_out)
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

    # Prova de inbound (obrigatório para method=REPLY)
    inbound_interaction_id: Optional[int] = None
    last_inbound_at: Optional[str] = None  # ISO timestamp

    # Bypass humano
    bypass_reason: Optional[str] = None

    # Metadata para propagação de dados (ex: meta_template info)
    metadata: Optional[Dict[str, Any]] = None

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
