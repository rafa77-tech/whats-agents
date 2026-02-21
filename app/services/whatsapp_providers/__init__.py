"""
WhatsApp Providers - Abstração para múltiplas APIs.

Sprint 26 - E08: Multi-Provider Support
Sprint 66 - Meta Cloud API Integration

Suporta:
- Evolution API (self-hosted)
- Z-API (SaaS)
- Meta Cloud API (API oficial)

Uso:
    from app.services.whatsapp_providers import get_provider

    # Obter provider para um chip
    provider = get_provider(chip)

    # Enviar mensagem
    result = await provider.send_text("5511999999999", "Olá!")
"""

import logging
from typing import Dict, Optional

from app.services.whatsapp_providers.base import (
    WhatsAppProvider,
    ProviderType,
    MessageResult,
    ConnectionStatus,
)
from app.services.whatsapp_providers.evolution import EvolutionProvider
from app.services.whatsapp_providers.zapi import ZApiProvider
from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

logger = logging.getLogger(__name__)

# Cache de providers (evita criar múltiplas instâncias)
_provider_cache: Dict[str, WhatsAppProvider] = {}

__all__ = [
    "WhatsAppProvider",
    "ProviderType",
    "MessageResult",
    "ConnectionStatus",
    "EvolutionProvider",
    "ZApiProvider",
    "MetaCloudProvider",
    "get_provider",
    "get_provider_by_type",
    "clear_provider_cache",
]


def get_provider(chip: dict) -> WhatsAppProvider:
    """
    Retorna provider apropriado para o chip.

    Args:
        chip: Dict com dados do chip (da tabela chips)

    Returns:
        WhatsAppProvider configurado

    Raises:
        ValueError: Se provider desconhecido
    """
    chip_id = chip.get("id", "unknown")

    # Retornar do cache se existir
    if chip_id in _provider_cache:
        return _provider_cache[chip_id]

    provider_type = chip.get("provider", "evolution")

    if provider_type == "evolution":
        provider = EvolutionProvider(
            instance_name=chip["instance_name"],
        )
    elif provider_type == "z-api":
        # Campos específicos do Z-API
        instance_id = chip.get("zapi_instance_id")
        token = chip.get("zapi_token")
        client_token = chip.get("zapi_client_token")

        if not instance_id or not token:
            raise ValueError(
                f"Chip Z-API {chip_id} sem credenciais: "
                f"zapi_instance_id={instance_id}, zapi_token={'***' if token else None}"
            )

        provider = ZApiProvider(
            instance_id=instance_id,
            token=token,
            client_token=client_token,
        )
    elif provider_type == "meta":
        # Sprint 66: Campos específicos do Meta Cloud API
        phone_number_id = chip.get("meta_phone_number_id")
        access_token = chip.get("meta_access_token")
        waba_id = chip.get("meta_waba_id")

        if not phone_number_id or not access_token:
            raise ValueError(f"Chip Meta {chip_id} sem meta_phone_number_id ou meta_access_token")

        provider = MetaCloudProvider(
            phone_number_id=phone_number_id,
            access_token=access_token,
            waba_id=waba_id,
        )
    else:
        raise ValueError(f"Provider desconhecido: {provider_type}")

    # Cachear
    _provider_cache[chip_id] = provider
    logger.debug(f"[Providers] Criado {provider_type} para chip {chip_id}")

    return provider


def get_provider_by_type(
    provider_type: str,
    instance_name: Optional[str] = None,
    zapi_instance_id: Optional[str] = None,
    zapi_token: Optional[str] = None,
    zapi_client_token: Optional[str] = None,
    meta_phone_number_id: Optional[str] = None,
    meta_access_token: Optional[str] = None,
    meta_waba_id: Optional[str] = None,
) -> WhatsAppProvider:
    """
    Cria provider diretamente pelo tipo (sem chip).

    Útil para testes e casos especiais.

    Args:
        provider_type: 'evolution', 'z-api', ou 'meta'
        instance_name: Nome da instância Evolution
        zapi_instance_id: ID da instância Z-API
        zapi_token: Token da instância Z-API
        zapi_client_token: Client token Z-API
        meta_phone_number_id: Phone Number ID (Meta)
        meta_access_token: Access Token (Meta)
        meta_waba_id: WABA ID (Meta)

    Returns:
        WhatsAppProvider configurado
    """
    if provider_type == "evolution":
        if not instance_name:
            raise ValueError("instance_name obrigatório para Evolution")
        return EvolutionProvider(instance_name=instance_name)

    elif provider_type == "z-api":
        if not zapi_instance_id or not zapi_token:
            raise ValueError("zapi_instance_id e zapi_token obrigatórios para Z-API")
        return ZApiProvider(
            instance_id=zapi_instance_id,
            token=zapi_token,
            client_token=zapi_client_token,
        )

    elif provider_type == "meta":
        if not meta_phone_number_id or not meta_access_token:
            raise ValueError("meta_phone_number_id e meta_access_token obrigatórios para Meta")
        return MetaCloudProvider(
            phone_number_id=meta_phone_number_id,
            access_token=meta_access_token,
            waba_id=meta_waba_id,
        )

    else:
        raise ValueError(f"Provider desconhecido: {provider_type}")


def clear_provider_cache(chip_id: Optional[str] = None) -> None:
    """
    Limpa cache de providers.

    Args:
        chip_id: ID específico para limpar, ou None para limpar tudo
    """
    if chip_id:
        removed = _provider_cache.pop(chip_id, None)
        if removed:
            logger.debug(f"[Providers] Cache removido para chip {chip_id}")
    else:
        count = len(_provider_cache)
        _provider_cache.clear()
        logger.debug(f"[Providers] Cache limpo ({count} providers)")
