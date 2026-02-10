"""
Testes para Mode Router (3 camadas).

Sprint 29 - Conversation Mode
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.conversation_mode.types import ConversationMode
from app.services.conversation_mode.intents import (
    DetectedIntent,
    IntentResult,
    IntentDetector,
)
from app.services.conversation_mode.proposer import (
    TransitionProposer,
    TransitionProposal,
    ALLOWED_TRANSITIONS,
    CONFIRMATION_REQUIRED,
)
from app.services.conversation_mode.validator import (
    TransitionValidator,
    TransitionDecision,
)
from app.services.conversation_mode.bootstrap import (
    bootstrap_mode,
    get_mode_source,
)


# =============================================================================
# TESTES: Intent Detector
# =============================================================================
class TestIntentDetector:
    """Testes para IntentDetector."""

    def test_detect_interesse_vaga_tem_vaga(self):
        """Detecta interesse quando médico pergunta 'tem vaga'."""
        detector = IntentDetector()
        result = detector.detect("Tem vaga de cardiologia?")
        assert result.intent == DetectedIntent.INTERESSE_VAGA
        assert result.confidence >= 0.7

    def test_detect_interesse_vaga_valor(self):
        """Detecta interesse quando médico pergunta sobre valor."""
        detector = IntentDetector()
        result = detector.detect("Quanto paga o plantão?")
        assert result.intent == DetectedIntent.INTERESSE_VAGA
        assert "valor" in result.evidence.lower() or "paga" in result.evidence.lower()

    def test_detect_pronto_fechar(self):
        """Detecta pronto para fechar."""
        detector = IntentDetector()
        result = detector.detect("Quero reservar esse plantão")
        assert result.intent == DetectedIntent.PRONTO_FECHAR
        assert result.confidence >= 0.8

    def test_detect_objecao(self):
        """Detecta objeção."""
        detector = IntentDetector()
        result = detector.detect("Preciso pensar mais")
        assert result.intent == DetectedIntent.OBJECAO

    def test_detect_recusa(self):
        """Detecta recusa."""
        detector = IntentDetector()
        result = detector.detect("Não quero mais receber mensagens")
        assert result.intent == DetectedIntent.RECUSA
        assert result.confidence >= 0.9

    def test_detect_duvida_perfil(self):
        """Detecta dúvida sobre perfil."""
        detector = IntentDetector()
        result = detector.detect("Como funciona esse serviço?")
        assert result.intent == DetectedIntent.DUVIDA_PERFIL

    def test_detect_voltando(self):
        """Detecta médico voltando."""
        detector = IntentDetector()
        result = detector.detect("Oi, voltei!")
        assert result.intent == DetectedIntent.VOLTANDO

    def test_detect_neutro_mensagem_generica(self):
        """Detecta neutro para mensagem genérica."""
        detector = IntentDetector()
        result = detector.detect("Tudo bem por aí?")
        assert result.intent == DetectedIntent.NEUTRO

    def test_detect_neutro_mensagem_vazia(self):
        """Detecta neutro para mensagem vazia."""
        detector = IntentDetector()
        result = detector.detect("")
        assert result.intent == DetectedIntent.NEUTRO
        assert result.confidence == 0.0

    def test_recusa_tem_prioridade_sobre_interesse(self):
        """Recusa tem prioridade sobre interesse."""
        detector = IntentDetector()
        # Mesmo com palavra de interesse, recusa prevalece
        result = detector.detect("Não quero saber de vaga, obrigado")
        assert result.intent == DetectedIntent.RECUSA


# =============================================================================
# TESTES: Transition Proposer
# =============================================================================
class TestTransitionProposer:
    """Testes para TransitionProposer."""

    def test_discovery_to_oferta_needs_confirmation(self):
        """discovery → oferta requer confirmação."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.INTERESSE_VAGA,
            confidence=0.8,
            evidence="tem vaga",
        )
        proposal = proposer.propose(intent, ConversationMode.DISCOVERY)

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.OFERTA
        assert proposal.needs_confirmation is True
        assert proposal.is_automatic is False

    def test_followup_to_oferta_needs_confirmation(self):
        """followup → oferta requer confirmação."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.INTERESSE_VAGA,
            confidence=0.8,
            evidence="tem vaga",
        )
        proposal = proposer.propose(intent, ConversationMode.FOLLOWUP)

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.OFERTA
        assert proposal.needs_confirmation is True

    def test_oferta_to_followup_is_automatic(self):
        """oferta → followup é automático (ponte feita)."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence="",
        )
        proposal = proposer.propose(
            intent,
            ConversationMode.OFERTA,
            ponte_feita=True,
        )

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.FOLLOWUP
        assert proposal.is_automatic is True
        assert proposal.needs_confirmation is False

    def test_silencio_7d_triggers_reativacao(self):
        """Silêncio de 7+ dias dispara REATIVAÇÃO."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence="",
        )
        last_msg = datetime.now(timezone.utc) - timedelta(days=10)

        proposal = proposer.propose(
            intent,
            ConversationMode.DISCOVERY,
            last_message_at=last_msg,
        )

        assert proposal.should_transition is True
        assert proposal.to_mode == ConversationMode.REATIVACAO
        assert proposal.is_automatic is True
        assert "silêncio" in proposal.evidence

    def test_forbidden_transition_blocked(self):
        """Transição não permitida é bloqueada."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.VOLTANDO,
            confidence=0.7,
            evidence="voltei",
        )
        # DISCOVERY → FOLLOWUP não está em ALLOWED_TRANSITIONS
        proposal = proposer.propose(intent, ConversationMode.DISCOVERY)

        assert proposal.should_transition is False
        assert proposal.trigger == "not_allowed"

    def test_already_in_mode_no_transition(self):
        """Já está no modo sugerido, não transiciona."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.INTERESSE_VAGA,
            confidence=0.8,
            evidence="tem vaga",
        )
        # Já está em OFERTA, interesse sugere OFERTA
        proposal = proposer.propose(intent, ConversationMode.OFERTA)

        assert proposal.should_transition is False
        assert proposal.trigger == "already_in_mode"

    def test_recusa_no_mode_suggestion(self):
        """Recusa não sugere mudança de modo."""
        proposer = TransitionProposer()
        intent = IntentResult(
            intent=DetectedIntent.RECUSA,
            confidence=0.9,
            evidence="não quero",
        )
        proposal = proposer.propose(intent, ConversationMode.DISCOVERY)

        assert proposal.should_transition is False
        assert proposal.trigger == "no_mode_suggestion"


# =============================================================================
# TESTES: Transition Validator
# =============================================================================
class TestTransitionValidator:
    """Testes para TransitionValidator."""

    def test_pending_confirmed_applies(self):
        """Pending confirmada aplica transição."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=False,
            from_mode=ConversationMode.DISCOVERY,
            to_mode=None,
            needs_confirmation=False,
            is_automatic=False,
            trigger="none",
            evidence="",
            confidence=0.0,
        )
        result = validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.now(timezone.utc),
            mensagem_confirma=True,
        )

        assert result.decision == TransitionDecision.CONFIRM
        assert result.final_mode == ConversationMode.OFERTA

    def test_pending_not_confirmed_cancels(self):
        """Pending não confirmada cancela."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=False,
            from_mode=ConversationMode.DISCOVERY,
            to_mode=None,
            needs_confirmation=False,
            is_automatic=False,
            trigger="none",
            evidence="",
            confidence=0.0,
        )
        result = validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.now(timezone.utc),
            mensagem_confirma=False,
        )

        assert result.decision == TransitionDecision.CANCEL
        assert result.final_mode == ConversationMode.DISCOVERY

    def test_pending_timeout_cancels(self):
        """Pending expirada (timeout) cancela."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=False,
            from_mode=ConversationMode.DISCOVERY,
            to_mode=None,
            needs_confirmation=False,
            is_automatic=False,
            trigger="none",
            evidence="",
            confidence=0.0,
        )
        # 60 minutos atrás (timeout é 30 min)
        result = validator.validate(
            proposal=proposal,
            pending_transition=ConversationMode.OFERTA,
            pending_transition_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            mensagem_confirma=False,
        )

        assert result.decision == TransitionDecision.CANCEL
        assert "timeout" in result.reason

    def test_automatic_transition_applies(self):
        """Transição automática é aplicada imediatamente."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=True,
            from_mode=ConversationMode.OFERTA,
            to_mode=ConversationMode.FOLLOWUP,
            needs_confirmation=False,
            is_automatic=True,
            trigger="ponte_feita",
            evidence="ponte feita",
            confidence=1.0,
        )
        result = validator.validate(proposal=proposal)

        assert result.decision == TransitionDecision.APPLY
        assert result.final_mode == ConversationMode.FOLLOWUP

    def test_needs_confirmation_creates_pending(self):
        """Transição que requer confirmação cria pending."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=True,
            from_mode=ConversationMode.DISCOVERY,
            to_mode=ConversationMode.OFERTA,
            needs_confirmation=True,
            is_automatic=False,
            trigger="intent_interesse_vaga",
            evidence="tem vaga",
            confidence=0.8,
        )
        result = validator.validate(proposal=proposal)

        assert result.decision == TransitionDecision.PENDING
        assert result.final_mode == ConversationMode.DISCOVERY  # Não muda ainda
        assert result.pending_mode == ConversationMode.OFERTA

    def test_cooldown_rejects_transition(self):
        """Cooldown rejeita transição."""
        validator = TransitionValidator()
        proposal = TransitionProposal(
            should_transition=True,
            from_mode=ConversationMode.DISCOVERY,
            to_mode=ConversationMode.OFERTA,
            needs_confirmation=False,
            is_automatic=False,
            trigger="test",
            evidence="test",
            confidence=0.8,
        )
        # Última transição foi 2 minutos atrás (cooldown é 5 min)
        result = validator.validate(
            proposal=proposal,
            last_transition_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )

        assert result.decision == TransitionDecision.REJECT
        assert "cooldown" in result.reason


# =============================================================================
# TESTES: Bootstrap
# =============================================================================
class TestBootstrap:
    """Testes para bootstrap de modo."""

    def test_bootstrap_inbound_with_vaga(self):
        """Inbound com 'vaga' começa em OFERTA."""
        mode = bootstrap_mode(
            primeira_mensagem="Oi, vi uma vaga de cardiologia",
            origem="inbound",
        )
        assert mode == ConversationMode.OFERTA

    def test_bootstrap_inbound_with_plantao(self):
        """Inbound com 'plantão' começa em OFERTA."""
        mode = bootstrap_mode(
            primeira_mensagem="Tem plantão disponível?",
            origem="inbound",
        )
        assert mode == ConversationMode.OFERTA

    def test_bootstrap_inbound_cold(self):
        """Inbound sem interesse claro começa em DISCOVERY."""
        mode = bootstrap_mode(
            primeira_mensagem="Oi, tudo bem?",
            origem="inbound",
        )
        assert mode == ConversationMode.DISCOVERY

    def test_bootstrap_campaign_inherits_mode(self):
        """Campanha herda modo configurado."""
        mode = bootstrap_mode(
            primeira_mensagem="qualquer coisa",
            origem="campaign:abc-123",
            campaign_mode="oferta",
        )
        assert mode == ConversationMode.OFERTA

    def test_bootstrap_campaign_invalid_mode_falls_to_discovery(self):
        """Campanha com modo inválido cai para DISCOVERY."""
        mode = bootstrap_mode(
            primeira_mensagem="qualquer coisa",
            origem="campaign:abc-123",
            campaign_mode="modo_invalido",
        )
        assert mode == ConversationMode.DISCOVERY

    def test_get_mode_source_campaign(self):
        """get_mode_source formata origem de campanha."""
        source = get_mode_source("campaign", "abc-123")
        assert source == "campaign:abc-123"

    def test_get_mode_source_inbound(self):
        """get_mode_source mantém inbound."""
        source = get_mode_source("inbound")
        assert source == "inbound"


# =============================================================================
# TESTES: Matriz de Transições
# =============================================================================
class TestTransitionMatrix:
    """Testes para matriz de transições."""

    def test_discovery_can_go_to_oferta(self):
        """DISCOVERY pode ir para OFERTA."""
        allowed = ALLOWED_TRANSITIONS[ConversationMode.DISCOVERY]
        assert ConversationMode.OFERTA in allowed

    def test_discovery_cannot_go_to_followup(self):
        """DISCOVERY NÃO pode ir direto para FOLLOWUP."""
        allowed = ALLOWED_TRANSITIONS[ConversationMode.DISCOVERY]
        assert ConversationMode.FOLLOWUP not in allowed

    def test_oferta_can_go_to_followup(self):
        """OFERTA pode ir para FOLLOWUP."""
        allowed = ALLOWED_TRANSITIONS[ConversationMode.OFERTA]
        assert ConversationMode.FOLLOWUP in allowed

    def test_oferta_can_retreat_to_discovery(self):
        """OFERTA pode recuar para DISCOVERY (objeção)."""
        allowed = ALLOWED_TRANSITIONS[ConversationMode.OFERTA]
        assert ConversationMode.DISCOVERY in allowed

    def test_reativacao_can_go_anywhere(self):
        """REATIVAÇÃO pode ir para qualquer modo."""
        allowed = ALLOWED_TRANSITIONS[ConversationMode.REATIVACAO]
        assert ConversationMode.DISCOVERY in allowed
        assert ConversationMode.OFERTA in allowed
        assert ConversationMode.FOLLOWUP in allowed

    def test_discovery_to_oferta_requires_confirmation(self):
        """discovery → oferta está em CONFIRMATION_REQUIRED."""
        assert (ConversationMode.DISCOVERY, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED

    def test_followup_to_oferta_requires_confirmation(self):
        """followup → oferta está em CONFIRMATION_REQUIRED."""
        assert (ConversationMode.FOLLOWUP, ConversationMode.OFERTA) in CONFIRMATION_REQUIRED
