"""
Classificador de contexto de mensagens.

Detecta o tipo de interacao para determinar delay apropriado.

Sprint 22 - Responsividade Inteligente
"""
import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.guardrails.types import OutboundContext, OutboundMethod

logger = logging.getLogger(__name__)


class ContextType(str, Enum):
    """Tipos de contexto de mensagem."""
    REPLY_DIRETA = "reply_direta"       # Resposta a pergunta do medico
    ACEITE_VAGA = "aceite_vaga"         # Medico aceitou/confirmou vaga
    CONFIRMACAO = "confirmacao"          # Confirmar dados/detalhes
    OFERTA_ATIVA = "oferta_ativa"       # Julia oferecendo vaga proativamente
    FOLLOWUP = "followup"                # Follow-up de conversa anterior
    CAMPANHA_FRIA = "campanha_fria"     # Primeiro contato/prospecao


@dataclass
class ContextClassification:
    """Resultado da classificacao de contexto."""
    tipo: ContextType
    prioridade: int  # 1 = mais urgente, 5 = menos urgente
    confianca: float  # 0.0 a 1.0
    razao: str


# Padroes para detectar aceite/confirmacao
PADROES_ACEITE = [
    r"\b(aceito|aceitar|fechado|fechou|bora|vamos|topo|topei)\b",
    r"\b(pode ser|pode reservar|reserva pra mim|quero)\b",
    r"\b(sim|ok|blz|beleza)\b",
    r"\b(confirmo|confirmado|confirma)\b",
]

PADROES_RECUSA = [
    r"\b(nao|não|nope|negativo)\b",
    r"\b(nao posso|não posso|infelizmente)\b",
    r"\b(passa essa|dessa vez nao|agora nao)\b",
]

PADROES_PERGUNTA = [
    r"\?",
    r"\b(qual|quanto|quando|onde|como|porque)\b",
    r"\b(me explica|me fala|me conta)\b",
]


def _detectar_aceite(mensagem: str) -> bool:
    """Detecta se mensagem indica aceite."""
    msg_lower = mensagem.lower()
    for padrao in PADROES_ACEITE:
        if re.search(padrao, msg_lower):
            # Verificar se nao tem negacao
            for neg in PADROES_RECUSA:
                if re.search(neg, msg_lower):
                    return False
            return True
    return False


def _detectar_pergunta(mensagem: str) -> bool:
    """Detecta se mensagem eh uma pergunta."""
    msg_lower = mensagem.lower()
    for padrao in PADROES_PERGUNTA:
        if re.search(padrao, msg_lower):
            return True
    return False


def _classificar_por_mensagem(mensagem: str) -> ContextClassification:
    """Classifica baseado no conteudo da mensagem."""
    # Aceite de vaga - PRIORIDADE MAXIMA
    if _detectar_aceite(mensagem):
        return ContextClassification(
            tipo=ContextType.ACEITE_VAGA,
            prioridade=1,
            confianca=0.9,
            razao="Detectado padrao de aceite/confirmacao"
        )

    # Pergunta direta - ALTA PRIORIDADE
    if _detectar_pergunta(mensagem):
        return ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.85,
            razao="Detectada pergunta do medico"
        )

    # Mensagem curta = provavelmente reply rapida
    if len(mensagem) < 50:
        return ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.7,
            razao="Mensagem curta indica conversa ativa"
        )

    # Default para reply direta com confianca moderada
    return ContextClassification(
        tipo=ContextType.REPLY_DIRETA,
        prioridade=2,
        confianca=0.6,
        razao="Classificacao padrao para mensagem inbound"
    )


def classificar_por_outbound_context(ctx: OutboundContext) -> ContextClassification:
    """
    Classifica contexto baseado em OutboundContext.

    Args:
        ctx: Contexto de outbound com method e metadados

    Returns:
        ContextClassification com tipo e prioridade
    """
    # REPLY = resposta a inbound
    if ctx.method == OutboundMethod.REPLY:
        return ContextClassification(
            tipo=ContextType.REPLY_DIRETA,
            prioridade=1,
            confianca=0.95,
            razao="OutboundMethod.REPLY indica resposta a inbound"
        )

    # FOLLOWUP = follow-up automatico
    if ctx.method == OutboundMethod.FOLLOWUP:
        return ContextClassification(
            tipo=ContextType.FOLLOWUP,
            prioridade=4,
            confianca=0.9,
            razao="OutboundMethod.FOLLOWUP"
        )

    # REACTIVATION = reativacao
    if ctx.method == OutboundMethod.REACTIVATION:
        return ContextClassification(
            tipo=ContextType.FOLLOWUP,
            prioridade=4,
            confianca=0.9,
            razao="OutboundMethod.REACTIVATION"
        )

    # CAMPAIGN = campanha fria
    if ctx.method == OutboundMethod.CAMPAIGN:
        return ContextClassification(
            tipo=ContextType.CAMPANHA_FRIA,
            prioridade=5,
            confianca=0.95,
            razao="OutboundMethod.CAMPAIGN"
        )

    # BUTTON/COMMAND = acao humana via Slack
    if ctx.method in (OutboundMethod.BUTTON, OutboundMethod.COMMAND, OutboundMethod.MANUAL):
        return ContextClassification(
            tipo=ContextType.OFERTA_ATIVA,
            prioridade=3,
            confianca=0.9,
            razao=f"OutboundMethod.{ctx.method.value} - acao humana"
        )

    # Default
    return ContextClassification(
        tipo=ContextType.OFERTA_ATIVA,
        prioridade=3,
        confianca=0.5,
        razao="Classificacao padrao"
    )


async def classificar_contexto(
    mensagem: Optional[str] = None,
    cliente_id: Optional[str] = None,
    outbound_ctx: Optional[OutboundContext] = None,
) -> ContextClassification:
    """
    Classifica contexto da mensagem para determinar delay.

    Estrategia:
    1. Se tem OutboundContext, usa method para classificar
    2. Se tem mensagem, analisa conteudo
    3. Fallback para reply_direta

    Args:
        mensagem: Texto da mensagem (opcional)
        cliente_id: ID do cliente (para futuro historico)
        outbound_ctx: Contexto de outbound se disponivel

    Returns:
        ContextClassification com tipo e prioridade
    """
    # Se tem contexto de outbound, usar method
    if outbound_ctx:
        classificacao = classificar_por_outbound_context(outbound_ctx)
        logger.debug(
            f"Classificado por OutboundContext: {classificacao.tipo.value} "
            f"(confianca: {classificacao.confianca})"
        )
        return classificacao

    # Se tem mensagem, analisar conteudo
    if mensagem:
        classificacao = _classificar_por_mensagem(mensagem)
        logger.debug(
            f"Classificado por mensagem: {classificacao.tipo.value} "
            f"(confianca: {classificacao.confianca})"
        )
        return classificacao

    # Fallback
    return ContextClassification(
        tipo=ContextType.REPLY_DIRETA,
        prioridade=2,
        confianca=0.5,
        razao="Fallback - sem mensagem ou contexto"
    )
