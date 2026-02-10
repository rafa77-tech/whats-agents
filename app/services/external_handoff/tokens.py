"""
Geracao e validacao de tokens JWT para confirmacao de handoff.

Sprint 20 - E02 - Tokens seguros e single-use.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

import jwt

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Configuracoes
TOKEN_EXPIRY_HOURS = 48
ALGORITHM = "HS256"


def gerar_token_confirmacao(
    handoff_id: str,
    action: str,  # 'confirmed' ou 'not_confirmed'
) -> str:
    """
    Gera token JWT assinado para confirmacao de handoff.

    Args:
        handoff_id: UUID do handoff
        action: Acao que o token executa

    Returns:
        Token JWT assinado

    Exemplo de uso:
        token = gerar_token_confirmacao("uuid-123", "confirmed")
        link = f"https://app.com/handoff/confirm?t={token}"
    """
    # JTI unico para garantir single-use
    jti = str(uuid4())

    payload = {
        "handoff_id": handoff_id,
        "action": action,
        "jti": jti,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )

    logger.debug(f"Token gerado para handoff {handoff_id[:8]}, action={action}, jti={jti[:8]}")

    return token


def gerar_par_links(handoff_id: str, base_url: str = None) -> Tuple[str, str]:
    """
    Gera par de links (confirmar/nao confirmar) para o handoff.

    Args:
        handoff_id: UUID do handoff
        base_url: URL base (default: settings.APP_BASE_URL)

    Returns:
        Tuple (link_confirmar, link_nao_confirmar)
    """
    base = base_url or settings.APP_BASE_URL or "https://api.revoluna.com"

    token_confirm = gerar_token_confirmacao(handoff_id, "confirmed")
    token_not_confirm = gerar_token_confirmacao(handoff_id, "not_confirmed")

    link_confirmar = f"{base}/handoff/confirm?t={token_confirm}"
    link_nao_confirmar = f"{base}/handoff/confirm?t={token_not_confirm}"

    logger.info(f"Par de links gerado para handoff {handoff_id[:8]}")

    return link_confirmar, link_nao_confirmar


async def validar_token(token: str) -> Tuple[bool, Optional[dict], Optional[str]]:
    """
    Valida token JWT e verifica se ja foi usado.

    Args:
        token: Token JWT

    Returns:
        Tuple (valido, payload, erro)
        - valido: True se token e valido e nao foi usado
        - payload: Dados do token se valido
        - erro: Mensagem de erro se invalido
    """
    try:
        # Decodificar e validar assinatura/expiracao
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
        )

        handoff_id = payload.get("handoff_id")
        action = payload.get("action")
        jti = payload.get("jti")

        if not all([handoff_id, action, jti]):
            return False, None, "Token incompleto"

        # Verificar se ja foi usado
        response = supabase.table("handoff_used_tokens").select("jti").eq("jti", jti).execute()

        if response.data:
            logger.warning(f"Token ja usado: jti={jti[:8]}")
            return False, payload, "Token ja utilizado"

        return True, payload, None

    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return False, None, "Link expirado"

    except jwt.InvalidTokenError as e:
        logger.warning(f"Token invalido: {e}")
        return False, None, "Link invalido"


async def marcar_token_usado(
    jti: str,
    handoff_id: str,
    action: str,
    ip_address: str = None,
) -> bool:
    """
    Marca token como usado (single-use).

    Args:
        jti: JWT ID
        handoff_id: UUID do handoff
        action: Acao executada
        ip_address: IP de origem (opcional)

    Returns:
        True se marcado com sucesso
    """
    try:
        supabase.table("handoff_used_tokens").insert(
            {
                "jti": jti,
                "handoff_id": handoff_id,
                "action": action,
                "ip_address": ip_address,
            }
        ).execute()

        logger.info(f"Token marcado como usado: jti={jti[:8]}")
        return True

    except Exception as e:
        # Pode falhar por unique constraint se race condition
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            logger.warning(f"Token ja marcado (race condition): jti={jti[:8]}")
            return False

        logger.error(f"Erro ao marcar token: {e}")
        return False
