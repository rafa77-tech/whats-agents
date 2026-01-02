"""
Intent Detector - Detecta intenção do médico (NÃO decide modo).

Sprint 29 - Conversation Mode

IMPORTANTE: Este detector NÃO decide o modo.
Ele apenas identifica o que o médico está sinalizando.
A decisão passa pela matriz ALLOWED_TRANSITIONS.
"""
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DetectedIntent(Enum):
    """Intenção detectada na mensagem do médico."""
    INTERESSE_VAGA = "interesse_vaga"
    DUVIDA_PERFIL = "duvida_perfil"
    PRONTO_FECHAR = "pronto_fechar"
    VOLTANDO = "voltando"
    NEUTRO = "neutro"
    OBJECAO = "objecao"
    RECUSA = "recusa"


# Keywords por tipo de intent
INTERESSE_KEYWORDS = [
    r"\binteress",
    r"\bconta mais\b",
    r"\bquero saber\b",
    r"\btem vaga\b",
    r"\bquanto paga\b",
    r"\bvalor\b",
    r"\bonde\b.*\bhospital\b",
    r"\bqual\b.*\bplant[aã]o\b",
    r"\bquando\b.*\bvaga\b",
    r"\bpode me mandar\b",
    r"\bquero ver\b",
    r"\bme manda\b.*\bop[cç][oõ]es\b",
    r"\btem algo\b",
    r"\btem plant[aã]o\b",
]

FECHAR_KEYWORDS = [
    r"\bquero\b.*\breservar\b",
    r"\bpode reservar\b",
    r"\bfecha\b",
    r"\bconfirma\b",
    r"\baceito\b",
    r"\bvou pegar\b",
    r"\bquero esse\b",
    r"\bpode ser\b.*\besse\b",
    r"\bfico com\b",
]

DUVIDA_KEYWORDS = [
    r"\bcomo funciona\b",
    r"\bo que [eé] isso\b",
    r"\bn[aã]o entendi\b",
    r"\bexplica\b",
    r"\bquem [eé] voc[eê]\b",
    r"\bque empresa\b",
    r"\b[eé] real\b",
    r"\b[eé] confi[aá]vel\b",
    r"\bque revoluna\b",
]

VOLTANDO_KEYWORDS = [
    r"^oi\b",
    r"\bvoltei\b",
    r"\blembrei\b",
    r"\bdesculpa a demora\b",
    r"\bsumido\b",
    r"\btava ocupado\b",
    r"\bestava viajando\b",
    r"\bfui viajar\b",
]

OBJECAO_KEYWORDS = [
    r"\bn[aã]o sei\b",
    r"\bpreciso pensar\b",
    r"\bdepois\b",
    r"\bagora n[aã]o\b",
    r"\bestou ocupado\b",
    r"\bmuito longe\b",
    r"\bvalor baixo\b",
    r"\bpaga pouco\b",
    r"\bvou ver\b",
    r"\btalvez\b",
]

RECUSA_KEYWORDS = [
    r"\bn[aã]o quero\b",
    r"\bn[aã]o tenho interesse\b",
    r"\bpara de mandar\b",
    r"\bn[aã]o me liga\b",
    r"\btira meu n[uú]mero\b",
    r"\bn[aã]o\b.*\bobrigado\b",
    r"\bsair\b.*\blista\b",
    r"\bn[aã]o precisa\b.*\bmandar\b",
    r"\bremove\b.*\bnumero\b",
]


@dataclass
class IntentResult:
    """Resultado da detecção de intent."""
    intent: DetectedIntent
    confidence: float
    evidence: str


def _check_keywords(text: str, patterns: list[str]) -> tuple[bool, str]:
    """Verifica se texto contém algum dos patterns."""
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return True, match.group()
    return False, ""


class IntentDetector:
    """
    Detecta intenção do médico na mensagem.

    IMPORTANTE: Este detector NÃO decide o modo.
    Ele apenas identifica o que o médico está sinalizando.
    """

    def detect(self, mensagem: str) -> IntentResult:
        """
        Detecta intenção na mensagem.

        Args:
            mensagem: Texto da mensagem do médico

        Returns:
            IntentResult com intent detectado
        """
        if not mensagem or not mensagem.strip():
            return IntentResult(
                intent=DetectedIntent.NEUTRO,
                confidence=0.0,
                evidence="mensagem vazia",
            )

        # Ordem importa: mais específico primeiro

        # 1. Recusa (mais forte)
        found, match = _check_keywords(mensagem, RECUSA_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.RECUSA,
                confidence=0.9,
                evidence=f"recusa: '{match}'",
            )

        # 2. Pronto para fechar
        found, match = _check_keywords(mensagem, FECHAR_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.PRONTO_FECHAR,
                confidence=0.85,
                evidence=f"pronto para fechar: '{match}'",
            )

        # 3. Objeção
        found, match = _check_keywords(mensagem, OBJECAO_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.OBJECAO,
                confidence=0.7,
                evidence=f"objeção: '{match}'",
            )

        # 4. Interesse em vaga
        found, match = _check_keywords(mensagem, INTERESSE_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.INTERESSE_VAGA,
                confidence=0.75,
                evidence=f"interesse: '{match}'",
            )

        # 5. Dúvida sobre perfil
        found, match = _check_keywords(mensagem, DUVIDA_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.DUVIDA_PERFIL,
                confidence=0.7,
                evidence=f"dúvida: '{match}'",
            )

        # 6. Voltando após silêncio
        found, match = _check_keywords(mensagem, VOLTANDO_KEYWORDS)
        if found:
            return IntentResult(
                intent=DetectedIntent.VOLTANDO,
                confidence=0.6,
                evidence=f"voltando: '{match}'",
            )

        # 7. Neutro (default)
        return IntentResult(
            intent=DetectedIntent.NEUTRO,
            confidence=0.5,
            evidence="sem sinal claro",
        )
