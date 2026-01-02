"""
Validador de resposta para garantir que Julia não desvia.

Sprint 29 - Conversation Mode

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
Este validador detecta padrões proibidos nas respostas:
1. Confirmação de reserva (Julia não reserva)
2. Citação de valores (Julia não negocia)
3. Negociação de termos (Julia não negocia)
"""
import re
import logging
from typing import Optional, Tuple

from .mode_logging import log_violation_attempt

logger = logging.getLogger(__name__)


# Padrões proibidos com tipo de violação
PADROES_PROIBIDOS: list[Tuple[str, str]] = [
    # confirm_booking - Julia não confirma reservas
    (r"(?i)reserv(ei|ado|a) (pra|para) voc[êe]", "confirm_booking"),
    (r"(?i)confirm(ado|ei|o) (seu|o) plant[aã]o", "confirm_booking"),
    (r"(?i)t[aá]\s+(fechado|confirm)", "confirm_booking"),
    (r"(?i)seu\s+plant[aã]o\s+(j[aá]|foi)\s+", "confirm_booking"),

    # quote_price - Julia não cita valores específicos
    (r"(?i)paga\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)consigo\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)valor\s+(é|de|seria)\s+R?\$?\s*\d+", "quote_price"),
    (r"(?i)R?\$\s*\d+[\.,]?\d*\s*(reais|por|a hora|por hora|noite|diurno)", "quote_price"),

    # negotiate_terms - Julia não negocia
    (r"(?i)d[aá]\s+pra\s+(sub|melhora)ir", "negotiate_terms"),
    (r"(?i)consigo\s+melhorar", "negotiate_terms"),
    (r"(?i)posso\s+negociar", "negotiate_terms"),
    (r"(?i)valor\s+m[ií]nimo", "negotiate_terms"),
]


def validar_resposta_julia(
    resposta: str,
    mode: str,
    conversa_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Valida se a resposta da Julia não contém desvios.

    Esta função é um guardrail de segunda linha. Se o LLM
    conseguir gerar uma resposta proibida mesmo com os
    constraints no prompt, esta função detecta e bloqueia.

    Args:
        resposta: Texto da resposta gerada
        mode: Modo atual da conversa
        conversa_id: ID da conversa (para logging)

    Returns:
        (is_valid, violation_type):
        - is_valid: True se resposta é válida
        - violation_type: Tipo de violação se inválida (None se válida)
    """
    if not resposta:
        return True, None

    for padrao, violacao in PADROES_PROIBIDOS:
        if re.search(padrao, resposta):
            logger.warning(
                f"VIOLAÇÃO DETECTADA: {violacao} em modo {mode}",
                extra={
                    "event": "response_violation",
                    "violacao": violacao,
                    "padrao": padrao,
                    "mode": mode,
                    "conversa_id": conversa_id,
                    "resposta_truncada": resposta[:100],
                }
            )

            # Log estruturado para auditoria
            if conversa_id:
                log_violation_attempt(
                    conversa_id=conversa_id,
                    mode=mode,
                    violation_type="claim",
                    attempted=violacao,
                )

            return False, violacao

    return True, None


def sanitizar_resposta_julia(
    resposta: str,
    mode: str,
    conversa_id: Optional[str] = None,
) -> str:
    """
    Sanitiza resposta, removendo ou substituindo padrões proibidos.

    NOTA: Prefira rejeitar a resposta e regenerar em vez de sanitizar.
    Esta função é para casos onde precisamos de fallback.

    Args:
        resposta: Texto da resposta gerada
        mode: Modo atual da conversa
        conversa_id: ID da conversa (para logging)

    Returns:
        Resposta sanitizada
    """
    if not resposta:
        return resposta

    resposta_sanitizada = resposta

    for padrao, violacao in PADROES_PROIBIDOS:
        if re.search(padrao, resposta_sanitizada):
            # Substituir por texto genérico
            if violacao == "quote_price":
                resposta_sanitizada = re.sub(
                    padrao,
                    "o valor você negocia direto com o responsável",
                    resposta_sanitizada,
                )
            elif violacao == "confirm_booking":
                resposta_sanitizada = re.sub(
                    padrao,
                    "vou te conectar com o responsável",
                    resposta_sanitizada,
                )
            elif violacao == "negotiate_terms":
                resposta_sanitizada = re.sub(
                    padrao,
                    "isso você acerta direto com quem oferece",
                    resposta_sanitizada,
                )

            logger.info(
                f"Resposta sanitizada: {violacao}",
                extra={
                    "event": "response_sanitized",
                    "violacao": violacao,
                    "mode": mode,
                    "conversa_id": conversa_id,
                }
            )

    return resposta_sanitizada


# Mensagem de fallback quando resposta é inválida
FALLBACK_RESPONSES = {
    "confirm_booking": (
        "Posso te colocar em contato com o responsável pela vaga? "
        "Ele vai te passar os detalhes e confirmar tudo com você."
    ),
    "quote_price": (
        "O valor você negocia direto com o responsável da vaga. "
        "Quer que eu te conecte com ele?"
    ),
    "negotiate_terms": (
        "As condições você acerta direto com quem tá oferecendo. "
        "Posso passar seu contato pra ele te ligar?"
    ),
}


def get_fallback_response(violation_type: str) -> str:
    """
    Retorna resposta de fallback para tipo de violação.

    Args:
        violation_type: Tipo de violação detectada

    Returns:
        Resposta de fallback apropriada
    """
    return FALLBACK_RESPONSES.get(
        violation_type,
        "Deixa eu te conectar com o responsável pela vaga, ele vai te ajudar com os detalhes.",
    )
