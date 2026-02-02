"""
Transition Proposer - Propõe transições baseado em intent + matriz.

Sprint 29 - Conversation Mode

NÃO aplica a transição - apenas propõe.
A decisão final é do TransitionValidator.
"""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from dateutil.parser import parse as parse_datetime

from app.core.timezone import agora_utc
from .types import ConversationMode


from .intents import DetectedIntent, IntentResult


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

logger = logging.getLogger(__name__)


# =============================================================================
# MATRIZ DE TRANSIÇÕES PERMITIDAS (AJUSTE 1)
# Transições fora desta matriz são BLOQUEADAS
# =============================================================================
ALLOWED_TRANSITIONS: dict[ConversationMode, set[ConversationMode]] = {
    ConversationMode.DISCOVERY: {
        ConversationMode.OFERTA,      # Com evidência + micro-confirmação
        ConversationMode.REATIVACAO,  # Silêncio > 7d (automático)
    },
    ConversationMode.OFERTA: {
        ConversationMode.FOLLOWUP,    # Ponte feita com responsável
        ConversationMode.DISCOVERY,   # Recuo tático (objeção)
        ConversationMode.REATIVACAO,  # Silêncio > 7d
    },
    ConversationMode.FOLLOWUP: {
        ConversationMode.OFERTA,      # Nova oportunidade
        ConversationMode.REATIVACAO,  # Silêncio > 7d
        ConversationMode.DISCOVERY,   # Mudou de perfil
    },
    ConversationMode.REATIVACAO: {
        ConversationMode.DISCOVERY,   # Médico respondeu com dúvida
        ConversationMode.OFERTA,      # Médico respondeu com interesse
        ConversationMode.FOLLOWUP,    # Médico respondeu neutro
    },
}

# Transições automáticas (não requerem confirmação)
AUTOMATIC_TRANSITIONS: set[tuple[ConversationMode, ConversationMode]] = {
    (ConversationMode.OFERTA, ConversationMode.FOLLOWUP),      # Ponte feita
    (ConversationMode.REATIVACAO, ConversationMode.FOLLOWUP),  # Médico respondeu
}

# Transições que REQUEREM micro-confirmação (AJUSTE 4)
# A confirmação é sobre PONTE, não reserva (Julia é intermediária)
CONFIRMATION_REQUIRED: set[tuple[ConversationMode, ConversationMode]] = {
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA),
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA),
}

# Mapeamento: intent → modo sugerido
INTENT_TO_MODE: dict[DetectedIntent, Optional[ConversationMode]] = {
    DetectedIntent.INTERESSE_VAGA: ConversationMode.OFERTA,
    DetectedIntent.PRONTO_FECHAR: ConversationMode.OFERTA,
    DetectedIntent.DUVIDA_PERFIL: ConversationMode.DISCOVERY,
    DetectedIntent.OBJECAO: ConversationMode.DISCOVERY,
    DetectedIntent.VOLTANDO: ConversationMode.FOLLOWUP,
    DetectedIntent.NEUTRO: None,
    DetectedIntent.RECUSA: None,
}

# Silêncio que dispara reativação
SILENCE_DAYS_FOR_REACTIVATION = 7


@dataclass
class TransitionProposal:
    """Proposta de transição de modo."""
    should_transition: bool
    from_mode: ConversationMode
    to_mode: Optional[ConversationMode]
    needs_confirmation: bool  # Se True, salvar como pending
    is_automatic: bool  # Transição automática (não precisa de evidência forte)
    trigger: str
    evidence: str
    confidence: float


class TransitionProposer:
    """
    Propõe transições baseado em intent detectado + matriz de transições.

    NÃO aplica a transição - apenas propõe.
    """

    def propose(
        self,
        intent_result: IntentResult,
        current_mode: ConversationMode,
        last_message_at: Optional[datetime] = None,
        ponte_feita: bool = False,
        objecao_resolvida: bool = False,
    ) -> TransitionProposal:
        """
        Propõe transição baseado no intent detectado.

        Args:
            intent_result: Resultado da detecção de intent
            current_mode: Modo atual da conversa
            last_message_at: Última mensagem do médico
            ponte_feita: Se ponte foi feita com responsável (Julia é intermediária)
            objecao_resolvida: Se objeção foi resolvida

        Returns:
            TransitionProposal com sugestão
        """
        # 1. Regras automáticas primeiro (alta prioridade)
        auto_proposal = self._check_automatic_rules(
            current_mode, last_message_at, ponte_feita
        )
        if auto_proposal.should_transition:
            return auto_proposal

        # 2. Baseado no intent detectado
        return self._propose_from_intent(
            intent_result, current_mode, objecao_resolvida
        )

    def _check_automatic_rules(
        self,
        current_mode: ConversationMode,
        last_message_at: Optional[datetime],
        ponte_feita: bool,
    ) -> TransitionProposal:
        """Verifica regras automáticas de transição."""

        # Regra: Silêncio >= 7 dias → REATIVACAO
        last_msg_dt = _ensure_datetime(last_message_at)
        if last_msg_dt:
            days_since = (agora_utc() - last_msg_dt.replace(tzinfo=None)).days
            if days_since >= SILENCE_DAYS_FOR_REACTIVATION:
                if current_mode != ConversationMode.REATIVACAO:
                    return TransitionProposal(
                        should_transition=True,
                        from_mode=current_mode,
                        to_mode=ConversationMode.REATIVACAO,
                        needs_confirmation=False,
                        is_automatic=True,
                        trigger="silencio_7d",
                        evidence=f"silêncio de {days_since} dias",
                        confidence=0.95,
                    )

        # Regra: Ponte feita com responsável → FOLLOWUP
        # (Julia é intermediária, não confirma reserva)
        if ponte_feita and current_mode == ConversationMode.OFERTA:
            return TransitionProposal(
                should_transition=True,
                from_mode=current_mode,
                to_mode=ConversationMode.FOLLOWUP,
                needs_confirmation=False,
                is_automatic=True,
                trigger="ponte_feita",
                evidence="médico conectado ao responsável da vaga",
                confidence=1.0,
            )

        # Nenhuma regra automática aplicável
        return TransitionProposal(
            should_transition=False,
            from_mode=current_mode,
            to_mode=None,
            needs_confirmation=False,
            is_automatic=False,
            trigger="none",
            evidence="",
            confidence=0.0,
        )

    def _propose_from_intent(
        self,
        intent_result: IntentResult,
        current_mode: ConversationMode,
        objecao_resolvida: bool,
    ) -> TransitionProposal:
        """Propõe transição baseado no intent."""

        # Obter modo sugerido pelo intent
        suggested_mode = INTENT_TO_MODE.get(intent_result.intent)

        # Caso especial: objeção resolvida em oferta → voltar pra discovery
        if objecao_resolvida and current_mode == ConversationMode.OFERTA:
            suggested_mode = ConversationMode.DISCOVERY

        # Se não há sugestão de modo, não transicionar
        if suggested_mode is None:
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=None,
                needs_confirmation=False,
                is_automatic=False,
                trigger="no_mode_suggestion",
                evidence=f"intent={intent_result.intent.value}",
                confidence=0.0,
            )

        # Se já está no modo sugerido, não transicionar
        if suggested_mode == current_mode:
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=None,
                needs_confirmation=False,
                is_automatic=False,
                trigger="already_in_mode",
                evidence=f"já em {current_mode.value}",
                confidence=0.0,
            )

        # Verificar se transição é permitida
        allowed = ALLOWED_TRANSITIONS.get(current_mode, set())
        if suggested_mode not in allowed:
            logger.warning(
                f"Transição não permitida: {current_mode.value} → {suggested_mode.value}"
            )
            return TransitionProposal(
                should_transition=False,
                from_mode=current_mode,
                to_mode=suggested_mode,
                needs_confirmation=False,
                is_automatic=False,
                trigger="not_allowed",
                evidence=f"transição não permitida na matriz",
                confidence=0.0,
            )

        # Verificar se requer confirmação
        transition_tuple = (current_mode, suggested_mode)
        needs_confirmation = transition_tuple in CONFIRMATION_REQUIRED
        is_automatic = transition_tuple in AUTOMATIC_TRANSITIONS

        return TransitionProposal(
            should_transition=True,
            from_mode=current_mode,
            to_mode=suggested_mode,
            needs_confirmation=needs_confirmation,
            is_automatic=is_automatic,
            trigger=f"intent_{intent_result.intent.value}",
            evidence=intent_result.evidence,
            confidence=intent_result.confidence,
        )
