"""
Testes para o serviço de rate limiting.
"""
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime

from app.services.rate_limiter import (
    verificar_horario_permitido,
    verificar_limite_hora,
    verificar_limite_dia,
    verificar_intervalo_minimo,
    pode_enviar,
    calcular_delay_humanizado,
    registrar_envio,
    INTERVALO_MIN_SEGUNDOS,
    INTERVALO_MAX_SEGUNDOS,
    LIMITE_POR_HORA,
    LIMITE_POR_DIA,
)


class TestHorarioPermitido:
    """Testes para verificação de horário comercial."""

    @pytest.mark.asyncio
    async def test_horario_comercial_segunda_10h(self):
        """Segunda às 10h deve ser permitido."""
        # Mock datetime para segunda às 10h
        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 8, 10, 0)  # Segunda
            ok, motivo = await verificar_horario_permitido()
            assert ok is True
            assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_fora_horario_sabado(self):
        """Sábado deve ser bloqueado."""
        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 13, 10, 0)  # Sábado
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "fim de semana" in motivo.lower()

    @pytest.mark.asyncio
    async def test_fora_horario_domingo(self):
        """Domingo deve ser bloqueado."""
        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 14, 10, 0)  # Domingo
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "fim de semana" in motivo.lower()

    @pytest.mark.asyncio
    async def test_antes_horario_comercial(self):
        """Antes das 8h deve ser bloqueado."""
        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 8, 7, 30)  # Segunda 7:30
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "antes" in motivo.lower()

    @pytest.mark.asyncio
    async def test_apos_horario_comercial(self):
        """Após às 20h deve ser bloqueado."""
        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2025, 12, 8, 20, 30)  # Segunda 20:30
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "após" in motivo.lower()


class TestDelayHumanizado:
    """Testes para cálculo de delay humanizado."""

    def test_delay_dentro_limites(self):
        """Delay deve estar entre mínimo e máximo."""
        for _ in range(100):
            delay = calcular_delay_humanizado()
            assert delay >= INTERVALO_MIN_SEGUNDOS
            # Máximo é INTERVALO_MAX_SEGUNDOS + 20 (variação)
            assert delay <= INTERVALO_MAX_SEGUNDOS + 20

    def test_delay_variavel(self):
        """Delay deve variar entre chamadas."""
        delays = [calcular_delay_humanizado() for _ in range(20)]
        # Verifica que não são todos iguais
        assert len(set(delays)) > 1


class TestLimiteHora:
    """Testes para verificação de limite por hora."""

    @pytest.mark.asyncio
    async def test_dentro_limite(self):
        """Deve permitir quando dentro do limite."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value="5")
            ok, count = await verificar_limite_hora()
            assert ok is True
            assert count == 5

    @pytest.mark.asyncio
    async def test_limite_atingido(self):
        """Deve bloquear quando limite atingido."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(LIMITE_POR_HORA))
            ok, count = await verificar_limite_hora()
            assert ok is False
            assert count == LIMITE_POR_HORA

    @pytest.mark.asyncio
    async def test_erro_redis_permite(self):
        """Em caso de erro no Redis, deve permitir (fail open)."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
            ok, count = await verificar_limite_hora()
            assert ok is True


class TestLimiteDia:
    """Testes para verificação de limite por dia."""

    @pytest.mark.asyncio
    async def test_dentro_limite(self):
        """Deve permitir quando dentro do limite."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value="50")
            ok, count = await verificar_limite_dia()
            assert ok is True
            assert count == 50

    @pytest.mark.asyncio
    async def test_limite_atingido(self):
        """Deve bloquear quando limite diário atingido."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=str(LIMITE_POR_DIA))
            ok, count = await verificar_limite_dia()
            assert ok is False
            assert count == LIMITE_POR_DIA


class TestIntervaloMinimo:
    """Testes para verificação de intervalo mínimo entre mensagens."""

    @pytest.mark.asyncio
    async def test_primeira_mensagem(self):
        """Primeira mensagem para número deve ser permitida."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)
            ok, segundos = await verificar_intervalo_minimo("5511999999999")
            assert ok is True
            assert segundos == 0

    @pytest.mark.asyncio
    async def test_intervalo_muito_curto(self):
        """Deve bloquear se intervalo muito curto."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            # Simula última mensagem há 10 segundos
            agora = datetime.now().timestamp()
            mock_redis.get = AsyncMock(return_value=str(agora - 10))

            with patch('app.services.rate_limiter.datetime') as mock_dt:
                mock_dt.now.return_value.timestamp.return_value = agora

                ok, segundos = await verificar_intervalo_minimo("5511999999999")
                assert ok is False
                assert segundos > 0

    @pytest.mark.asyncio
    async def test_intervalo_suficiente(self):
        """Deve permitir se intervalo suficiente."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            # Simula última mensagem há 60 segundos
            agora = datetime.now().timestamp()
            mock_redis.get = AsyncMock(return_value=str(agora - 60))

            ok, segundos = await verificar_intervalo_minimo("5511999999999")
            assert ok is True
            assert segundos == 0


class TestPodeEnviar:
    """Testes para verificação completa de envio."""

    @pytest.mark.asyncio
    async def test_pode_enviar_normal(self):
        """Deve permitir em condições normais."""
        # Usar datetime real mas criar mock que funciona
        mock_now = datetime(2025, 12, 8, 10, 0)  # Segunda 10h

        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = mock_now

            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)

                ok, motivo = await pode_enviar("5511999999999")
                assert ok is True
                assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_bloqueia_fora_horario(self):
        """Deve bloquear fora do horário comercial."""
        mock_now = datetime(2025, 12, 13, 10, 0)  # Sábado

        with patch('app.services.rate_limiter.datetime') as mock_dt:
            mock_dt.now.return_value = mock_now

            ok, motivo = await pode_enviar("5511999999999")
            assert ok is False
            assert "fim de semana" in motivo.lower()


class TestRegistrarEnvio:
    """Testes para registro de envio."""

    @pytest.mark.asyncio
    async def test_registra_envio(self):
        """Deve registrar envio corretamente."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.incr = AsyncMock()
            mock_redis.expire = AsyncMock()
            mock_redis.set = AsyncMock()

            await registrar_envio("5511999999999")

            # Verifica que os contadores foram incrementados
            assert mock_redis.incr.call_count == 2  # hora e dia
            assert mock_redis.expire.call_count >= 2
            assert mock_redis.set.call_count == 1  # último envio

    @pytest.mark.asyncio
    async def test_erro_redis_nao_quebra(self):
        """Erro no Redis não deve quebrar a aplicação."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

            # Não deve levantar exceção
            await registrar_envio("5511999999999")
