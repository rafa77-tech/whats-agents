"""
Bootstrap de Modo - Determina modo inicial de forma determinística.

Sprint 29 - Conversation Mode

Problema que resolve: Inbound que deveria começar em OFERTA
entra como DISCOVERY, fazendo Julia parecer "lerda".

Exemplo perigoso:
"Oi, sou o Dr João, vi uma vaga de anestesia com vocês"
# Se cair como DISCOVERY por default, Julia parece desatenta.
"""

import logging
import re
from typing import Optional

from .types import ConversationMode

logger = logging.getLogger(__name__)


# Patterns que indicam interesse direto em vaga
INBOUND_INTEREST_PATTERNS = [
    r"\bvaga\b",
    r"\bplant[aã]o\b",
    r"\bescala\b",
    r"\btrabalhar\b.*\bvoc[eê]s\b",
    r"\bvi\b.*\bvaga\b",
    r"\binteress[ae]\b.*\btrabalhar\b",
    r"\bquero\b.*\bplant[aã]o\b",
    r"\btem\b.*\bplant[aã]o\b",
    r"\bprocurando\b.*\bvaga\b",
]


def bootstrap_mode(
    primeira_mensagem: str,
    origem: str,
    campaign_mode: Optional[str] = None,
) -> ConversationMode:
    """
    Determina modo inicial de forma determinística.

    Args:
        primeira_mensagem: Primeira mensagem do médico
        origem: Origem da conversa ("inbound", "campaign:<id>", "manual")
        campaign_mode: Modo da campanha (se origem for campanha)

    Returns:
        ConversationMode inicial
    """
    # 1. Se veio de campanha, herda o modo da campanha
    if origem.startswith("campaign:") and campaign_mode:
        try:
            mode = ConversationMode(campaign_mode)
            logger.info(f"Bootstrap: campanha → {mode.value}")
            return mode
        except ValueError:
            logger.warning(f"Modo de campanha inválido: {campaign_mode}")

    # 2. Inbound com sinal claro de interesse → OFERTA
    if origem == "inbound":
        mensagem_lower = primeira_mensagem.lower()
        for pattern in INBOUND_INTEREST_PATTERNS:
            if re.search(pattern, mensagem_lower):
                logger.info(f"Bootstrap: inbound com interesse → oferta (pattern: {pattern})")
                return ConversationMode.OFERTA

    # 3. Default conservador → DISCOVERY
    logger.info("Bootstrap: default → discovery")
    return ConversationMode.DISCOVERY


def get_mode_source(
    origem: str,
    campaign_id: Optional[str] = None,
) -> str:
    """
    Gera string de mode_source para persistência.

    Args:
        origem: Tipo de origem ("inbound", "campaign", "manual")
        campaign_id: ID da campanha (se origem for campaign)

    Returns:
        String no formato: "inbound", "campaign:<id>", "manual"
    """
    if origem == "campaign" and campaign_id:
        return f"campaign:{campaign_id}"
    return origem


def should_start_as_reactivation(
    dias_desde_ultima_mensagem: int,
    tinha_conversa_anterior: bool,
) -> bool:
    """
    Verifica se conversa deve começar como REATIVAÇÃO.

    Args:
        dias_desde_ultima_mensagem: Dias desde última interação
        tinha_conversa_anterior: Se já teve conversa antes

    Returns:
        True se deve começar como REATIVAÇÃO
    """
    if not tinha_conversa_anterior:
        return False

    # Se mais de 7 dias desde última conversa, é reativação
    return dias_desde_ultima_mensagem >= 7
