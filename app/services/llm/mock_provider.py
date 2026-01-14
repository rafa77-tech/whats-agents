"""
Mock LLM Provider - Para testes sem chamadas reais.

Sprint 31 - S31.E1.4

Este provider permite testar código que usa LLM sem custos ou latência.
"""
from typing import List, Optional, Callable
from dataclasses import dataclass, field

from .protocol import LLMError
from .models import (
    LLMRequest,
    LLMResponse,
    ToolCall,
    ToolResult,
    StopReason,
)


@dataclass
class MockLLMProvider:
    """
    Provider mockado para testes.

    Permite configurar respostas fixas ou dinâmicas.

    Exemplo de uso básico:
        mock = MockLLMProvider(default_response="Olá!")
        response = await mock.generate(request)
        assert response.content == "Olá!"

    Exemplo com tool calls:
        mock = MockLLMProvider(
            tool_calls=[ToolCall(id="1", name="buscar_vagas", input={})]
        )
        response = await mock.generate(request)
        assert response.has_tool_calls

    Exemplo com callback:
        def custom_response(request):
            return LLMResponse(content=f"Recebi: {request.messages[-1].content}")

        mock = MockLLMProvider(response_callback=custom_response)
    """

    # Configurações
    default_response: str = "Mock response"
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: StopReason = StopReason.END_TURN
    model_id: str = "mock-model"

    # Callback opcional para respostas dinâmicas
    response_callback: Optional[Callable[[LLMRequest], LLMResponse]] = None

    # Tracking de chamadas (para assertions em testes)
    calls: List[LLMRequest] = field(default_factory=list)
    tool_continuation_calls: List[tuple] = field(default_factory=list)

    # Simular erros
    should_fail: bool = False
    fail_message: str = "Mock error"

    # Sequência de respostas (para múltiplas chamadas)
    response_sequence: List[LLMResponse] = field(default_factory=list)
    _sequence_index: int = field(default=0, repr=False)

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Gera resposta mockada.

        Args:
            request: LLMRequest (será registrado para assertions)

        Returns:
            LLMResponse configurada ou via callback
        """
        # Registrar chamada
        self.calls.append(request)

        # Simular erro se configurado
        if self.should_fail:
            raise LLMError(
                self.fail_message,
                provider="mock",
                retryable=False,
            )

        # Usar callback se fornecido
        if self.response_callback:
            return self.response_callback(request)

        # Usar sequência se configurada
        if self.response_sequence and self._sequence_index < len(self.response_sequence):
            response = self.response_sequence[self._sequence_index]
            self._sequence_index += 1
            return response

        # Determinar stop_reason baseado em tool_calls
        actual_stop_reason = self.stop_reason
        if self.tool_calls:
            actual_stop_reason = StopReason.TOOL_USE

        # Retornar response padrão
        return LLMResponse(
            content=self.default_response,
            tool_calls=list(self.tool_calls),  # Cópia para evitar mutação
            stop_reason=actual_stop_reason,
            usage={"input_tokens": 10, "output_tokens": 20},
            model_id=self.model_id,
        )

    async def generate_with_tools(
        self,
        request: LLMRequest,
        tool_results: List[ToolResult],
    ) -> LLMResponse:
        """
        Continua após tool execution (mockado).

        Registra a chamada e retorna response configurada.
        """
        self.tool_continuation_calls.append((request, tool_results))

        if self.response_callback:
            return self.response_callback(request)

        # Usar sequência se configurada
        if self.response_sequence and self._sequence_index < len(self.response_sequence):
            response = self.response_sequence[self._sequence_index]
            self._sequence_index += 1
            return response

        return LLMResponse(
            content=f"Processado {len(tool_results)} tool results",
            tool_calls=[],
            stop_reason=StopReason.END_TURN,
            usage={"input_tokens": 5, "output_tokens": 10},
            model_id=self.model_id,
        )

    # Métodos auxiliares para testes

    def reset(self):
        """Limpa histórico de chamadas e reseta sequência."""
        self.calls.clear()
        self.tool_continuation_calls.clear()
        self._sequence_index = 0

    @property
    def call_count(self) -> int:
        """Número de chamadas a generate()."""
        return len(self.calls)

    @property
    def last_call(self) -> Optional[LLMRequest]:
        """Última chamada feita."""
        return self.calls[-1] if self.calls else None

    @property
    def last_messages(self) -> List:
        """Mensagens da última chamada."""
        if self.last_call:
            return self.last_call.messages
        return []

    def assert_called(self):
        """Asserta que generate() foi chamado."""
        assert self.call_count > 0, "MockLLMProvider.generate() não foi chamado"

    def assert_not_called(self):
        """Asserta que generate() NÃO foi chamado."""
        assert self.call_count == 0, f"MockLLMProvider.generate() foi chamado {self.call_count}x"

    def assert_called_once(self):
        """Asserta que generate() foi chamado exatamente 1 vez."""
        assert self.call_count == 1, f"MockLLMProvider.generate() chamado {self.call_count}x, esperado 1x"

    def assert_called_with_tool(self, tool_name: str):
        """Asserta que foi chamado com determinada tool disponível."""
        assert self.last_call is not None, "Nenhuma chamada registrada"
        assert self.last_call.tools is not None, "Chamada não incluiu tools"
        tool_names = [t.name for t in self.last_call.tools]
        assert tool_name in tool_names, f"Tool {tool_name} não estava disponível. Tools: {tool_names}"

    def assert_system_prompt_contains(self, text: str):
        """Asserta que system prompt contém determinado texto."""
        assert self.last_call is not None, "Nenhuma chamada registrada"
        assert self.last_call.system_prompt is not None, "Chamada não incluiu system_prompt"
        assert text in self.last_call.system_prompt, (
            f"System prompt não contém '{text}'. "
            f"Início: {self.last_call.system_prompt[:100]}..."
        )


# Factories para casos comuns

def create_mock_that_returns(content: str) -> MockLLMProvider:
    """Cria mock que sempre retorna o conteúdo especificado."""
    return MockLLMProvider(default_response=content)


def create_mock_that_calls_tool(
    tool_name: str,
    tool_input: dict = None,
    tool_id: str = "mock-tool-1",
) -> MockLLMProvider:
    """Cria mock que retorna uma chamada de tool."""
    return MockLLMProvider(
        tool_calls=[ToolCall(
            id=tool_id,
            name=tool_name,
            input=tool_input or {},
        )],
        stop_reason=StopReason.TOOL_USE,
        default_response="",  # Quando há tool_use, geralmente não há texto
    )


def create_mock_that_fails(message: str = "Mock error") -> MockLLMProvider:
    """Cria mock que sempre falha."""
    return MockLLMProvider(should_fail=True, fail_message=message)


def create_mock_with_sequence(responses: List[LLMResponse]) -> MockLLMProvider:
    """Cria mock que retorna respostas em sequência."""
    return MockLLMProvider(response_sequence=responses)
