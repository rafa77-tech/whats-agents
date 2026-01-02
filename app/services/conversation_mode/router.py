"""
Mode Router - Orquestra detecção, proposta e validação de transições.

Sprint 29 - Conversation Mode

3 CAMADAS:
1. IntentDetector - Detecta intenção do médico
2. TransitionProposer - Propõe transição
3. TransitionValidator - Valida e decide

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não confirma reservas
- Conecta médico com responsável da vaga
- Micro-confirmação é sobre PONTE, não reserva
"""
import logging
from datetime import datetime
from typing import Optional

from .types import ConversationMode, ModeInfo
from .intents import IntentDetector, DetectedIntent
from .proposer import TransitionProposer, TransitionProposal
from .validator import TransitionValidator, TransitionDecision, ValidationResult
from .repository import (
    get_conversation_mode,
    set_conversation_mode,
    set_pending_transition,
    clear_pending_transition,
)

logger = logging.getLogger(__name__)


class ModeRouter:
    """
    Orquestra o fluxo completo de transição de modo.

    3 camadas:
    1. IntentDetector - Detecta intenção do médico
    2. TransitionProposer - Propõe transição
    3. TransitionValidator - Valida e decide

    Suporta micro-confirmação para transições críticas.
    """

    def __init__(self):
        self.intent_detector = IntentDetector()
        self.proposer = TransitionProposer()
        self.validator = TransitionValidator()

    async def process(
        self,
        conversa_id: str,
        mensagem: str,
        last_message_at: Optional[datetime] = None,
        ponte_feita: bool = False,
        objecao_resolvida: bool = False,
    ) -> ModeInfo:
        """
        Processa mensagem e decide transição de modo.

        Args:
            conversa_id: ID da conversa
            mensagem: Texto da mensagem do médico
            last_message_at: Timestamp da última mensagem
            ponte_feita: Se ponte foi feita com responsável (Julia é intermediária)
            objecao_resolvida: Se objeção foi resolvida

        Returns:
            ModeInfo atualizado (ou atual se sem mudança)
        """
        # 1. Buscar modo atual + pending
        current_info = await get_conversation_mode(conversa_id)
        current_mode = current_info.mode

        # 2. Detectar intent (AJUSTE 2)
        intent_result = self.intent_detector.detect(mensagem)
        logger.debug(
            f"Intent detectado: {intent_result.intent.value} "
            f"(confidence={intent_result.confidence:.2f})"
        )

        # 3. Propor transição
        proposal = self.proposer.propose(
            intent_result=intent_result,
            current_mode=current_mode,
            last_message_at=last_message_at,
            ponte_feita=ponte_feita,
            objecao_resolvida=objecao_resolvida,
        )

        # 4. Verificar se mensagem confirma pending
        mensagem_confirma = self._check_confirmation(
            mensagem, intent_result, current_info.pending_transition
        )

        # 5. Validar transição
        validation = self.validator.validate(
            proposal=proposal,
            pending_transition=current_info.pending_transition,
            pending_transition_at=current_info.pending_transition_at,
            last_transition_at=current_info.updated_at,
            mensagem_confirma=mensagem_confirma,
        )

        # 6. Aplicar decisão
        return await self._apply_decision(
            conversa_id=conversa_id,
            current_info=current_info,
            validation=validation,
            proposal=proposal,
        )

    def _check_confirmation(
        self,
        mensagem: str,
        intent_result,
        pending_transition: Optional[ConversationMode],
    ) -> bool:
        """
        Verifica se mensagem confirma pending_transition.

        Confirmação acontece quando:
        - Há pending_transition
        - Mensagem não é recusa/objeção
        - Mensagem indica continuidade ou interesse
        """
        if not pending_transition:
            return False

        # Recusa ou objeção = não confirma
        if intent_result.intent in (DetectedIntent.RECUSA, DetectedIntent.OBJECAO):
            return False

        # Interesse explícito = confirma
        if intent_result.intent in (
            DetectedIntent.INTERESSE_VAGA,
            DetectedIntent.PRONTO_FECHAR,
        ):
            return True

        # Resposta neutra curta = provavelmente confirma
        # (ex: "sim", "ok", "pode ser", "tenho")
        mensagem_lower = mensagem.lower().strip()
        confirma_keywords = [
            "sim", "ok", "pode", "tenho", "blz", "beleza",
            "pode ser", "aham", "isso", "claro", "tá bom",
            "ta bom", "fechado", "bora", "vamo", "vamos",
            "quero", "manda", "show",
        ]
        for kw in confirma_keywords:
            if kw in mensagem_lower:
                return True

        return False

    async def _apply_decision(
        self,
        conversa_id: str,
        current_info: ModeInfo,
        validation: ValidationResult,
        proposal: TransitionProposal,
    ) -> ModeInfo:
        """Aplica a decisão do validador."""

        if validation.decision == TransitionDecision.APPLY:
            # Aplicar transição
            await set_conversation_mode(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                reason=f"{proposal.trigger}: {proposal.evidence}",
            )
            # Limpar pending se houver
            if current_info.pending_transition:
                await clear_pending_transition(conversa_id)

            return ModeInfo(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                updated_at=datetime.utcnow(),
                updated_reason=validation.reason,
            )

        elif validation.decision == TransitionDecision.PENDING:
            # Salvar pending_transition
            await set_pending_transition(
                conversa_id=conversa_id,
                pending_mode=validation.pending_mode,
            )
            return current_info  # Modo não muda ainda

        elif validation.decision == TransitionDecision.CONFIRM:
            # Confirmar pending → aplicar transição
            await set_conversation_mode(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                reason="micro-confirmação aceita",
            )
            await clear_pending_transition(conversa_id)

            return ModeInfo(
                conversa_id=conversa_id,
                mode=validation.final_mode,
                updated_at=datetime.utcnow(),
                updated_reason=validation.reason,
            )

        elif validation.decision == TransitionDecision.CANCEL:
            # Cancelar pending
            await clear_pending_transition(conversa_id)
            return current_info  # Modo não muda

        else:  # REJECT
            return current_info  # Modo não muda


# Singleton para uso global
_router: Optional[ModeRouter] = None


def get_mode_router() -> ModeRouter:
    """Retorna instância singleton do ModeRouter."""
    global _router
    if _router is None:
        _router = ModeRouter()
    return _router
