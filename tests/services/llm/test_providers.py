"""
Testes dos LLM Providers.

Sprint 31 - S31.E1.6
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.llm.models import (
    LLMRequest,
    LLMResponse,
    Message,
    MessageRole,
    ToolCall,
    ToolDefinition,
    ToolResult,
    StopReason,
    UsageStats,
)
from app.services.llm.mock_provider import (
    MockLLMProvider,
    create_mock_that_returns,
    create_mock_that_calls_tool,
    create_mock_that_fails,
    create_mock_with_sequence,
)
from app.services.llm.protocol import LLMProvider, LLMError


class TestMessage:
    """Testes da dataclass Message."""

    def test_create_user_message(self):
        """Deve criar mensagem de usuário."""
        msg = Message.user("Olá")
        assert msg.role == MessageRole.USER
        assert msg.content == "Olá"

    def test_create_assistant_message(self):
        """Deve criar mensagem de assistente."""
        msg = Message.assistant("Oi!")
        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Oi!"

    def test_create_system_message(self):
        """Deve criar mensagem de sistema."""
        msg = Message.system("Você é um assistente.")
        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "Você é um assistente."

    def test_to_dict(self):
        """Deve converter para dict."""
        msg = Message.user("Teste")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Teste"}

    def test_message_is_immutable(self):
        """Message deve ser imutável (frozen)."""
        msg = Message.user("Teste")
        with pytest.raises(AttributeError):
            msg.content = "Novo"


class TestToolDefinition:
    """Testes da dataclass ToolDefinition."""

    def test_create_tool_definition(self):
        """Deve criar definição de tool."""
        tool = ToolDefinition(
            name="buscar_vagas",
            description="Busca vagas disponíveis",
            input_schema={"type": "object", "properties": {}},
        )
        assert tool.name == "buscar_vagas"
        assert tool.description == "Busca vagas disponíveis"

    def test_to_dict(self):
        """Deve converter para dict."""
        tool = ToolDefinition(
            name="test_tool",
            description="Test",
            input_schema={"type": "object"},
        )
        d = tool.to_dict()
        assert d["name"] == "test_tool"
        assert d["description"] == "Test"
        assert "input_schema" in d


class TestToolResult:
    """Testes da dataclass ToolResult."""

    def test_create_tool_result(self):
        """Deve criar resultado de tool."""
        result = ToolResult(
            tool_call_id="123",
            content='{"vagas": []}',
        )
        assert result.tool_call_id == "123"
        assert result.is_error is False

    def test_to_dict(self):
        """Deve converter para formato de API."""
        result = ToolResult(tool_call_id="abc", content="resultado")
        d = result.to_dict()
        assert d["type"] == "tool_result"
        assert d["tool_use_id"] == "abc"
        assert d["content"] == "resultado"


class TestLLMRequest:
    """Testes da dataclass LLMRequest."""

    def test_create_simple_request(self):
        """Deve criar request simples."""
        request = LLMRequest(
            messages=[Message.user("Oi")],
            max_tokens=100,
        )
        assert len(request.messages) == 1
        assert request.max_tokens == 100
        assert request.tools is None
        assert request.system_prompt is None

    def test_create_request_with_tools(self):
        """Deve criar request com tools."""
        tool = ToolDefinition(
            name="buscar_vagas",
            description="Busca vagas",
            input_schema={"type": "object"},
        )
        request = LLMRequest(
            messages=[Message.user("Buscar vagas")],
            tools=[tool],
        )
        assert len(request.tools) == 1
        assert request.tools[0].name == "buscar_vagas"

    def test_trace_id_propagation(self):
        """Deve propagar trace_id."""
        request = LLMRequest(
            messages=[Message.user("Teste")],
            trace_id="trace-123",
        )
        assert request.trace_id == "trace-123"

    def test_default_values(self):
        """Deve ter valores default corretos."""
        request = LLMRequest(messages=[Message.user("Test")])
        assert request.max_tokens == 300
        assert request.temperature == 0.7


class TestLLMResponse:
    """Testes da dataclass LLMResponse."""

    def test_simple_response(self):
        """Deve criar response simples."""
        response = LLMResponse(content="Olá!")
        assert response.content == "Olá!"
        assert response.has_tool_calls is False
        assert len(response.tool_calls) == 0

    def test_response_with_tool_calls(self):
        """Deve criar response com tool calls."""
        response = LLMResponse(
            content="",
            tool_calls=[ToolCall(id="1", name="test", input={})],
            stop_reason=StopReason.TOOL_USE,
        )
        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.stop_reason == StopReason.TOOL_USE

    def test_usage_properties(self):
        """Deve expor usage via properties."""
        response = LLMResponse(
            content="Test",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert response.input_tokens == 100
        assert response.output_tokens == 50

    def test_usage_defaults_to_zero(self):
        """Deve retornar 0 se usage não definido."""
        response = LLMResponse(content="Test")
        assert response.input_tokens == 0
        assert response.output_tokens == 0


class TestUsageStats:
    """Testes da dataclass UsageStats."""

    def test_add_usage(self):
        """Deve acumular uso."""
        stats = UsageStats()
        response1 = LLMResponse(content="A", usage={"input_tokens": 10, "output_tokens": 5})
        response2 = LLMResponse(content="B", usage={"input_tokens": 20, "output_tokens": 10})

        stats.add(response1)
        stats.add(response2)

        assert stats.total_input_tokens == 30
        assert stats.total_output_tokens == 15
        assert stats.total_requests == 2
        assert stats.total_tokens == 45


class TestMockLLMProvider:
    """Testes do MockLLMProvider."""

    @pytest.mark.asyncio
    async def test_returns_configured_response(self):
        """Deve retornar resposta configurada."""
        mock = MockLLMProvider(default_response="Resposta fixa")
        request = LLMRequest(messages=[Message.user("Oi")])

        response = await mock.generate(request)

        assert response.content == "Resposta fixa"

    @pytest.mark.asyncio
    async def test_tracks_calls(self):
        """Deve rastrear chamadas."""
        mock = MockLLMProvider()
        request = LLMRequest(messages=[Message.user("Teste")])

        await mock.generate(request)
        await mock.generate(request)

        assert mock.call_count == 2
        mock.assert_called()

    @pytest.mark.asyncio
    async def test_last_call_property(self):
        """Deve retornar última chamada."""
        mock = MockLLMProvider()
        request1 = LLMRequest(messages=[Message.user("Primeira")])
        request2 = LLMRequest(messages=[Message.user("Segunda")])

        await mock.generate(request1)
        await mock.generate(request2)

        assert mock.last_call == request2

    @pytest.mark.asyncio
    async def test_returns_tool_calls(self):
        """Deve retornar tool calls configuradas."""
        mock = create_mock_that_calls_tool("buscar_vagas", {"regiao": "SP"})
        request = LLMRequest(messages=[Message.user("Buscar")])

        response = await mock.generate(request)

        assert response.has_tool_calls
        assert response.tool_calls[0].name == "buscar_vagas"
        assert response.tool_calls[0].input == {"regiao": "SP"}
        assert response.stop_reason == StopReason.TOOL_USE

    @pytest.mark.asyncio
    async def test_fails_when_configured(self):
        """Deve falhar quando configurado."""
        mock = create_mock_that_fails("Erro simulado")
        request = LLMRequest(messages=[Message.user("Teste")])

        with pytest.raises(LLMError) as exc_info:
            await mock.generate(request)

        assert "Erro simulado" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_callback_response(self):
        """Deve usar callback para resposta dinâmica."""
        def custom_callback(req: LLMRequest) -> LLMResponse:
            last_msg = req.messages[-1].content
            return LLMResponse(content=f"Recebi: {last_msg}")

        mock = MockLLMProvider(response_callback=custom_callback)
        request = LLMRequest(messages=[Message.user("Olá mundo")])

        response = await mock.generate(request)

        assert response.content == "Recebi: Olá mundo"

    @pytest.mark.asyncio
    async def test_sequence_response(self):
        """Deve retornar respostas em sequência."""
        responses = [
            LLMResponse(content="Primeira"),
            LLMResponse(content="Segunda"),
            LLMResponse(content="Terceira"),
        ]
        mock = create_mock_with_sequence(responses)
        request = LLMRequest(messages=[Message.user("Test")])

        r1 = await mock.generate(request)
        r2 = await mock.generate(request)
        r3 = await mock.generate(request)

        assert r1.content == "Primeira"
        assert r2.content == "Segunda"
        assert r3.content == "Terceira"

    @pytest.mark.asyncio
    async def test_assert_called_with_tool(self):
        """Deve verificar se tool estava disponível."""
        mock = MockLLMProvider()
        tool = ToolDefinition(name="minha_tool", description="Test", input_schema={})
        request = LLMRequest(messages=[Message.user("Test")], tools=[tool])

        await mock.generate(request)

        mock.assert_called_with_tool("minha_tool")

    @pytest.mark.asyncio
    async def test_assert_called_with_tool_fails(self):
        """Deve falhar se tool não estava disponível."""
        mock = MockLLMProvider()
        tool = ToolDefinition(name="outra_tool", description="Test", input_schema={})
        request = LLMRequest(messages=[Message.user("Test")], tools=[tool])

        await mock.generate(request)

        with pytest.raises(AssertionError):
            mock.assert_called_with_tool("tool_inexistente")

    @pytest.mark.asyncio
    async def test_generate_with_tools_tracks_calls(self):
        """Deve rastrear chamadas de continuação."""
        mock = MockLLMProvider()
        request = LLMRequest(messages=[Message.user("Test")])
        results = [ToolResult(tool_call_id="1", content="resultado")]

        await mock.generate_with_tools(request, results)

        assert len(mock.tool_continuation_calls) == 1
        assert mock.tool_continuation_calls[0] == (request, results)

    def test_reset_clears_history(self):
        """Deve limpar histórico no reset."""
        mock = MockLLMProvider()
        mock.calls.append(LLMRequest(messages=[]))
        mock._sequence_index = 5

        mock.reset()

        assert mock.call_count == 0
        assert mock._sequence_index == 0

    @pytest.mark.asyncio
    async def test_assert_system_prompt_contains(self):
        """Deve verificar conteúdo do system prompt."""
        mock = MockLLMProvider()
        request = LLMRequest(
            messages=[Message.user("Test")],
            system_prompt="Você é a Julia, uma escalista.",
        )

        await mock.generate(request)

        mock.assert_system_prompt_contains("Julia")
        mock.assert_system_prompt_contains("escalista")

    @pytest.mark.asyncio
    async def test_assert_not_called(self):
        """Deve verificar que não foi chamado."""
        mock = MockLLMProvider()
        mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_assert_called_once(self):
        """Deve verificar chamada única."""
        mock = MockLLMProvider()
        request = LLMRequest(messages=[Message.user("Test")])

        await mock.generate(request)

        mock.assert_called_once()


class TestProtocolCompliance:
    """Testes de conformidade com o Protocol."""

    def test_mock_implements_protocol(self):
        """MockLLMProvider deve implementar LLMProvider."""
        mock = MockLLMProvider()
        assert isinstance(mock, LLMProvider)

    def test_mock_has_model_id(self):
        """Mock deve ter model_id."""
        mock = MockLLMProvider(model_id="test-model")
        assert mock.model_id == "test-model"


class TestLLMError:
    """Testes da classe LLMError."""

    def test_error_attributes(self):
        """Deve ter atributos corretos."""
        error = LLMError(
            "Mensagem de erro",
            provider="anthropic",
            retryable=True,
            original_error=ValueError("Original"),
        )

        assert "Mensagem de erro" in str(error)
        assert error.provider == "anthropic"
        assert error.retryable is True
        assert isinstance(error.original_error, ValueError)

    def test_error_string_includes_provider(self):
        """String do erro deve incluir provider."""
        error = LLMError("Teste", provider="openai")
        assert "[openai]" in str(error)


# Testes de integração (requerem API key - skip se não disponível)
@pytest.mark.integration
class TestAnthropicProviderIntegration:
    """Testes de integração com Anthropic (requer API key)."""

    @pytest.fixture
    def provider(self):
        """Cria provider real (skip se sem API key)."""
        import os
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY não configurada")

        from app.services.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(use_circuit_breaker=False)

    @pytest.mark.asyncio
    async def test_simple_generation(self, provider):
        """Deve gerar resposta simples."""
        request = LLMRequest(
            messages=[Message.user("Diga apenas 'OK' sem mais nada")],
            max_tokens=10,
        )

        try:
            response = await provider.generate(request)
        except Exception as e:
            if "credit balance" in str(e).lower() or "billing" in str(e).lower():
                pytest.skip("Anthropic API sem créditos suficientes")
            raise

        assert response.content is not None
        assert len(response.content) > 0
        assert response.input_tokens > 0
        assert response.output_tokens > 0
