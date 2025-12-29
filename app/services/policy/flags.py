"""
Feature flags service para Policy Engine.

Sprint 16 - Kill Switch
Permite desligar funcionalidades sem deploy.

Implementação:
- Redis cache com TTL curto (30s)
- Fallback para Supabase se cache miss ou erro
- Fallback para valores seguros se tudo falhar
"""
import logging
from dataclasses import dataclass
from typing import Optional

from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

# TTL curto para atualizações rápidas
CACHE_TTL = 30  # segundos
CACHE_PREFIX = "feature_flag"


@dataclass
class PolicyEngineFlags:
    """Flags do Policy Engine."""

    enabled: bool = True


@dataclass
class SafeModeFlags:
    """Flags do modo seguro."""

    enabled: bool = False
    mode: str = "wait"  # "wait" ou "handoff"


@dataclass
class CampaignsFlags:
    """Flags de campanhas."""

    enabled: bool = True


@dataclass
class DisabledRulesFlags:
    """Regras desabilitadas."""

    rules: list[str] = None

    def __post_init__(self):
        if self.rules is None:
            self.rules = []


async def _get_flag_value(key: str) -> Optional[dict]:
    """
    Busca valor de flag com cache.

    1. Tenta cache Redis (30s TTL)
    2. Fallback para Supabase
    3. Retorna None se tudo falhar
    """
    cache_key = f"{CACHE_PREFIX}:{key}"

    # 1. Tentar cache
    try:
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return cached
    except Exception as e:
        logger.warning(f"Erro ao ler cache de flag {key}: {e}")

    # 2. Fallback para Supabase
    try:
        response = (
            supabase.table("feature_flags")
            .select("value")
            .eq("key", key)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            value = response.data[0]["value"]
            # Salvar no cache
            try:
                await cache_set_json(cache_key, value, CACHE_TTL)
            except Exception as e:
                logger.warning(f"Erro ao salvar cache de flag {key}: {e}")
            return value

    except Exception as e:
        logger.error(f"Erro ao buscar flag {key} do Supabase: {e}")

    return None


async def get_policy_engine_flags() -> PolicyEngineFlags:
    """
    Retorna flags do Policy Engine.

    Fallback seguro: enabled=True (manter comportamento normal)
    """
    value = await _get_flag_value("policy_engine")

    if value is None:
        logger.warning("Flag policy_engine não encontrada, usando default")
        return PolicyEngineFlags()

    return PolicyEngineFlags(
        enabled=value.get("enabled", True)
    )


async def get_safe_mode_flags() -> SafeModeFlags:
    """
    Retorna flags do modo seguro.

    Fallback seguro: enabled=False (não ativar safe_mode por erro)
    """
    value = await _get_flag_value("safe_mode")

    if value is None:
        logger.warning("Flag safe_mode não encontrada, usando default")
        return SafeModeFlags()

    return SafeModeFlags(
        enabled=value.get("enabled", False),
        mode=value.get("mode", "wait"),
    )


async def get_campaigns_flags() -> CampaignsFlags:
    """
    Retorna flags de campanhas.

    Fallback seguro: enabled=True (manter campanhas funcionando)
    """
    value = await _get_flag_value("campaigns")

    if value is None:
        logger.warning("Flag campaigns não encontrada, usando default")
        return CampaignsFlags()

    return CampaignsFlags(
        enabled=value.get("enabled", True)
    )


async def get_disabled_rules() -> DisabledRulesFlags:
    """
    Retorna lista de regras desabilitadas.

    Fallback seguro: lista vazia (nenhuma regra desabilitada)
    """
    value = await _get_flag_value("disabled_rules")

    if value is None:
        logger.warning("Flag disabled_rules não encontrada, usando default")
        return DisabledRulesFlags()

    return DisabledRulesFlags(
        rules=value.get("rules", [])
    )


async def is_rule_disabled(rule_id: str) -> bool:
    """
    Verifica se uma regra específica está desabilitada.

    Args:
        rule_id: ID da regra (ex: "rule_grave_objection")

    Returns:
        True se a regra está desabilitada
    """
    flags = await get_disabled_rules()
    return rule_id in flags.rules


async def is_policy_engine_enabled() -> bool:
    """Verifica se o Policy Engine está habilitado."""
    flags = await get_policy_engine_flags()
    return flags.enabled


async def is_safe_mode_active() -> bool:
    """Verifica se o modo seguro está ativo."""
    flags = await get_safe_mode_flags()
    return flags.enabled


async def get_safe_mode_action() -> str:
    """
    Retorna a ação do modo seguro.

    Returns:
        "wait" ou "handoff"
    """
    flags = await get_safe_mode_flags()
    return flags.mode


async def are_campaigns_enabled() -> bool:
    """Verifica se campanhas estão habilitadas."""
    flags = await get_campaigns_flags()
    return flags.enabled


async def set_flag(key: str, value: dict, updated_by: str = "system") -> bool:
    """
    Atualiza valor de uma flag.

    Args:
        key: Nome da flag
        value: Novo valor (dict)
        updated_by: Quem está atualizando

    Returns:
        True se sucesso
    """
    try:
        # Atualizar no banco
        response = (
            supabase.table("feature_flags")
            .update({
                "value": value,
                "updated_by": updated_by,
            })
            .eq("key", key)
            .execute()
        )

        if not response.data:
            logger.error(f"Flag {key} não encontrada para atualização")
            return False

        # Invalidar cache
        cache_key = f"{CACHE_PREFIX}:{key}"
        try:
            # Setar com valor atualizado (não apenas deletar)
            await cache_set_json(cache_key, value, CACHE_TTL)
        except Exception as e:
            logger.warning(f"Erro ao atualizar cache de flag {key}: {e}")

        logger.info(f"Flag {key} atualizada por {updated_by}: {value}")
        return True

    except Exception as e:
        logger.error(f"Erro ao atualizar flag {key}: {e}")
        return False


async def enable_safe_mode(mode: str = "wait", updated_by: str = "system") -> bool:
    """
    Ativa modo seguro.

    Args:
        mode: "wait" (não responde) ou "handoff" (escala humano)
        updated_by: Quem está ativando

    Returns:
        True se sucesso
    """
    return await set_flag(
        "safe_mode",
        {"enabled": True, "mode": mode},
        updated_by=updated_by,
    )


async def disable_safe_mode(updated_by: str = "system") -> bool:
    """Desativa modo seguro."""
    return await set_flag(
        "safe_mode",
        {"enabled": False, "mode": "wait"},
        updated_by=updated_by,
    )


async def disable_policy_engine(updated_by: str = "system") -> bool:
    """Desativa Policy Engine completamente."""
    return await set_flag(
        "policy_engine",
        {"enabled": False},
        updated_by=updated_by,
    )


async def enable_policy_engine(updated_by: str = "system") -> bool:
    """Reativa Policy Engine."""
    return await set_flag(
        "policy_engine",
        {"enabled": True},
        updated_by=updated_by,
    )


async def disable_rule(rule_id: str, updated_by: str = "system") -> bool:
    """
    Desabilita uma regra específica.

    Args:
        rule_id: ID da regra a desabilitar
        updated_by: Quem está desabilitando

    Returns:
        True se sucesso
    """
    current = await get_disabled_rules()
    if rule_id not in current.rules:
        current.rules.append(rule_id)

    return await set_flag(
        "disabled_rules",
        {"rules": current.rules},
        updated_by=updated_by,
    )


async def enable_rule(rule_id: str, updated_by: str = "system") -> bool:
    """
    Reabilita uma regra específica.

    Args:
        rule_id: ID da regra a reabilitar
        updated_by: Quem está reabilitando

    Returns:
        True se sucesso
    """
    current = await get_disabled_rules()
    if rule_id in current.rules:
        current.rules.remove(rule_id)

    return await set_flag(
        "disabled_rules",
        {"rules": current.rules},
        updated_by=updated_by,
    )
