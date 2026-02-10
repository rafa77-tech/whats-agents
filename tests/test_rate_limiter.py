"""
Testes para o serviço de rate limiting.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone

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


def criar_mock_datetime(year, month, day, hour, minute=0):
    """Cria mock datetime com timezone de Brasília."""
    from zoneinfo import ZoneInfo
    tz_brasilia = ZoneInfo("America/Sao_Paulo")
    return datetime(year, month, day, hour, minute, tzinfo=tz_brasilia)


class TestHorarioPermitido:
    """Testes para verificação de horário comercial."""

    @pytest.mark.asyncio
    async def test_horario_comercial_segunda_10h(self):
        """Segunda às 10h deve ser permitido."""
        # Mock agora_brasilia para segunda às 10h
        mock_time = criar_mock_datetime(2025, 12, 8, 10)  # Segunda
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is True
            assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_fora_horario_sabado(self):
        """Sábado deve ser bloqueado."""
        mock_time = criar_mock_datetime(2025, 12, 13, 10)  # Sábado
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "fim de semana" in motivo.lower()

    @pytest.mark.asyncio
    async def test_fora_horario_domingo(self):
        """Domingo deve ser bloqueado."""
        mock_time = criar_mock_datetime(2025, 12, 14, 10)  # Domingo
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "fim de semana" in motivo.lower()

    @pytest.mark.asyncio
    async def test_antes_horario_comercial(self):
        """Antes das 8h deve ser bloqueado."""
        mock_time = criar_mock_datetime(2025, 12, 8, 7, 30)  # Segunda 7:30
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "antes" in motivo.lower()

    @pytest.mark.asyncio
    async def test_apos_horario_comercial(self):
        """Após às 20h deve ser bloqueado."""
        mock_time = criar_mock_datetime(2025, 12, 8, 20, 30)  # Segunda 20:30
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
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
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value="5")
                ok, count = await verificar_limite_hora()
                assert ok is True
                assert count == 5

    @pytest.mark.asyncio
    async def test_limite_atingido(self):
        """Deve bloquear quando limite atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=str(LIMITE_POR_HORA))
                ok, count = await verificar_limite_hora()
                assert ok is False
                assert count == LIMITE_POR_HORA

    @pytest.mark.asyncio
    async def test_erro_redis_usa_fallback(self):
        """Em caso de erro no Redis, deve tentar fallback Supabase."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                # Mock Supabase fallback para retornar sucesso
                with patch('app.services.rate_limiter._fallback_verificar_limite_hora',
                          new_callable=AsyncMock, return_value=(True, 5)):
                    ok, count = await verificar_limite_hora()
                    assert ok is True
                    assert count == 5

    @pytest.mark.asyncio
    async def test_erro_redis_e_fallback_bloqueia(self):
        """Sprint 44: FAIL-CLOSED quando Redis e fallback falham."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                # Mock Supabase fallback para também falhar
                with patch('app.services.rate_limiter._fallback_verificar_limite_hora',
                          new_callable=AsyncMock, side_effect=Exception("Supabase error")):
                    ok, count = await verificar_limite_hora()
                    # Sprint 44 T01.2: FAIL-CLOSED - bloqueia
                    assert ok is False
                    assert count == 0


class TestLimiteDia:
    """Testes para verificação de limite por dia."""

    @pytest.mark.asyncio
    async def test_dentro_limite(self):
        """Deve permitir quando dentro do limite."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value="50")
                ok, count = await verificar_limite_dia()
                assert ok is True
                assert count == 50

    @pytest.mark.asyncio
    async def test_limite_atingido(self):
        """Deve bloquear quando limite diário atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
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
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        agora_ts = mock_time.timestamp()

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                # Simula última mensagem há 10 segundos
                mock_redis.get = AsyncMock(return_value=str(agora_ts - 10))

                ok, segundos = await verificar_intervalo_minimo("5511999999999")
                assert ok is False
                assert segundos > 0

    @pytest.mark.asyncio
    async def test_intervalo_suficiente(self):
        """Deve permitir se intervalo suficiente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        agora_ts = mock_time.timestamp()

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                # Simula última mensagem há 60 segundos
                mock_redis.get = AsyncMock(return_value=str(agora_ts - 60))

                ok, segundos = await verificar_intervalo_minimo("5511999999999")
                assert ok is True
                assert segundos == 0


class TestPodeEnviar:
    """Testes para verificação completa de envio."""

    @pytest.mark.asyncio
    async def test_pode_enviar_normal(self):
        """Deve permitir em condições normais."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)  # Segunda 10h

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)

                ok, motivo = await pode_enviar("5511999999999")
                assert ok is True
                assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_bloqueia_fora_horario(self):
        """Deve bloquear fora do horário comercial."""
        mock_time = criar_mock_datetime(2025, 12, 13, 10)  # Sábado

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await pode_enviar("5511999999999")
            assert ok is False
            assert "fim de semana" in motivo.lower()


class TestRegistrarEnvio:
    """Testes para registro de envio."""

    @pytest.mark.asyncio
    async def test_registra_envio(self):
        """Deve registrar envio corretamente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
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
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

                # Não deve levantar exceção
                await registrar_envio("5511999999999")
