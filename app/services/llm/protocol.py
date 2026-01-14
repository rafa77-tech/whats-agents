"""
LLM Provider Protocol - Interface para qualquer provider de LLM.

Sprint 31 - S31.E1.1

Este módulo define a interface que todos os providers devem implementar.
Usar Protocol permite duck typing com type checking estático.

Exemplo de uso:
    def minha_funcao(provider: LLMProvider):
        response = await provider.generate(request)
"""
from typing import Protocol, Optional, List, runtime_checkable

from .models import LLMRequest, LLMResponse, ToolResult


@runtime_checkable
class LLMProvider(Protocol):
    """
    Interface para providers de LLM.

    Qualquer classe que implemente estes métodos é um LLMProvider válido.
    Não precisa herdar explicitamente.

    Attributes:
        model_id: Identificador do modelo (ex: "claude-3-haiku-20240307")
    """

    @property
    def model_id(self) -> str:
        """Retorna o ID do modelo sendo usado."""
        ...

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Gera uma resposta do LLM.

        Args:
            request: Objeto LLMRequest com mensagens, tools, etc.

        Returns:
            LLMResponse com texto, tool_calls, e metadata.

        Raises:
            LLMError: Se houver erro na chamada ao provider.
        """
        ...

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[ToolResult],
    ) -> LLMResponse:
        """
        Continua geração após execução de tools.

        Args:
            request: Request original
            tool_results: Resultados das tools executadas

        Returns:
            LLMResponse com continuação

        Raises:
            LLMError: Se houver erro na chamada.
        """
        ...


class LLMError(Exception):
    """Erro genérico de LLM."""

    def __init__(
        self,
        message: str,
        provider: str = "unknown",
        retryable: bool = False,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable
        self.original_error = original_error

    def __str__(self) -> str:
        return f"[{self.provider}] {super().__str__()}"
