"""
Testes para o circuit breaker.
"""
import pytest
import asyncio
from datetime import datetime, timedelta

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    obter_status_circuits,
)


class TestCircuitBreaker:
    """Testes para a classe CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_circuit_comeca_fechado(self):
        """Circuit deve começar no estado CLOSED."""
        cb = CircuitBreaker(nome="test")
        assert cb.estado == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_chamada_sucesso_mantem_fechado(self):
        """Chamada bem-sucedida mantém circuit fechado."""
        cb = CircuitBreaker(nome="test")

        async def funcao_sucesso():
            return "ok"

        resultado = await cb.executar(funcao_sucesso)
        assert resultado == "ok"
        assert cb.estado == CircuitState.CLOSED
        assert cb.falhas_consecutivas == 0

    @pytest.mark.asyncio
    async def test_circuit_abre_apos_falhas(self):
        """Circuit deve abrir após número configurado de falhas."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=3)

        async def funcao_falha():
            raise Exception("Erro simulado")

        # 3 falhas devem abrir o circuit
        for i in range(3):
            with pytest.raises(Exception):
                await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN
        assert cb.falhas_consecutivas == 3

    @pytest.mark.asyncio
    async def test_circuit_aberto_bloqueia_chamadas(self):
        """Circuit aberto deve bloquear chamadas sem fallback."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1)

        async def funcao_falha():
            raise Exception("Erro")

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN

        # Próxima chamada deve ser bloqueada
        with pytest.raises(CircuitOpenError):
            await cb.executar(funcao_falha)

    @pytest.mark.asyncio
    async def test_circuit_usa_fallback_quando_aberto(self):
        """Circuit aberto deve usar fallback se fornecido."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1)

        async def funcao_falha():
            raise Exception("Erro")

        async def fallback():
            return "fallback_value"

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Usar fallback
        resultado = await cb.executar(funcao_falha, fallback=fallback)
        assert resultado == "fallback_value"

    @pytest.mark.asyncio
    async def test_circuit_fallback_sincrono(self):
        """Fallback síncrono também deve funcionar."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1)

        async def funcao_falha():
            raise Exception("Erro")

        def fallback_sync():
            return "sync_fallback"

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Usar fallback síncrono
        resultado = await cb.executar(funcao_falha, fallback=fallback_sync)
        assert resultado == "sync_fallback"

    @pytest.mark.asyncio
    async def test_circuit_transiciona_para_half_open(self):
        """Circuit deve ir para HALF_OPEN após tempo de reset."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1, tempo_reset_segundos=0)

        async def funcao_falha():
            raise Exception("Erro")

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN

        # Forçar transição (tempo_reset=0)
        cb._verificar_transicao_half_open()

        assert cb.estado == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_recupera_apos_sucesso_em_half_open(self):
        """Circuit deve fechar após sucesso em HALF_OPEN."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1, tempo_reset_segundos=0)

        async def funcao_falha():
            raise Exception("Erro")

        async def funcao_sucesso():
            return "ok"

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Ir para half-open
        cb._verificar_transicao_half_open()
        assert cb.estado == CircuitState.HALF_OPEN

        # Sucesso deve fechar
        resultado = await cb.executar(funcao_sucesso)
        assert resultado == "ok"
        assert cb.estado == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_circuit_volta_para_open_se_falha_em_half_open(self):
        """Circuit deve voltar para OPEN se falhar em HALF_OPEN."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1, tempo_reset_segundos=0)

        async def funcao_falha():
            raise Exception("Erro")

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        # Ir para half-open
        cb._verificar_transicao_half_open()
        assert cb.estado == CircuitState.HALF_OPEN

        # Falha deve voltar para open
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_sucesso_reseta_contador_falhas(self):
        """Sucesso deve resetar contador de falhas."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=3)

        async def funcao_falha():
            raise Exception("Erro")

        async def funcao_sucesso():
            return "ok"

        # 2 falhas
        for _ in range(2):
            with pytest.raises(Exception):
                await cb.executar(funcao_falha)

        assert cb.falhas_consecutivas == 2

        # 1 sucesso reseta
        await cb.executar(funcao_sucesso)
        assert cb.falhas_consecutivas == 0

    @pytest.mark.asyncio
    async def test_timeout_nao_conta_como_falha(self):
        """Sprint 36 T02.3: Timeout NÃO deve ser contado como falha para abrir circuit."""
        from app.services.circuit_breaker import ErrorType

        cb = CircuitBreaker(nome="test", falhas_para_abrir=1, timeout_segundos=0.1)

        async def funcao_lenta():
            await asyncio.sleep(1)
            return "ok"

        with pytest.raises(asyncio.TimeoutError):
            await cb.executar(funcao_lenta)

        # Timeout é registrado mas NÃO incrementa falhas (decisão de design Sprint 36)
        assert cb.falhas_consecutivas == 0
        assert cb.estado == CircuitState.CLOSED  # Circuit não abre por timeout
        assert cb.ultimo_erro_tipo == ErrorType.TIMEOUT

    def test_status_retorna_info_correta(self):
        """Status deve retornar informações corretas."""
        cb = CircuitBreaker(nome="test_circuit")
        status = cb.status()

        assert status["nome"] == "test_circuit"
        assert status["estado"] == "closed"
        assert status["falhas_consecutivas"] == 0
        assert status["ultima_falha"] is None
        assert status["ultimo_sucesso"] is None

    @pytest.mark.asyncio
    async def test_reset_manual(self):
        """Reset manual deve funcionar."""
        cb = CircuitBreaker(nome="test", falhas_para_abrir=1)

        async def funcao_falha():
            raise Exception("Erro")

        # Abrir circuit
        with pytest.raises(Exception):
            await cb.executar(funcao_falha)

        assert cb.estado == CircuitState.OPEN

        # Reset manual
        cb.reset()
        assert cb.estado == CircuitState.CLOSED
        assert cb.falhas_consecutivas == 0


class TestCircuitsGlobais:
    """Testes para as instâncias globais de circuit breaker."""

    def test_obter_status_circuits(self):
        """Deve retornar status de todos os circuits."""
        status = obter_status_circuits()

        assert "evolution" in status
        assert "claude" in status
        assert "supabase" in status

        # Todos devem ter os campos esperados
        for nome, circuit_status in status.items():
            assert "nome" in circuit_status
            assert "estado" in circuit_status
            assert "falhas_consecutivas" in circuit_status
