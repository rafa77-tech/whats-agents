"""
Transition Validator - Valida transições com micro-confirmação.

Sprint 29 - Conversation Mode

MICRO-CONFIRMAÇÃO (AJUSTE 4):
A confirmação é sobre PONTE/CONEXÃO, não sobre reserva.
Julia é INTERMEDIÁRIA - não confirma reservas.

Exemplos de micro-confirmação:
✅ "Quer que eu te conecte ao responsável pela vaga X?"
✅ "Posso te colocar em contato com quem tá oferecendo?"
❌ "Quer que eu reserve pra você?" (Julia não reserva)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Union
from dateutil.parser import parse as parse_datetime

from app.core.timezone import agora_utc


def _ensure_datetime(value: Optional[Union[datetime, str]]) -> Optional[datetime]:
    """Converte string ISO para datetime se necessário."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return parse_datetime(value)
    except Exception:
        return None


from .types import ConversationMode
from .proposer import TransitionProposal

logger = logging.getLogger(__name__)


# Cooldown mínimo entre transições (evitar flip-flop)
TRANSITION_COOLDOWN_MINUTES = 5

# Timeout para pending_transition (se médico não confirmar)
PENDING_TRANSITION_TIMEOUT_MINUTES = 30


class TransitionDecision(Enum):
    """Decisão do validador."""

    APPLY = "apply"  # Aplicar transição imediatamente
    PENDING = "pending"  # Salvar como pending (aguardar confirmação)
    CONFIRM = "confirm"  # Confirmar pending existente
    CANCEL = "cancel"  # Cancelar pending existente
    REJECT = "reject"  # Rejeitar transição


@dataclass
class ValidationResult:
    """Resultado da validação de transição."""

    decision: TransitionDecision
    final_mode: ConversationMode  # Modo final após decisão
    reason: str
    pending_mode: Optional[ConversationMode] = None  # Se decision=PENDING


class TransitionValidator:
    """
    Valida transições com suporte a micro-confirmação.

    Se transição requer confirmação:
    1. Primeira vez: salva pending_transition, retorna PENDING
    2. Médico responde: verifica se confirma ou cancela
    3. Timeout: cancela pending automaticamente
    """

    def validate(
        self,
        proposal: TransitionProposal,
        pending_transition: Optional[ConversationMode] = None,
        pending_transition_at: Optional[datetime] = None,
        last_transition_at: Optional[datetime] = None,
        mensagem_confirma: bool = False,  # Se resposta confirma pending
    ) -> ValidationResult:
        """
        Valida proposta de transição.

        Args:
            proposal: Proposta de transição
            pending_transition: Transição pendente (se houver)
            pending_transition_at: Quando pending foi criada
            last_transition_at: Última transição (para cooldown)
            mensagem_confirma: Se mensagem atual confirma pending

        Returns:
            ValidationResult com decisão
        """
        current_mode = proposal.from_mode

        # 1. Se há pending_transition, verificar confirmação
        if pending_transition:
            return self._handle_pending(
                pending_transition,
                pending_transition_at,
                current_mode,
                mensagem_confirma,
            )

        # 2. Se proposta não sugere transição, manter modo
        if not proposal.should_transition:
            return ValidationResult(
                decision=TransitionDecision.REJECT,
                final_mode=current_mode,
                reason=proposal.trigger,
            )

        # 3. Verificar cooldown
        last_trans_dt = _ensure_datetime(last_transition_at)
        if last_trans_dt:
            minutes_since = (agora_utc() - last_trans_dt.replace(tzinfo=None)).total_seconds() / 60
            if minutes_since < TRANSITION_COOLDOWN_MINUTES:
                return ValidationResult(
                    decision=TransitionDecision.REJECT,
                    final_mode=current_mode,
                    reason=f"cooldown ({minutes_since:.1f}min < {TRANSITION_COOLDOWN_MINUTES}min)",
                )

        # 4. Se transição é automática ou não requer confirmação, aplicar
        if proposal.is_automatic or not proposal.needs_confirmation:
            logger.info(
                f"Transição aplicada: {current_mode.value} → {proposal.to_mode.value} "
                f"(trigger={proposal.trigger})"
            )
            return ValidationResult(
                decision=TransitionDecision.APPLY,
                final_mode=proposal.to_mode,
                reason=f"automático: {proposal.trigger}",
            )

        # 5. Transição requer confirmação → salvar como pending
        logger.info(
            f"Transição pendente: {current_mode.value} → {proposal.to_mode.value} "
            f"(aguardando confirmação)"
        )
        return ValidationResult(
            decision=TransitionDecision.PENDING,
            final_mode=current_mode,  # Ainda não muda
            reason="aguardando micro-confirmação",
            pending_mode=proposal.to_mode,
        )

    def _handle_pending(
        self,
        pending_transition: ConversationMode,
        pending_transition_at: Optional[datetime],
        current_mode: ConversationMode,
        mensagem_confirma: bool,
    ) -> ValidationResult:
        """Trata pending_transition existente."""

        # Verificar timeout
        pending_at_dt = _ensure_datetime(pending_transition_at)
        if pending_at_dt:
            minutes_since = (agora_utc() - pending_at_dt.replace(tzinfo=None)).total_seconds() / 60
            if minutes_since > PENDING_TRANSITION_TIMEOUT_MINUTES:
                logger.info(f"Pending expirada após {minutes_since:.1f}min")
                return ValidationResult(
                    decision=TransitionDecision.CANCEL,
                    final_mode=current_mode,
                    reason="pending expirada por timeout",
                )

        # Se mensagem confirma, aplicar transição
        if mensagem_confirma:
            logger.info(f"Pending confirmada: {current_mode.value} → {pending_transition.value}")
            return ValidationResult(
                decision=TransitionDecision.CONFIRM,
                final_mode=pending_transition,
                reason="confirmado pelo médico",
            )

        # Se mensagem não confirma, cancelar pending
        logger.info("Pending cancelada: médico não confirmou")
        return ValidationResult(
            decision=TransitionDecision.CANCEL,
            final_mode=current_mode,
            reason="não confirmado pelo médico",
        )
