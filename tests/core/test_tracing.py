"""
Testes do módulo de tracing.

Sprint 31 - S31.E3.5
"""
import pytest
import asyncio

from app.core.tracing import (
    generate_trace_id,
    set_trace_id,
    get_trace_id,
    clear_trace_id,
    TraceContext,
    get_trace_prefix,
)


class TestGenerateTraceId:
    """Testes da geração de trace ID."""

    def test_gera_trace_id(self):
        """Deve gerar trace ID."""
        trace_id = generate_trace_id()
        assert trace_id is not None
        assert len(trace_id) == 8

    def test_trace_id_unico(self):
        """Deve gerar IDs únicos."""
        ids = [generate_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100  # Todos únicos

    def test_trace_id_hex(self):
        """Deve gerar apenas caracteres hexadecimais."""
        trace_id = generate_trace_id()
        assert all(c in "0123456789abcdef" for c in trace_id)


class TestContextVar:
    """Testes das context vars."""

    def test_set_e_get(self):
        """Deve definir e recuperar trace ID."""
        clear_trace_id()  # Limpar estado anterior

        set_trace_id("abc12345")
        assert get_trace_id() == "abc12345"

        clear_trace_id()

    def test_get_sem_set(self):
        """Deve retornar None se não definido."""
        clear_trace_id()
        assert get_trace_id() is None

    def test_clear(self):
        """Deve limpar trace ID."""
        set_trace_id("test123")
        clear_trace_id()
        assert get_trace_id() is None


class TestTraceContext:
    """Testes do context manager."""

    def test_context_manager(self):
        """Deve funcionar como context manager."""
        clear_trace_id()

        with TraceContext() as trace_id:
            assert trace_id is not None
            assert len(trace_id) == 8
            assert get_trace_id() == trace_id

        # Após sair do contexto
        assert get_trace_id() is None

    def test_context_manager_com_id(self):
        """Deve aceitar ID específico."""
        clear_trace_id()

        with TraceContext("custom12") as trace_id:
            assert trace_id == "custom12"
            assert get_trace_id() == "custom12"

    def test_context_manager_aninhado(self):
        """Deve funcionar com contextos aninhados."""
        clear_trace_id()

        with TraceContext("outer123") as outer:
            assert get_trace_id() == "outer123"

            with TraceContext("inner456") as inner:
                assert get_trace_id() == "inner456"

            # Restaura o anterior
            assert get_trace_id() == "outer123"

        assert get_trace_id() is None


class TestGetTracePrefix:
    """Testes do prefixo de trace."""

    def test_com_trace(self):
        """Deve retornar prefixo formatado."""
        set_trace_id("abc12345")
        assert get_trace_prefix() == "[abc12345] "
        clear_trace_id()

    def test_sem_trace(self):
        """Deve retornar string vazia."""
        clear_trace_id()
        assert get_trace_prefix() == ""


class TestAsyncPropagation:
    """Testes de propagação em código async."""

    @pytest.mark.asyncio
    async def test_propaga_em_async(self):
        """Deve propagar trace ID em código async."""
        clear_trace_id()
        set_trace_id("async123")

        async def inner_func():
            return get_trace_id()

        result = await inner_func()
        assert result == "async123"
        clear_trace_id()

    @pytest.mark.asyncio
    async def test_propaga_em_gather(self):
        """Deve propagar em asyncio.gather."""
        clear_trace_id()
        set_trace_id("gather12")

        async def check_trace():
            return get_trace_id()

        results = await asyncio.gather(
            check_trace(),
            check_trace(),
            check_trace(),
        )

        assert all(r == "gather12" for r in results)
        clear_trace_id()

    @pytest.mark.asyncio
    async def test_context_manager_async(self):
        """Deve funcionar em async com context manager."""
        clear_trace_id()

        async def async_work():
            return get_trace_id()

        with TraceContext("async456"):
            result = await async_work()
            assert result == "async456"
