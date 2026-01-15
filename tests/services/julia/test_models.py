"""
Testes dos modelos do módulo Julia.

Sprint 31 - S31.E2.7
"""
import pytest

from app.services.julia.models import (
    JuliaContext,
    PolicyContext,
    ToolExecutionResult,
    GenerationResult,
    JuliaResponse,
)


class TestJuliaContext:
    """Testes da dataclass JuliaContext."""

    def test_criar_contexto_basico(self):
        """Deve criar contexto com dados mínimos."""
        ctx = JuliaContext(
            mensagem="Oi",
            medico={"nome": "Dr. Carlos"},
            conversa={"id": "123"},
        )
        assert ctx.mensagem == "Oi"
        assert ctx.medico["nome"] == "Dr. Carlos"
        assert ctx.conversa["id"] == "123"

    def test_valores_default(self):
        """Deve ter valores default corretos."""
        ctx = JuliaContext(
            mensagem="Oi",
            medico={},
            conversa={},
        )
        assert ctx.primeira_mensagem is False
        assert ctx.incluir_historico is True
        assert ctx.usar_tools is True
        assert ctx.historico_raw == []
        assert ctx.trace_id is None

    def test_contexto_com_todos_campos(self):
        """Deve criar contexto com todos os campos."""
        ctx = JuliaContext(
            mensagem="Olá",
            medico={"nome": "Dr. Ana"},
            conversa={"id": "456"},
            contexto_medico="Cardiologista experiente",
            contexto_vagas="3 vagas disponíveis",
            primeira_mensagem=True,
            trace_id="trace-abc",
        )
        assert ctx.contexto_medico == "Cardiologista experiente"
        assert ctx.primeira_mensagem is True
        assert ctx.trace_id == "trace-abc"


class TestPolicyContext:
    """Testes da dataclass PolicyContext."""

    def test_criar_policy_context_vazio(self):
        """Deve criar policy context vazio."""
        ctx = PolicyContext()
        assert ctx.policy_constraints == ""
        assert ctx.capabilities_gate is None
        assert ctx.mode_info is None
        assert ctx.tools_filtradas == []

    def test_criar_policy_context_com_constraints(self):
        """Deve criar policy context com constraints."""
        ctx = PolicyContext(
            policy_constraints="Não fale de preços",
        )
        assert ctx.policy_constraints == "Não fale de preços"


class TestToolExecutionResult:
    """Testes da dataclass ToolExecutionResult."""

    def test_criar_resultado_sucesso(self):
        """Deve criar resultado de sucesso."""
        result = ToolExecutionResult(
            tool_call_id="tool-123",
            tool_name="buscar_vagas",
            result={"vagas": [{"id": 1}]},
            success=True,
        )
        assert result.tool_call_id == "tool-123"
        assert result.tool_name == "buscar_vagas"
        assert result.success is True
        assert result.error is None

    def test_criar_resultado_erro(self):
        """Deve criar resultado de erro."""
        result = ToolExecutionResult(
            tool_call_id="tool-456",
            tool_name="reservar_plantao",
            result={},
            success=False,
            error="Vaga não encontrada",
        )
        assert result.success is False
        assert result.error == "Vaga não encontrada"

    def test_to_api_format_sucesso(self):
        """Deve converter para formato de API em sucesso."""
        result = ToolExecutionResult(
            tool_call_id="tool-789",
            tool_name="buscar_vagas",
            result={"vagas": []},
            success=True,
        )
        api_format = result.to_api_format()
        assert api_format["type"] == "tool_result"
        assert api_format["tool_use_id"] == "tool-789"
        assert "vagas" in api_format["content"]

    def test_to_api_format_erro(self):
        """Deve converter para formato de API em erro."""
        result = ToolExecutionResult(
            tool_call_id="tool-000",
            tool_name="test",
            result={},
            success=False,
            error="Erro de teste",
        )
        api_format = result.to_api_format()
        assert api_format["content"] == "Erro de teste"


class TestGenerationResult:
    """Testes da dataclass GenerationResult."""

    def test_criar_resultado_simples(self):
        """Deve criar resultado simples sem tool calls."""
        result = GenerationResult(text="Olá!")
        assert result.text == "Olá!"
        assert result.tool_calls == []
        assert result.has_tool_calls is False
        assert result.stop_reason == "end_turn"

    def test_criar_resultado_com_tools(self):
        """Deve criar resultado com tool calls."""
        result = GenerationResult(
            text="",
            tool_calls=[{"id": "1", "name": "buscar_vagas"}],
            stop_reason="tool_use",
        )
        assert result.has_tool_calls is True
        assert len(result.tool_calls) == 1
        assert result.stop_reason == "tool_use"

    def test_from_llm_response(self):
        """Deve criar de resposta do LLM legado."""
        llm_response = {
            "text": "Resposta",
            "tool_use": [{"id": "123", "name": "test"}],
            "stop_reason": "tool_use",
        }
        result = GenerationResult.from_llm_response(llm_response)
        assert result.text == "Resposta"
        assert len(result.tool_calls) == 1
        assert result.stop_reason == "tool_use"

    def test_from_llm_response_vazio(self):
        """Deve criar de resposta vazia."""
        result = GenerationResult.from_llm_response({})
        assert result.text == ""
        assert result.tool_calls == []
        assert result.stop_reason == "end_turn"


class TestJuliaResponse:
    """Testes da dataclass JuliaResponse."""

    def test_criar_resposta_sucesso(self):
        """Deve criar resposta de sucesso."""
        resp = JuliaResponse(
            texto="Oi, tudo bem?",
            tool_calls_executadas=2,
        )
        assert resp.texto == "Oi, tudo bem?"
        assert resp.sucesso is True
        assert resp.tool_calls_executadas == 2

    def test_criar_resposta_vazia(self):
        """Deve criar resposta vazia (falha)."""
        resp = JuliaResponse(texto="")
        assert resp.sucesso is False

    def test_resposta_com_metadata(self):
        """Deve criar resposta com metadata."""
        resp = JuliaResponse(
            texto="Resposta",
            retry_necessario=True,
            conhecimento_usado=True,
            trace_id="trace-xyz",
        )
        assert resp.retry_necessario is True
        assert resp.conhecimento_usado is True
        assert resp.trace_id == "trace-xyz"
