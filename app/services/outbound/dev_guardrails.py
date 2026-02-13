"""
DEV allowlist guardrail para envio outbound.

Sprint 58 E04 - Extraido de outbound.py monolitico.
Sprint 18 Auditoria - R-2: DEV allowlist (fail-closed).
"""

import logging
from typing import Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


def _verificar_dev_allowlist(telefone: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se o numero esta na allowlist de DEV.

    R-2: DEV allowlist (fail-closed)

    Esta verificacao e INESCAPAVEL e roda ANTES de qualquer outro guardrail.
    NAO tem bypass humano - DEV nunca pode enviar para fora da allowlist.

    Comportamento:
    - PROD (APP_ENV=production): sempre permitido, retorna (True, None)
    - DEV com allowlist VAZIA: bloqueia TUDO, retorna (False, "dev_allowlist_empty")
    - DEV com numero NA allowlist: permitido, retorna (True, None)
    - DEV com numero FORA da allowlist: bloqueia, retorna (False, "dev_allowlist")

    Args:
        telefone: Numero de destino (5511999999999)

    Returns:
        Tuple (pode_enviar, reason_code)
    """
    # Em producao, nao verifica
    if settings.is_production:
        return (True, None)

    # Normalizar telefone (so digitos)
    telefone_normalizado = "".join(filter(str.isdigit, telefone))

    # Obter allowlist
    allowlist = settings.outbound_allowlist_numbers

    # Allowlist vazia em DEV = fail-closed (bloqueia TUDO)
    if not allowlist:
        logger.warning(
            f"[DEV GUARDRAIL] BLOCKED: OUTBOUND_ALLOWLIST vazia em DEV. "
            f"Destino: {telefone_normalizado[:8]}... bloqueado."
        )
        return (False, "dev_allowlist_empty")

    # Verificar se numero esta na allowlist
    if telefone_normalizado not in allowlist:
        logger.warning(
            f"[DEV GUARDRAIL] BLOCKED: {telefone_normalizado[:8]}... "
            f"nao esta na allowlist. Permitidos: {len(allowlist)} numeros."
        )
        return (False, "dev_allowlist")

    logger.debug(f"[DEV GUARDRAIL] ALLOWED: {telefone_normalizado[:8]}... esta na allowlist.")
    return (True, None)
