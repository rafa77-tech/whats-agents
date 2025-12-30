"""
Classificador de erros de provider para diagnóstico operacional.

Sprint 23 - Produção Ready: Distinguir FAILED_VALIDATION de FAILED_PROVIDER.

Este módulo analisa erros da Evolution API/Baileys e classifica em:
- FAILED_VALIDATION: Número inválido, inexistente, não está no WhatsApp
- FAILED_BANNED: Número banido, bloqueado pelo usuário, spam
- FAILED_PROVIDER: Erro real de infra (timeout, 5xx, rede)

Isso permite métricas distintas:
- % FAILED_VALIDATION por campanha → qualidade do target set
- % FAILED_BANNED por janela → risco reputacional
- % FAILED_PROVIDER por hora → estabilidade do provider
"""
import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

from app.services.guardrails.types import SendOutcome

logger = logging.getLogger(__name__)


@dataclass
class ClassifiedError:
    """Resultado da classificação de erro."""
    outcome: SendOutcome
    provider_error_code: str  # Código curto (ex: "invalid_number", "blocked_by_user")
    provider_error_raw: str   # Trecho do erro original (truncado)


# Padrões para números inválidos/inexistentes (FAILED_VALIDATION)
VALIDATION_PATTERNS = [
    # Número inválido
    r"invalid.*number",
    r"not.*valid.*number",
    r"invalid.*jid",
    r"invalid.*phone",
    r"número.*inválido",
    # Número não existe no WhatsApp
    r"not.*registered",
    r"não.*registrado",
    r"does.*not.*exist",
    r"doesn.*t.*exist",
    r"not.*on.*whatsapp",
    r"não.*está.*no.*whatsapp",
    r"number.*not.*found",
    r"user.*not.*found",
    # JID/formato inválido
    r"malformed.*jid",
    r"bad.*jid",
    r"invalid.*remote.*jid",
    # Baileys específico
    r"jid.*required",
    r"404.*not.*found",
    r"number.*doesn.*t.*have.*whatsapp",
]

# Padrões para números banidos/bloqueados (FAILED_BANNED)
BANNED_PATTERNS = [
    # Bloqueio pelo usuário
    r"blocked.*by.*user",
    r"user.*blocked",
    r"bloqueado.*pelo.*usuário",
    r"recipient.*blocked",
    # Banimento por spam
    r"banned",
    r"spam",
    r"restricted",
    r"account.*restricted",
    r"conta.*restrita",
    # Privacy settings
    r"privacy.*settings",
    r"configurações.*privacidade",
    r"cannot.*send.*message.*to.*this.*user",
    # Rate limit do WhatsApp (diferente do nosso)
    r"too.*many.*requests.*to.*this.*number",
    r"message.*rate.*exceeded",
    # Baileys específico
    r"403.*forbidden.*blocked",
    r"recipient.*not.*available",
]

# Padrões de erros de infra (FAILED_PROVIDER - fallback)
PROVIDER_PATTERNS = [
    r"timeout",
    r"timed.*out",
    r"connection.*refused",
    r"network.*error",
    r"socket.*error",
    r"5\d\d",  # 5xx status codes
    r"502.*bad.*gateway",
    r"503.*service.*unavailable",
    r"504.*gateway.*timeout",
    r"evolution.*api.*unavailable",
    r"circuit.*open",
]


def _match_patterns(error_text: str, patterns: list[str]) -> Optional[str]:
    """
    Verifica se o texto de erro bate com algum padrão.

    Returns:
        O padrão que deu match ou None
    """
    error_lower = error_text.lower()
    for pattern in patterns:
        if re.search(pattern, error_lower, re.IGNORECASE):
            return pattern
    return None


def _extract_error_code(error_text: str, outcome: SendOutcome) -> str:
    """
    Extrai código de erro curto baseado no conteúdo.
    """
    error_lower = error_text.lower()

    if outcome == SendOutcome.FAILED_VALIDATION:
        if "not registered" in error_lower or "not on whatsapp" in error_lower:
            return "not_on_whatsapp"
        if "invalid" in error_lower and "jid" in error_lower:
            return "invalid_jid"
        if "not found" in error_lower:
            return "number_not_found"
        return "invalid_number"

    elif outcome == SendOutcome.FAILED_BANNED:
        if "blocked by user" in error_lower or "user blocked" in error_lower:
            return "blocked_by_user"
        if "spam" in error_lower:
            return "spam_detected"
        if "restricted" in error_lower:
            return "account_restricted"
        if "privacy" in error_lower:
            return "privacy_settings"
        if "banned" in error_lower:
            return "banned"
        return "blocked"

    else:  # FAILED_PROVIDER
        if "timeout" in error_lower:
            return "timeout"
        if "circuit" in error_lower:
            return "circuit_open"
        if "5" in error_lower and any(c.isdigit() for c in error_lower):
            return "server_error"
        if "network" in error_lower or "connection" in error_lower:
            return "network_error"
        return "unknown"


def classify_provider_error(error: Exception) -> ClassifiedError:
    """
    Classifica um erro de provider em categoria específica.

    Args:
        error: A exception capturada (HTTPStatusError, TimeoutException, etc)

    Returns:
        ClassifiedError com outcome, código curto e texto original truncado

    Exemplo:
        >>> err = Exception("invalid jid: 5511999@s.whatsapp.net")
        >>> result = classify_provider_error(err)
        >>> result.outcome
        SendOutcome.FAILED_VALIDATION
        >>> result.provider_error_code
        'invalid_jid'
    """
    error_text = str(error)

    # Tentar extrair response body se for HTTPStatusError
    response_text = ""
    try:
        if hasattr(error, 'response') and error.response is not None:
            response_text = error.response.text[:500] if hasattr(error.response, 'text') else ""
    except Exception:
        pass

    # Combinar erro e response para análise
    full_text = f"{error_text} {response_text}"

    # Verificar padrões na ordem: VALIDATION > BANNED > PROVIDER
    if _match_patterns(full_text, VALIDATION_PATTERNS):
        outcome = SendOutcome.FAILED_VALIDATION
        logger.debug(f"Erro classificado como VALIDATION: {error_text[:100]}")
    elif _match_patterns(full_text, BANNED_PATTERNS):
        outcome = SendOutcome.FAILED_BANNED
        logger.debug(f"Erro classificado como BANNED: {error_text[:100]}")
    else:
        outcome = SendOutcome.FAILED_PROVIDER
        logger.debug(f"Erro classificado como PROVIDER (fallback): {error_text[:100]}")

    error_code = _extract_error_code(full_text, outcome)
    error_raw = error_text[:200]  # Truncar para storage

    return ClassifiedError(
        outcome=outcome,
        provider_error_code=error_code,
        provider_error_raw=error_raw,
    )


def classify_error_string(error_text: str) -> Tuple[SendOutcome, str]:
    """
    Versão simplificada que recebe string diretamente.

    Útil para casos onde já temos o texto do erro.

    Returns:
        Tuple de (SendOutcome, provider_error_code)
    """
    if _match_patterns(error_text, VALIDATION_PATTERNS):
        outcome = SendOutcome.FAILED_VALIDATION
    elif _match_patterns(error_text, BANNED_PATTERNS):
        outcome = SendOutcome.FAILED_BANNED
    else:
        outcome = SendOutcome.FAILED_PROVIDER

    error_code = _extract_error_code(error_text, outcome)
    return outcome, error_code
