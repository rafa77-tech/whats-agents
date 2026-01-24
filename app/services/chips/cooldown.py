"""
Chip Cooldown - Gerenciamento de cooldown por tipo de erro.

Sprint 36 - T05.8: Cooldown após erro WhatsApp.

Quando um chip recebe erro do WhatsApp, aplica cooldown temporário
baseado no tipo de erro para evitar mais falhas.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# Mapeamento de códigos de erro para tempo de cooldown
COOLDOWN_POR_ERRO = {
    # Rate limit: cooldown curto
    429: 5,      # 5 minutos

    # Bad request: pode ser restrição temporária
    400: 15,     # 15 minutos

    # Forbidden: restrição mais séria
    403: 60,     # 1 hora

    # Not found: número inválido (não é culpa do chip)
    404: 0,      # Sem cooldown

    # Server error: problema no servidor (não é culpa do chip)
    500: 0,      # Sem cooldown
    502: 0,
    503: 5,      # Pode ser temporário
}

# Mensagens de erro que indicam restrição
MENSAGENS_RESTRICAO = [
    "blocked",
    "banned",
    "restricted",
    "spam",
    "rate limit",
    "too many",
    "temporarily unavailable",
]


async def aplicar_cooldown(
    chip_id: str,
    minutos: int,
    motivo: str = "erro_whatsapp",
) -> bool:
    """
    Aplica cooldown a um chip.

    Args:
        chip_id: ID do chip
        minutos: Duração do cooldown em minutos
        motivo: Motivo do cooldown (para log)

    Returns:
        True se cooldown foi aplicado
    """
    if minutos <= 0:
        return False

    cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=minutos)

    try:
        supabase.table("chips").update({
            "cooldown_until": cooldown_until.isoformat(),
            "cooldown_motivo": motivo,
        }).eq("id", chip_id).execute()

        logger.warning(
            f"[ChipCooldown] Chip {chip_id[:8]} em cooldown por {minutos}min. "
            f"Motivo: {motivo}"
        )

        return True

    except Exception as e:
        logger.error(f"[ChipCooldown] Erro ao aplicar cooldown: {e}")
        return False


async def registrar_erro_whatsapp(
    chip_id: str,
    error_code: Optional[int] = None,
    error_message: Optional[str] = None,
) -> dict:
    """
    Registra erro do WhatsApp e aplica cooldown se necessário.

    Sprint 36 - T05.8: Cooldown automático por tipo de erro.

    Args:
        chip_id: ID do chip
        error_code: Código HTTP do erro
        error_message: Mensagem de erro

    Returns:
        {
            'cooldown_aplicado': bool,
            'cooldown_minutos': int,
            'motivo': str,
        }
    """
    cooldown_minutos = 0
    motivo = "erro_desconhecido"

    # 1. Verificar por código de erro
    if error_code and error_code in COOLDOWN_POR_ERRO:
        cooldown_minutos = COOLDOWN_POR_ERRO[error_code]
        motivo = f"http_{error_code}"

    # 2. Verificar por mensagem de erro (pode aumentar cooldown)
    if error_message:
        error_lower = error_message.lower()
        for msg_restricao in MENSAGENS_RESTRICAO:
            if msg_restricao in error_lower:
                # Aumentar cooldown para mensagens de restrição
                cooldown_minutos = max(cooldown_minutos, 30)
                motivo = f"restricao:{msg_restricao}"
                break

    # 3. Aplicar cooldown se necessário
    if cooldown_minutos > 0:
        await aplicar_cooldown(chip_id, cooldown_minutos, motivo)

    return {
        "cooldown_aplicado": cooldown_minutos > 0,
        "cooldown_minutos": cooldown_minutos,
        "motivo": motivo,
    }


async def limpar_cooldown(chip_id: str) -> bool:
    """
    Remove cooldown de um chip manualmente.

    Args:
        chip_id: ID do chip

    Returns:
        True se cooldown foi removido
    """
    try:
        supabase.table("chips").update({
            "cooldown_until": None,
            "cooldown_motivo": None,
        }).eq("id", chip_id).execute()

        logger.info(f"[ChipCooldown] Cooldown removido do chip {chip_id[:8]}")
        return True

    except Exception as e:
        logger.error(f"[ChipCooldown] Erro ao limpar cooldown: {e}")
        return False


async def verificar_cooldown(chip_id: str) -> dict:
    """
    Verifica status de cooldown de um chip.

    Args:
        chip_id: ID do chip

    Returns:
        {
            'em_cooldown': bool,
            'cooldown_until': datetime | None,
            'minutos_restantes': int,
            'motivo': str | None,
        }
    """
    try:
        result = supabase.table("chips").select(
            "cooldown_until, cooldown_motivo"
        ).eq("id", chip_id).single().execute()

        if not result.data:
            return {
                "em_cooldown": False,
                "cooldown_until": None,
                "minutos_restantes": 0,
                "motivo": None,
            }

        cooldown_until_str = result.data.get("cooldown_until")
        if not cooldown_until_str:
            return {
                "em_cooldown": False,
                "cooldown_until": None,
                "minutos_restantes": 0,
                "motivo": None,
            }

        cooldown_until = datetime.fromisoformat(
            cooldown_until_str.replace("Z", "+00:00")
        )
        agora = datetime.now(timezone.utc)

        if cooldown_until <= agora:
            return {
                "em_cooldown": False,
                "cooldown_until": cooldown_until,
                "minutos_restantes": 0,
                "motivo": result.data.get("cooldown_motivo"),
            }

        minutos_restantes = int((cooldown_until - agora).total_seconds() / 60)

        return {
            "em_cooldown": True,
            "cooldown_until": cooldown_until,
            "minutos_restantes": minutos_restantes,
            "motivo": result.data.get("cooldown_motivo"),
        }

    except Exception as e:
        logger.error(f"[ChipCooldown] Erro ao verificar cooldown: {e}")
        return {
            "em_cooldown": False,
            "cooldown_until": None,
            "minutos_restantes": 0,
            "motivo": None,
        }
