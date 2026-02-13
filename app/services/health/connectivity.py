"""
Verificacoes de conectividade para health checks.

Sprint 58 - Epic 3: Extraido de app/api/routes/health.py
"""

import logging

from app.services.redis import verificar_conexao_redis
from app.services.whatsapp import evolution
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


async def verificar_redis() -> dict:
    """Verifica conexao com Redis.

    Returns:
        dict com status e mensagem de erro opcional.
    """
    try:
        redis_ok = await verificar_conexao_redis()
        if redis_ok:
            return {"status": "ok"}
        return {"status": "error", "message": "Redis ping failed"}
    except Exception as e:
        logger.error(f"[health] Redis check failed: {e}")
        return {"status": "error", "message": str(e)}


def verificar_supabase() -> dict:
    """Verifica conexao com Supabase.

    Returns:
        dict com status e mensagem de erro opcional.
    """
    try:
        supabase.table("clientes").select("id").limit(1).execute()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[health] Supabase check failed: {e}")
        return {"status": "error", "message": str(e)}


async def verificar_evolution() -> dict:
    """Verifica conexao com Evolution API.

    Returns:
        dict com connected, state e details.
    """
    try:
        status = await evolution.verificar_conexao()
        state = None
        if status:
            if "instance" in status:
                state = status.get("instance", {}).get("state")
            else:
                state = status.get("state")

        connected = state == "open"
        return {
            "connected": connected,
            "instance": evolution.instance,
            "state": state or "unknown",
            "details": status,
        }
    except Exception as e:
        return {
            "connected": False,
            "instance": evolution.instance,
            "state": "error",
            "error": str(e),
        }
