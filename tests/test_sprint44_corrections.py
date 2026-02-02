"""
Testes para correções da Sprint 44.

Sprint 44 T08.1: Testes para correções críticas.
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone


class TestLoggingContext:
    """Testes para o sistema de logging com contexto."""

    def test_mask_phone_full(self):
        """Testa mascaramento de telefone completo."""
        from app.core.logging import mask_phone

        assert mask_phone("5511999991234") == "5511...1234"
        assert mask_phone("11999991234") == "1199...1234"

    def test_mask_phone_short(self):
        """Testa mascaramento de telefone curto."""
        from app.core.logging import mask_phone

        assert mask_phone("1234") == "****"
        assert mask_phone("") == "****"
        assert mask_phone(None) == "****"

    def test_generate_trace_id(self):
        """Testa geração de trace_id."""
        from app.core.logging import generate_trace_id

        trace_id = generate_trace_id()
        assert len(trace_id) == 8
        assert isinstance(trace_id, str)

        # Deve gerar IDs únicos
        ids = [generate_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_set_and_get_trace_id(self):
        """Testa set/get de trace_id."""
        from app.core.logging import set_trace_id, get_trace_id, clear_log_context

        clear_log_context()

        # Gerar automaticamente
        tid = set_trace_id()
        assert get_trace_id() == tid

        # Definir manualmente
        set_trace_id("custom123")
        assert get_trace_id() == "custom123"

        clear_log_context()

    def test_log_context_manager(self):
        """Testa context manager de logging."""
        from app.core.logging import log_context, get_trace_id, clear_log_context
        from app.core.logging import _cliente_id, _conversa_id

        clear_log_context()

        # Fora do contexto
        assert get_trace_id() == ""

        with log_context(cliente_id="cli-123", conversa_id="conv-456"):
            assert _cliente_id.get() == "cli-123"
            assert _conversa_id.get() == "conv-456"
            assert get_trace_id() != ""  # Deve gerar um

        # Depois do contexto deve limpar
        assert _cliente_id.get() == ""
        assert _conversa_id.get() == ""


class TestToolRegistry:
    """Testes para o registry de tools."""

    def test_register_and_get_tool(self):
        """Testa registro e recuperação de tool."""
        from app.tools.registry import clear_registry, register_tool, get_tool

        clear_registry()

        @register_tool(
            name="test_tool",
            description="Tool de teste",
            input_schema={"type": "object"},
            category="test"
        )
        async def test_handler(input_data, medico, conversa):
            return {"success": True}

        tool = get_tool("test_tool")
        assert tool is not None
        assert tool["name"] == "test_tool"
        assert tool["category"] == "test"

        clear_registry()

    def test_get_all_tools(self):
        """Testa listagem de todas as tools."""
        from app.tools.registry import clear_registry, register_tool, get_all_tools

        clear_registry()

        @register_tool(name="tool1", description="T1", input_schema={})
        async def h1(i, m, c): pass

        @register_tool(name="tool2", description="T2", input_schema={})
        async def h2(i, m, c): pass

        tools = get_all_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "tool1" in names
        assert "tool2" in names

        clear_registry()

    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """Testa execução de tool com sucesso."""
        from app.tools.registry import clear_registry, register_tool, execute_tool

        clear_registry()

        @register_tool(name="echo", description="Echo", input_schema={})
        async def echo_handler(input_data, medico, conversa):
            return {"echo": input_data.get("msg")}

        result = await execute_tool("echo", {"msg": "test"}, {}, {})
        assert result["echo"] == "test"

        clear_registry()

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self):
        """Testa execução de tool desconhecida."""
        from app.tools.registry import clear_registry, execute_tool

        clear_registry()

        result = await execute_tool("unknown", {}, {}, {})
        assert result["success"] is False
        assert "desconhecida" in result["error"]


class TestHandoffKeywordRegex:
    """Testes para regex pré-compilados do HandoffKeywordProcessor."""

    def test_detect_confirmed_keywords(self):
        """Testa detecção de keywords de confirmação."""
        from app.pipeline.processors.handoff import HandoffKeywordProcessor

        processor = HandoffKeywordProcessor()

        assert processor._detectar_keyword("confirmado") == "confirmed"
        assert processor._detectar_keyword("FECHOU") == "confirmed"
        assert processor._detectar_keyword("tudo certo!") == "confirmed"
        assert processor._detectar_keyword("ok, fechou") == "confirmed"

    def test_detect_not_confirmed_keywords(self):
        """Testa detecção de keywords de não confirmação."""
        from app.pipeline.processors.handoff import HandoffKeywordProcessor

        processor = HandoffKeywordProcessor()

        assert processor._detectar_keyword("não fechou") == "not_confirmed"
        assert processor._detectar_keyword("desistiu") == "not_confirmed"
        assert processor._detectar_keyword("cancelou") == "not_confirmed"
        assert processor._detectar_keyword("não vai dar") == "not_confirmed"

    def test_detect_no_keyword(self):
        """Testa mensagens sem keywords."""
        from app.pipeline.processors.handoff import HandoffKeywordProcessor

        processor = HandoffKeywordProcessor()

        assert processor._detectar_keyword("oi, tudo bem?") is None
        assert processor._detectar_keyword("preciso de informações") is None
        assert processor._detectar_keyword("") is None


class TestConfigCentralization:
    """Testes para configurações centralizadas."""

    def test_llm_settings_exist(self):
        """Verifica que configurações de LLM existem."""
        from app.core.config import settings

        assert hasattr(settings, "LLM_MAX_TOKENS")
        assert hasattr(settings, "LLM_MAX_TOOL_ITERATIONS")
        assert hasattr(settings, "LLM_TIMEOUT_SEGUNDOS")
        assert hasattr(settings, "LLM_LOOP_TIMEOUT_SEGUNDOS")

    def test_pipeline_settings_exist(self):
        """Verifica que configurações de pipeline existem."""
        from app.core.config import settings

        assert hasattr(settings, "PIPELINE_MAX_CONCURRENT")
        assert settings.PIPELINE_MAX_CONCURRENT > 0

    def test_cache_settings_exist(self):
        """Verifica que configurações de cache existem."""
        from app.core.config import settings

        assert hasattr(settings, "CACHE_TTL_LLM_RESPONSE")
        assert hasattr(settings, "CACHE_TTL_PROMPTS")
        assert hasattr(settings, "CACHE_TTL_CONTEXTO")


class TestDistributedCircuitBreaker:
    """Testes para circuit breaker distribuído."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_creation(self):
        """Testa criação de circuit breaker distribuído."""
        from app.services.circuit_breaker import DistributedCircuitBreaker

        cb = DistributedCircuitBreaker("test_service")
        assert cb._redis_prefix == "circuit:test_service"

    @pytest.mark.asyncio
    async def test_circuit_breaker_fallback_on_redis_error(self):
        """Testa fallback para local quando Redis falha."""
        from app.services.circuit_breaker import DistributedCircuitBreaker, CircuitState

        with patch("app.services.circuit_breaker._get_redis") as mock_redis:
            mock_redis.return_value.get.side_effect = Exception("Redis down")

            cb = DistributedCircuitBreaker("test_fallback")

            # Deve usar fallback local
            state = await cb._get_state_async()
            assert state == CircuitState.CLOSED


class TestEventEmitter:
    """Testes para o event emitter."""

    @pytest.mark.asyncio
    async def test_emitir_offer_events_no_vagas(self):
        """Testa emissão de eventos sem vagas específicas."""
        from app.services.julia.event_emitter import emitir_offer_events

        with patch("app.services.julia.event_emitter.should_emit_event") as mock_should:
            mock_should.return_value = False  # Rollout desabilitado

            # Não deve fazer nada se rollout desabilitado
            await emitir_offer_events(
                cliente_id="cli-123",
                conversa_id="conv-456",
                resposta="Oi, temos vagas disponíveis!"
            )

            mock_should.assert_called_once()
