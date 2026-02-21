"""
Regras de auto-recovery e anti-flap para qualidade de chips Meta.

Sprint 67 (R9, Chunk 3).

Regras de recovery:
- RED → GREEN: trust = 30 (recuperação parcial)
- YELLOW → GREEN: trust = trust * 0.8 (quase normal)
- RED → YELLOW: mantém chip desativado (não confiável ainda)

Anti-flap:
- >3 oscilações em 24h = cooldown de 6h
"""

import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Constantes de recovery
TRUST_RED_TO_GREEN = 30
TRUST_YELLOW_TO_GREEN_FACTOR = 0.8
TRUST_DEFAULT = 50

# Anti-flap
MAX_OSCILLATIONS_24H = 3
COOLDOWN_HOURS = 6


def calcular_trust_recovery(
    previous_rating: str,
    new_rating: str,
    current_trust: int,
) -> int:
    """
    Calcula o trust score após mudança de qualidade.

    Args:
        previous_rating: Rating anterior (RED, YELLOW, GREEN)
        new_rating: Novo rating
        current_trust: Trust score atual do chip

    Returns:
        Novo trust score (0-100).
    """
    if new_rating == "GREEN":
        if previous_rating == "RED":
            return TRUST_RED_TO_GREEN
        elif previous_rating == "YELLOW":
            return max(1, int(current_trust * TRUST_YELLOW_TO_GREEN_FACTOR))
        return current_trust  # GREEN → GREEN, sem mudança

    if new_rating == "YELLOW":
        if previous_rating == "GREEN":
            return max(1, int(current_trust * 0.5))
        return current_trust  # RED → YELLOW ou YELLOW → YELLOW

    if new_rating == "RED":
        return 0  # Qualquer coisa → RED = trust zero

    return current_trust


async def verificar_anti_flap(chip_id: str) -> bool:
    """
    Verifica se um chip está em anti-flap (muitas oscilações recentes).

    Um chip com >3 mudanças de qualidade em 24h entra em cooldown
    de 6h para evitar ativação/desativação frequente.

    Args:
        chip_id: ID do chip

    Returns:
        True se o chip está em cooldown (NÃO deve ser reativado).
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        resp = (
            supabase.table("meta_quality_history")
            .select("id, quality_rating, checked_at")
            .eq("chip_id", chip_id)
            .gte("checked_at", cutoff.isoformat())
            .order("checked_at", desc=False)
            .execute()
        )

        if not resp.data:
            return False

        # Contar oscilações (mudanças de rating consecutivas)
        oscillations = 0
        prev_rating = None
        for entry in resp.data:
            rating = entry["quality_rating"]
            if prev_rating is not None and rating != prev_rating:
                oscillations += 1
            prev_rating = rating

        if oscillations <= MAX_OSCILLATIONS_24H:
            return False

        # Verificar se a última oscilação foi há menos de COOLDOWN_HOURS
        last_change_at = datetime.fromisoformat(resp.data[-1]["checked_at"].replace("Z", "+00:00"))
        cooldown_until = last_change_at + timedelta(hours=COOLDOWN_HOURS)
        now = datetime.now(timezone.utc)

        in_cooldown = now < cooldown_until
        if in_cooldown:
            logger.warning(
                "Chip %s em anti-flap cooldown (oscilações=%d, cooldown até %s)",
                chip_id,
                oscillations,
                cooldown_until.isoformat(),
            )

        return in_cooldown

    except Exception as e:
        logger.error("Erro ao verificar anti-flap chip %s: %s", chip_id, e)
        # Conservador: se erro, assumir cooldown para não piorar
        return True


def deve_reativar_chip(
    previous_rating: str,
    new_rating: str,
) -> bool:
    """
    Determina se um chip deve ser reativado baseado na transição de qualidade.

    RED → GREEN: sim (reativar com trust baixo)
    YELLOW → GREEN: sim
    RED → YELLOW: NÃO (ainda não confiável)

    Args:
        previous_rating: Rating anterior
        new_rating: Novo rating

    Returns:
        True se o chip deve ser reativado.
    """
    if new_rating != "GREEN":
        return False

    # Qualquer transição para GREEN permite reativação
    return previous_rating in ("RED", "YELLOW")


def deve_desativar_chip(
    previous_rating: str,
    new_rating: str,
) -> bool:
    """
    Determina se um chip deve ser desativado baseado na transição de qualidade.

    Args:
        previous_rating: Rating anterior
        new_rating: Novo rating

    Returns:
        True se o chip deve ser desativado.
    """
    if new_rating == "RED":
        return True

    if new_rating == "YELLOW" and previous_rating == "GREEN":
        return True

    return False
