"""
Anthropic Provider - Implementação do LLMProvider para Claude.

Sprint 31 - S31.E1.3

Este módulo implementa a interface LLMProvider usando a API da Anthropic.
"""

import logging
import asyncio
from typing import List, Optional, Any

import anthropic

from app.core.config import settings
from app.services.circuit_breaker import circuit_claude, CircuitOpenError
from .protocol import LLMError
from .models import (
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolResult,
    StopReason,
    Message,
)

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """
    Provider de LLM usando Anthropic Claude.

    Implementa a interface LLMProvider.

    Attributes:
        model_id: ID do modelo Claude a usar
        client: Cliente Anthropic

    Exemplo:
        provider = AnthropicProvider(model_id="claude-3-haiku-20240307")
        response = await provider.generate(request)
    """

    # Mapeamento de stop_reason da Anthropic para nosso enum
    STOP_REASON_MAP = {
        "end_turn": StopReason.END_TURN,
        "tool_use": StopReason.TOOL_USE,
        "max_tokens": StopReason.MAX_TOKENS,
        "stop_sequence": StopReason.STOP_SEQUENCE,
    }

    def __init__(
        self,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        use_circuit_breaker: bool = True,
    ):
        """
        Inicializa o provider.

        Args:
            model_id: ID do modelo Claude (default: settings.LLM_MODEL)
            api_key: API key (usa settings se não fornecida)
            use_circuit_breaker: Se deve usar circuit breaker (default: True)
        """
        self._model_id = model_id or settings.LLM_MODEL
        self._api_key = api_key or settings.ANTHROPIC_API_KEY
        self._use_circuit_breaker = use_circuit_breaker

        if not self._api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY não configurada",
                provider="anthropic",
                retryable=False,
            )

        self._client = anthropic.Anthropic(api_key=self._api_key)

    @property
    def model_id(self) -> str:
        """Retorna o ID do modelo."""
        return self._model_id

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Gera resposta do Claude.

        Args:
            request: LLMRequest com mensagens e configurações

        Returns:
            LLMResponse com texto e/ou tool_calls

        Raises:
            LLMError: Se houver erro na API
        """
        try:
            # Converter mensagens para formato Anthropic
            messages = self._convert_messages(request.messages)

            # Converter tools se existirem
            tools = None
            if request.tools:
                tools = [tool.to_dict() for tool in request.tools]

            # Preparar kwargs
            kwargs = {
                "model": self._model_id,
                "messages": messages,
                "max_tokens": request.max_tokens,
            }

            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            if tools:
                kwargs["tools"] = tools

            if request.stop_sequences:
                kwargs["stop_sequences"] = request.stop_sequences

            # Log da chamada
            logger.debug(
                f"Chamando Anthropic: model={self._model_id}, "
                f"messages={len(messages)}, has_tools={bool(tools)}, "
                f"trace_id={request.trace_id}"
            )

            # Chamar API
            response = await self._call_api(kwargs)

            # Converter response
            return self._convert_response(response)

        except CircuitOpenError as e:
            raise LLMError(
                f"Circuit breaker aberto: {e}",
                provider="anthropic",
                retryable=True,
                original_error=e,
            )
        except anthropic.APIConnectionError as e:
            raise LLMError(
                f"Erro de conexão com Anthropic: {e}",
                provider="anthropic",
                retryable=True,
                original_error=e,
            )
        except anthropic.RateLimitError as e:
            raise LLMError(
                f"Rate limit Anthropic: {e}",
                provider="anthropic",
                retryable=True,
                original_error=e,
            )
        except anthropic.APIStatusError as e:
            raise LLMError(
                f"Erro API Anthropic: {e}",
                provider="anthropic",
                retryable=e.status_code >= 500,
                original_error=e,
            )
        except Exception as e:
            logger.exception("Erro inesperado ao chamar Anthropic")
            raise LLMError(
                f"Erro inesperado: {e}",
                provider="anthropic",
                retryable=False,
                original_error=e,
            )

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[ToolResult],
    ) -> LLMResponse:
        """
        Continua geração após execução de tools.

        Args:
            request: Request original (com histórico atualizado)
            tool_results: Resultados das tools

        Returns:
            LLMResponse com continuação
        """
        try:
            # Converter mensagens
            messages = self._convert_messages(request.messages)

            # Adicionar tool results como mensagem do user
            tool_result_content = [tr.to_dict() for tr in tool_results]
            messages.append(
                {
                    "role": "user",
                    "content": tool_result_content,
                }
            )

            # Converter tools
            tools = None
            if request.tools:
                tools = [tool.to_dict() for tool in request.tools]

            # Preparar kwargs
            kwargs = {
                "model": self._model_id,
                "messages": messages,
                "max_tokens": request.max_tokens,
            }

            if request.system_prompt:
                kwargs["system"] = request.system_prompt

            if tools:
                kwargs["tools"] = tools

            # Chamar API
            response = await self._call_api(kwargs)

            return self._convert_response(response)

        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(
                f"Erro ao continuar após tool: {e}",
                provider="anthropic",
                retryable=False,
                original_error=e,
            )

    async def _call_api(self, kwargs: dict) -> Any:
        """
        Chama a API de forma assíncrona.

        Usa run_in_executor porque o client Anthropic é síncrono.
        Opcionalmente usa circuit breaker para resiliência.
        """

        def _sync_call():
            return self._client.messages.create(**kwargs)

        async def _async_call():
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _sync_call)

        if self._use_circuit_breaker:
            return await circuit_claude.executar(_async_call)
        else:
            return await _async_call()

    def _convert_messages(self, messages: List[Message]) -> List[dict]:
        """Converte nossas mensagens para formato Anthropic."""
        result = []
        for msg in messages:
            # Se content já é uma lista (tool_use blocks), manter como está
            if isinstance(msg.content, list):
                result.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )
            else:
                result.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )
        return result

    def _convert_response(self, response: Any) -> LLMResponse:
        """Converte response da Anthropic para nosso formato."""
        # Extrair conteúdo de texto
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        input=block.input,
                    )
                )

        # Mapear stop reason
        stop_reason = self.STOP_REASON_MAP.get(response.stop_reason, StopReason.END_TURN)

        # Extrair usage
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            model_id=response.model,
            raw_response=response,
        )


# Factory functions para criar providers com configurações padrão
def create_haiku_provider() -> AnthropicProvider:
    """Cria provider com Claude Haiku (mais barato)."""
    return AnthropicProvider(model_id=settings.LLM_MODEL)


def create_sonnet_provider() -> AnthropicProvider:
    """Cria provider com Claude Sonnet (mais capaz)."""
    return AnthropicProvider(model_id=settings.LLM_MODEL_COMPLEX)
