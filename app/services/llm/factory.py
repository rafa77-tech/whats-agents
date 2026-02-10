"""
Factory para LLM Providers.

Sprint 31 - S31.E1.7

Centraliza criação de providers para facilitar DI e configuração.
"""

from typing import Optional
from functools import lru_cache

from app.core.config import settings
from .protocol import LLMProvider
from .anthropic_provider import AnthropicProvider


@lru_cache()
def get_llm_provider(
    model: str = "haiku",
) -> LLMProvider:
    """
    Retorna provider de LLM configurado.

    Args:
        model: "haiku" ou "sonnet"

    Returns:
        LLMProvider configurado

    Exemplo:
        provider = get_llm_provider()  # Haiku por padrão
        provider = get_llm_provider("sonnet")  # Sonnet para tarefas complexas
    """
    model_map = {
        "haiku": settings.LLM_MODEL,
        "sonnet": settings.LLM_MODEL_COMPLEX,
    }

    model_id = model_map.get(model, settings.LLM_MODEL)

    return AnthropicProvider(model_id=model_id)


def get_haiku_provider() -> LLMProvider:
    """Atalho para provider Haiku (mais econômico)."""
    return get_llm_provider("haiku")


def get_sonnet_provider() -> LLMProvider:
    """Atalho para provider Sonnet (mais capaz)."""
    return get_llm_provider("sonnet")


def create_provider(
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    use_circuit_breaker: bool = True,
) -> LLMProvider:
    """
    Cria provider com configurações customizadas.

    Útil para testes ou configurações especiais.

    Args:
        model_id: ID do modelo (default: settings.LLM_MODEL)
        api_key: API key (default: settings.ANTHROPIC_API_KEY)
        use_circuit_breaker: Se deve usar circuit breaker

    Returns:
        LLMProvider configurado
    """
    return AnthropicProvider(
        model_id=model_id,
        api_key=api_key,
        use_circuit_breaker=use_circuit_breaker,
    )


# Para testes - permite limpar cache
def clear_provider_cache():
    """Limpa cache de providers (usar em testes)."""
    get_llm_provider.cache_clear()
