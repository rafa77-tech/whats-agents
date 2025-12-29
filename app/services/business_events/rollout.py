"""
Controle de rollout para business events.

Sprint 17 - E08

Usa feature_flags para controlar:
- enabled: master switch
- percentage: % de clientes no rollout (hash consistente)
- force_on: lista de cliente_ids para debug
"""
import hashlib
import json
import logging
import time
from typing import Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Cache local para evitar queries repetidas
_canary_cache: dict = {}
_cache_ttl = 60  # segundos


async def get_canary_config() -> dict:
    """
    Obtem configuracao do canary (com cache).

    Returns:
        dict com enabled, percentage, force_on
    """
    cache_key = "business_events_canary"
    now = time.time()

    # Verificar cache
    if cache_key in _canary_cache:
        cached = _canary_cache[cache_key]
        if now - cached["ts"] < _cache_ttl:
            return cached["config"]

    # Buscar do banco
    try:
        response = (
            supabase.table("feature_flags")
            .select("value")
            .eq("key", "business_events_canary")
            .maybe_single()
            .execute()
        )

        if response.data:
            config = response.data.get("value", {})
            if isinstance(config, str):
                config = json.loads(config)
        else:
            # Flag nao existe - desabilitado por padrao
            config = {"enabled": False, "percentage": 0, "force_on": []}

    except Exception as e:
        logger.error(f"Erro ao obter canary config: {e}")
        config = {"enabled": False, "percentage": 0, "force_on": []}

    # Atualizar cache
    _canary_cache[cache_key] = {"ts": now, "config": config}

    return config


async def should_emit_event(
    cliente_id: str,
    event_type: str,
) -> bool:
    """
    Verifica se deve emitir evento baseado no rollout.

    Args:
        cliente_id: UUID do cliente (usado para consistencia)
        event_type: Tipo do evento

    Returns:
        True se deve emitir
    """
    config = await get_canary_config()

    # Master switch
    if not config.get("enabled", False):
        return False

    # Allowlist para debug (force_on)
    force_on = config.get("force_on", [])
    if cliente_id in force_on:
        logger.debug(f"Cliente {cliente_id[:8]} esta na allowlist, emitindo evento")
        return True

    # Percentual de rollout
    percentage = config.get("percentage", 0)

    if percentage >= 100:
        return True

    if percentage <= 0:
        return False

    # Hash do cliente_id para consistencia
    # Mesmo cliente sempre na mesma cohort
    hash_val = int(hashlib.md5(cliente_id.encode()).hexdigest()[:8], 16)
    bucket = hash_val % 100

    return bucket < percentage


async def get_rollout_status() -> dict:
    """Retorna status atual do rollout."""
    config = await get_canary_config()

    return {
        "enabled": config.get("enabled", False),
        "percentage": config.get("percentage", 0),
        "force_on_count": len(config.get("force_on", [])),
        "phase": _get_phase_name(config.get("percentage", 0)),
    }


async def add_to_allowlist(cliente_id: str) -> bool:
    """
    Adiciona cliente a allowlist para debug.

    Args:
        cliente_id: UUID do cliente

    Returns:
        True se adicionado com sucesso
    """
    try:
        config = await get_canary_config()
        force_on = config.get("force_on", [])

        if cliente_id not in force_on:
            force_on.append(cliente_id)
            config["force_on"] = force_on

            # Atualizar no banco
            supabase.table("feature_flags").update({
                "value": config,
                "updated_at": "now()",
                "updated_by": "allowlist_api"
            }).eq("key", "business_events_canary").execute()

            # Limpar cache
            _canary_cache.clear()

            logger.info(f"Cliente {cliente_id[:8]} adicionado a allowlist")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao adicionar a allowlist: {e}")
        return False


async def remove_from_allowlist(cliente_id: str) -> bool:
    """
    Remove cliente da allowlist.

    Args:
        cliente_id: UUID do cliente

    Returns:
        True se removido com sucesso
    """
    try:
        config = await get_canary_config()
        force_on = config.get("force_on", [])

        if cliente_id in force_on:
            force_on.remove(cliente_id)
            config["force_on"] = force_on

            # Atualizar no banco
            supabase.table("feature_flags").update({
                "value": config,
                "updated_at": "now()",
                "updated_by": "allowlist_api"
            }).eq("key", "business_events_canary").execute()

            # Limpar cache
            _canary_cache.clear()

            logger.info(f"Cliente {cliente_id[:8]} removido da allowlist")
            return True

        return False

    except Exception as e:
        logger.error(f"Erro ao remover da allowlist: {e}")
        return False


def clear_cache():
    """Limpa cache do canary (util para testes)."""
    _canary_cache.clear()


def _get_phase_name(pct: int) -> str:
    """Retorna nome da fase baseado no percentual."""
    if pct <= 0:
        return "disabled"
    elif pct <= 5:
        return "canary_2pct"
    elif pct <= 15:
        return "canary_10pct"
    elif pct <= 60:
        return "canary_50pct"
    else:
        return "full_rollout"
