"""
LLM Provider Module - Abstração sobre providers de LLM.

Sprint 31

Este módulo fornece uma interface unificada para trabalhar com LLMs,
permitindo trocar providers sem mudar código consumidor.

Uso básico:
    from app.services.llm import get_llm_provider, LLMRequest, Message

    provider = get_llm_provider()
    request = LLMRequest(messages=[Message.user("Olá!")])
    response = await provider.generate(request)
    print(response.content)

Uso em testes:
    from app.services.llm import MockLLMProvider

    mock = MockLLMProvider(default_response="Mock!")
    response = await mock.generate(request)

Classes principais:
    - LLMProvider: Protocol que define a interface
    - LLMRequest: Dados de entrada para o LLM
    - LLMResponse: Dados de saída do LLM
    - AnthropicProvider: Implementação para Claude
    - MockLLMProvider: Implementação para testes
"""

# Protocol e erros
from .protocol import LLMProvider, LLMError

# Modelos de dados
from .models import (
    Message,
    MessageRole,
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolDefinition,
    ToolResult,
    StopReason,
    UsageStats,
)

# Providers
from .anthropic_provider import (
    AnthropicProvider,
    create_haiku_provider,
    create_sonnet_provider,
)
from .mock_provider import (
    MockLLMProvider,
    create_mock_that_returns,
    create_mock_that_calls_tool,
    create_mock_that_fails,
    create_mock_with_sequence,
)

# Factory
from .factory import (
    get_llm_provider,
    get_haiku_provider,
    get_sonnet_provider,
    create_provider,
    clear_provider_cache,
)

# Legacy functions (backward compatibility)
from .legacy import (
    gerar_resposta,
    gerar_resposta_com_tools,
    continuar_apos_tool,
    gerar_resposta_complexa,
    get_anthropic_client,
    client,
)

__all__ = [
    # Protocol
    "LLMProvider",
    "LLMError",
    # Models
    "Message",
    "MessageRole",
    "LLMRequest",
    "LLMResponse",
    "ToolCall",
    "ToolDefinition",
    "ToolResult",
    "StopReason",
    "UsageStats",
    # Providers
    "AnthropicProvider",
    "create_haiku_provider",
    "create_sonnet_provider",
    "MockLLMProvider",
    "create_mock_that_returns",
    "create_mock_that_calls_tool",
    "create_mock_that_fails",
    "create_mock_with_sequence",
    # Factory
    "get_llm_provider",
    "get_haiku_provider",
    "get_sonnet_provider",
    "create_provider",
    "clear_provider_cache",
    # Legacy (backward compatibility)
    "gerar_resposta",
    "gerar_resposta_com_tools",
    "continuar_apos_tool",
    "gerar_resposta_complexa",
    "get_anthropic_client",
    "client",
]
