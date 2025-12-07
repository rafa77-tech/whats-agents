"""
Testes para circuit breakers.
"""
import pytest
import asyncio
from unittest.mock import patch

from app.services.circuit_breaker import (
    circuit_evolution,
    circuit_claude,
    circuit_supabase,
    CircuitState,
    CircuitOpenError
)


@pytest.fixture(autouse=True)
def reset_circuits():
    """Reset todos os circuits antes de cada teste."""
    circuit_evolution.estado = CircuitState.CLOSED
    circuit_evolution.falhas_consecutivas = 0
    circuit_evolution.ultima_falha = None
    circuit_claude.estado = CircuitState.CLOSED
    circuit_claude.falhas_consecutivas = 0
    circuit_claude.ultima_falha = None
    circuit_supabase.estado = CircuitState.CLOSED
    circuit_supabase.falhas_consecutivas = 0
    circuit_supabase.ultima_falha = None
    yield


class TestCircuitEvolution:
    """Testes para circuit breaker da Evolution API."""
    
    @pytest.mark.asyncio
    async def test_abre_apos_3_falhas(self):
        """Evolution circuit abre após 3 falhas consecutivas."""
        async def sempre_falha():
            raise Exception("Connection refused")
        
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_evolution.executar(sempre_falha)
        
        assert circuit_evolution.estado == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_fallback_quando_aberto(self):
        """Usa fallback quando circuit está aberto."""
        circuit_evolution.estado = CircuitState.OPEN
        
        async def funcao_principal():
            return "principal"
        
        async def fallback():
            return "fallback"
        
        resultado = await circuit_evolution.executar(
            funcao_principal,
            fallback=fallback
        )
        assert resultado == "fallback"
    
    @pytest.mark.asyncio
    async def test_levanta_erro_sem_fallback(self):
        """Levanta CircuitOpenError quando aberto e sem fallback."""
        circuit_evolution.estado = CircuitState.OPEN
        
        async def funcao():
            return "ok"
        
        with pytest.raises(CircuitOpenError):
            await circuit_evolution.executar(funcao)


class TestCircuitClaude:
    """Testes para circuit breaker da Claude API."""
    
    @pytest.mark.asyncio
    async def test_timeout_conta_como_falha(self):
        """Timeout na API do Claude conta como falha."""
        async def func_lenta():
            await asyncio.sleep(100)  # Nunca completa
        
        with pytest.raises(asyncio.TimeoutError):
            await circuit_claude.executar(func_lenta)
        
        assert circuit_claude.falhas_consecutivas == 1
    
    @pytest.mark.asyncio
    async def test_recuperacao_apos_sucesso(self):
        """Circuit volta a CLOSED após sucesso em HALF_OPEN."""
        circuit_claude.estado = CircuitState.HALF_OPEN
        
        async def sucesso():
            return "ok"
        
        resultado = await circuit_claude.executar(sucesso)
        assert resultado == "ok"
        assert circuit_claude.estado == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_transicao_para_half_open(self):
        """Circuit transiciona para HALF_OPEN após tempo de reset."""
        # Abrir circuit
        circuit_claude.estado = CircuitState.OPEN
        circuit_claude.ultima_falha = None  # Simular que passou tempo suficiente
        
        # Mock datetime para simular tempo passado
        from datetime import datetime, timedelta
        circuit_claude.ultima_falha = datetime.now() - timedelta(seconds=61)
        
        # Verificar transição
        circuit_claude._verificar_transicao_half_open()
        assert circuit_claude.estado == CircuitState.HALF_OPEN


class TestCircuitSupabase:
    """Testes para circuit breaker do Supabase."""
    
    @pytest.mark.asyncio
    async def test_reset_manual(self):
        """Reset manual volta circuit para CLOSED."""
        circuit_supabase.estado = CircuitState.OPEN
        circuit_supabase.falhas_consecutivas = 5
        
        circuit_supabase.reset()
        
        assert circuit_supabase.estado == CircuitState.CLOSED
        assert circuit_supabase.falhas_consecutivas == 0
    
    @pytest.mark.asyncio
    async def test_sucesso_reseta_falhas(self):
        """Sucesso reseta contador de falhas."""
        circuit_supabase.falhas_consecutivas = 2
        
        async def sucesso():
            return "ok"
        
        await circuit_supabase.executar(sucesso)
        
        assert circuit_supabase.falhas_consecutivas == 0

