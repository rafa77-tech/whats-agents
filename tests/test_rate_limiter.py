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
    obter_estatisticas,
    verificar_limite_cliente,
    registrar_envio_cliente,
    verificar_limite_tipo,
    registrar_envio_tipo,
    calcular_delay_com_jitter,
    calcular_delay_por_tipo,
    pode_enviar_completo,
    registrar_envio_completo,
    RateLimitExceeded,
    TipoMensagem,
    _fallback_verificar_limite_hora,
    _fallback_verificar_limite_dia,
    _fallback_verificar_limite_cliente,
    INTERVALO_MIN_SEGUNDOS,
    INTERVALO_MAX_SEGUNDOS,
    LIMITE_POR_HORA,
    LIMITE_POR_DIA,
    LIMITE_POR_CLIENTE_HORA,
    LIMITES_POR_TIPO,
    HORA_INICIO,
    HORA_FIM,
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


class TestRateLimitExceeded:
    """Testes para a exceção RateLimitExceeded."""

    def test_criacao_com_motivo(self):
        """Deve armazenar motivo e retry_after."""
        exc = RateLimitExceeded("Limite atingido", retry_after=60)
        assert exc.motivo == "Limite atingido"
        assert exc.retry_after == 60
        assert str(exc) == "Limite atingido"

    def test_criacao_sem_retry_after(self):
        """Deve funcionar sem retry_after."""
        exc = RateLimitExceeded("Bloqueado")
        assert exc.motivo == "Bloqueado"
        assert exc.retry_after is None


class TestHorarioBoundaries:
    """Testes para limites exatos de horário (8h e 20h)."""

    @pytest.mark.asyncio
    async def test_exatamente_8h_permitido(self):
        """Exatamente 8h deve ser permitido (hora de início)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 8, 0)  # Segunda 8:00
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is True
            assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_exatamente_20h_bloqueado(self):
        """Exatamente 20h deve ser bloqueado (hora >= HORA_FIM)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 20, 0)  # Segunda 20:00
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "após" in motivo.lower()

    @pytest.mark.asyncio
    async def test_19h59_permitido(self):
        """19:59 deve ser permitido (último minuto antes do limite)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 19, 59)  # Segunda 19:59
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is True
            assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_7h59_bloqueado(self):
        """7:59 deve ser bloqueado (antes da hora de início)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 7, 59)  # Segunda 7:59
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is False
            assert "antes" in motivo.lower()

    @pytest.mark.asyncio
    async def test_sexta_feira_permitido(self):
        """Sexta-feira em horário comercial deve ser permitido."""
        mock_time = criar_mock_datetime(2025, 12, 12, 14, 0)  # Sexta 14:00
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await verificar_horario_permitido()
            assert ok is True
            assert motivo == "OK"


class TestLimiteDiaFallback:
    """Testes para fallback do limite diário quando Redis falha."""

    @pytest.mark.asyncio
    async def test_erro_redis_usa_fallback_dia(self):
        """Em caso de erro no Redis, deve tentar fallback Supabase para dia."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                with patch('app.services.rate_limiter._fallback_verificar_limite_dia',
                          new_callable=AsyncMock, return_value=(True, 30)):
                    ok, count = await verificar_limite_dia()
                    assert ok is True
                    assert count == 30

    @pytest.mark.asyncio
    async def test_erro_redis_e_fallback_dia_bloqueia(self):
        """Sprint 44: FAIL-CLOSED quando Redis e fallback dia falham."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                with patch('app.services.rate_limiter._fallback_verificar_limite_dia',
                          new_callable=AsyncMock, side_effect=Exception("Supabase error")):
                    ok, count = await verificar_limite_dia()
                    assert ok is False
                    assert count == 0


class TestIntervaloMinimoFallback:
    """Testes para fail-closed do intervalo mínimo."""

    @pytest.mark.asyncio
    async def test_erro_redis_fail_closed(self):
        """Sprint 44: FAIL-CLOSED quando Redis falha ao verificar intervalo."""
        with patch('app.services.rate_limiter.redis_client') as mock_redis:
            mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
            ok, segundos = await verificar_intervalo_minimo("5511999999999")
            # Deve bloquear com intervalo mínimo
            assert ok is False
            assert segundos == INTERVALO_MIN_SEGUNDOS


class TestPodeEnviarCompleto:
    """Testes para pode_enviar com mensagens de bloqueio específicas."""

    @pytest.mark.asyncio
    async def test_bloqueia_limite_hora(self):
        """Deve retornar mensagem específica quando limite hora atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                # Horário OK (retorna None para horário), limite hora atingido
                async def mock_get(chave):
                    if "hora" in chave:
                        return str(LIMITE_POR_HORA)
                    if "dia" in chave:
                        return "5"
                    return None

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar("5511999999999")
                assert ok is False
                assert "limite por hora" in motivo.lower()

    @pytest.mark.asyncio
    async def test_bloqueia_limite_dia(self):
        """Deve retornar mensagem específica quando limite dia atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "hora" in chave:
                        return "5"  # Dentro do limite hora
                    if "dia" in chave:
                        return str(LIMITE_POR_DIA)  # Limite dia atingido
                    return None

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar("5511999999999")
                assert ok is False
                assert "limite por dia" in motivo.lower()

    @pytest.mark.asyncio
    async def test_bloqueia_intervalo_minimo(self):
        """Deve retornar mensagem específica quando intervalo mínimo não respeitado."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        agora_ts = mock_time.timestamp()

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "hora" in chave:
                        return "5"
                    if "dia" in chave:
                        return "5"
                    if "ultimo" in chave:
                        return str(agora_ts - 5)  # Apenas 5 segundos atrás
                    return None

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar("5511999999999")
                assert ok is False
                assert "aguardar" in motivo.lower()


class TestObterEstatisticas:
    """Testes para obtenção de estatísticas."""

    @pytest.mark.asyncio
    async def test_estatisticas_normais(self):
        """Deve retornar estatísticas corretamente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=["15", "80"])
                stats = await obter_estatisticas()

                assert stats["msgs_hora"] == 15
                assert stats["msgs_dia"] == 80
                assert stats["limite_hora"] == LIMITE_POR_HORA
                assert stats["limite_dia"] == LIMITE_POR_DIA
                assert stats["horario_permitido"] is True
                assert "hora_atual" in stats
                assert "dia_semana" in stats

    @pytest.mark.asyncio
    async def test_estatisticas_sem_dados(self):
        """Deve retornar zeros quando não há dados no Redis."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)
                stats = await obter_estatisticas()

                assert stats["msgs_hora"] == 0
                assert stats["msgs_dia"] == 0

    @pytest.mark.asyncio
    async def test_estatisticas_erro_redis(self):
        """Deve retornar dict vazio em caso de erro."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                stats = await obter_estatisticas()
                assert stats == {}


class TestVerificarLimiteCliente:
    """Testes para verificação de limite por cliente (Sprint 36 T04.1)."""

    @pytest.mark.asyncio
    async def test_dentro_limite_cliente(self):
        """Deve permitir quando cliente está dentro do limite."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value="1")
                ok, count = await verificar_limite_cliente("cliente-123")
                assert ok is True
                assert count == 1

    @pytest.mark.asyncio
    async def test_limite_cliente_atingido(self):
        """Deve bloquear quando limite por cliente atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=str(LIMITE_POR_CLIENTE_HORA))
                ok, count = await verificar_limite_cliente("cliente-123")
                assert ok is False
                assert count == LIMITE_POR_CLIENTE_HORA

    @pytest.mark.asyncio
    async def test_erro_redis_usa_fallback_cliente(self):
        """Deve usar fallback Supabase quando Redis falha para cliente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                with patch('app.services.rate_limiter._fallback_verificar_limite_cliente',
                          new_callable=AsyncMock, return_value=(True, 1)):
                    ok, count = await verificar_limite_cliente("cliente-123")
                    assert ok is True
                    assert count == 1

    @pytest.mark.asyncio
    async def test_cliente_sem_dados(self):
        """Deve permitir quando não há dados para o cliente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)
                ok, count = await verificar_limite_cliente("cliente-novo")
                assert ok is True
                assert count == 0


class TestRegistrarEnvioCliente:
    """Testes para registro de envio por cliente (Sprint 36 T04.1)."""

    @pytest.mark.asyncio
    async def test_registra_envio_cliente(self):
        """Deve registrar envio por cliente corretamente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock()
                mock_redis.expire = AsyncMock()

                await registrar_envio_cliente("cliente-123")
                mock_redis.incr.assert_called_once()
                mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_erro_redis_nao_quebra_cliente(self):
        """Erro no Redis não deve quebrar ao registrar envio por cliente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))
                # Não deve levantar exceção
                await registrar_envio_cliente("cliente-123")


class TestVerificarLimiteTipo:
    """Testes para verificação de limite por tipo de mensagem (Sprint 36 T04.2)."""

    @pytest.mark.asyncio
    async def test_dentro_limite_prospeccao(self):
        """Deve permitir prospecção dentro do limite."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value="5")
                ok, count, limite = await verificar_limite_tipo(TipoMensagem.PROSPECCAO)
                assert ok is True
                assert count == 5
                assert limite == LIMITES_POR_TIPO[TipoMensagem.PROSPECCAO]

    @pytest.mark.asyncio
    async def test_limite_tipo_atingido(self):
        """Deve bloquear quando limite por tipo atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        tipo = TipoMensagem.PROSPECCAO
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=str(LIMITES_POR_TIPO[tipo]))
                ok, count, limite = await verificar_limite_tipo(tipo)
                assert ok is False
                assert count == LIMITES_POR_TIPO[tipo]

    @pytest.mark.asyncio
    async def test_erro_redis_permite_tipo(self):
        """Erro no Redis deve permitir (fail-open para tipos)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(side_effect=Exception("Redis error"))
                ok, count, limite = await verificar_limite_tipo(TipoMensagem.RESPOSTA)
                assert ok is True
                assert count == 0

    @pytest.mark.asyncio
    async def test_tipo_sem_dados(self):
        """Deve permitir quando não há dados para o tipo."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)
                ok, count, limite = await verificar_limite_tipo(TipoMensagem.CAMPANHA)
                assert ok is True
                assert count == 0
                assert limite == LIMITES_POR_TIPO[TipoMensagem.CAMPANHA]


class TestRegistrarEnvioTipo:
    """Testes para registro de envio por tipo (Sprint 36 T04.2)."""

    @pytest.mark.asyncio
    async def test_registra_envio_tipo(self):
        """Deve registrar envio por tipo corretamente."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock()
                mock_redis.expire = AsyncMock()

                await registrar_envio_tipo(TipoMensagem.FOLLOWUP)
                mock_redis.incr.assert_called_once()
                mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_erro_redis_nao_quebra_tipo(self):
        """Erro no Redis não deve quebrar ao registrar envio por tipo."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))
                await registrar_envio_tipo(TipoMensagem.PROSPECCAO)


class TestCalcularDelayComJitter:
    """Testes para cálculo de delay com jitter (Sprint 36 T04.3)."""

    def test_delay_respeita_minimo(self):
        """Delay com jitter nunca deve ser menor que base_min."""
        for _ in range(200):
            delay = calcular_delay_com_jitter(base_min=45, base_max=180)
            assert delay >= 45

    def test_delay_com_parametros_custom(self):
        """Deve usar parâmetros customizados."""
        for _ in range(100):
            delay = calcular_delay_com_jitter(base_min=10, base_max=20, jitter_pct=0.1)
            assert delay >= 10

    def test_delay_com_jitter_zero(self):
        """Jitter zero deve retornar exatamente o valor base."""
        # Sem random extra (mockando o random para evitar o 10% distraction)
        with patch('app.services.rate_limiter.random') as mock_random:
            mock_random.randint = MagicMock(side_effect=[50, 0])  # base=50, jitter=0
            mock_random.random = MagicMock(return_value=0.5)  # > 0.1, sem extra
            delay = calcular_delay_com_jitter(base_min=30, base_max=60, jitter_pct=0.2)
            assert delay == 50

    def test_delay_com_distracao_extra(self):
        """10% das vezes deve adicionar delay extra de 30-90s (parecer distraída)."""
        with patch('app.services.rate_limiter.random') as mock_random:
            mock_random.randint = MagicMock(side_effect=[50, 0, 60])  # base=50, jitter=0, extra=60
            mock_random.random = MagicMock(return_value=0.05)  # < 0.1, ativa distração
            delay = calcular_delay_com_jitter(base_min=30, base_max=60, jitter_pct=0.2)
            assert delay == 110  # 50 + 0 + 60

    def test_delay_usa_defaults_config(self):
        """Sem parâmetros deve usar valores da config."""
        for _ in range(50):
            delay = calcular_delay_com_jitter()
            assert delay >= INTERVALO_MIN_SEGUNDOS


class TestCalcularDelayPorTipo:
    """Testes para cálculo de delay por tipo de mensagem (Sprint 36 T04.3)."""

    def test_delay_prospeccao_maior(self):
        """Prospecção deve ter delays maiores (60-180 base)."""
        delays = [calcular_delay_por_tipo(TipoMensagem.PROSPECCAO) for _ in range(50)]
        assert min(delays) >= 60  # base_min para prospecção

    def test_delay_followup_medio(self):
        """Follow-up deve ter delays médios (45-120 base)."""
        delays = [calcular_delay_por_tipo(TipoMensagem.FOLLOWUP) for _ in range(50)]
        assert min(delays) >= 45

    def test_delay_resposta_curto(self):
        """Resposta deve ter delays curtos (30-90 base)."""
        delays = [calcular_delay_por_tipo(TipoMensagem.RESPOSTA) for _ in range(50)]
        assert min(delays) >= 30

    def test_delay_campanha(self):
        """Campanha deve ter delays configuráveis (45-150 base)."""
        delays = [calcular_delay_por_tipo(TipoMensagem.CAMPANHA) for _ in range(50)]
        assert min(delays) >= 45

    def test_delay_sistema_minimo(self):
        """Sistema deve ter delays mínimos (5-15 base)."""
        delays = [calcular_delay_por_tipo(TipoMensagem.SISTEMA) for _ in range(50)]
        assert min(delays) >= 5


class TestFallbackSupabaseHora:
    """Testes para fallback Supabase do limite por hora."""

    @pytest.mark.asyncio
    async def test_fallback_hora_sucesso(self):
        """Deve contar mensagens no Supabase quando Redis cai."""
        mock_result = MagicMock()
        mock_result.count = 10

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_hora()
                assert ok is True
                assert count == 10

    @pytest.mark.asyncio
    async def test_fallback_hora_limite_atingido(self):
        """Deve bloquear quando contagem Supabase excede limite."""
        mock_result = MagicMock()
        mock_result.count = LIMITE_POR_HORA + 10

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_hora()
                assert ok is False
                assert count == LIMITE_POR_HORA + 10

    @pytest.mark.asyncio
    async def test_fallback_hora_count_none(self):
        """Deve tratar count None como 0."""
        mock_result = MagicMock()
        mock_result.count = None

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_hora()
                assert ok is True
                assert count == 0

    @pytest.mark.asyncio
    async def test_fallback_hora_erro_supabase(self):
        """Deve retornar True quando Supabase também falha (fail-open no fallback hora)."""
        with patch.dict('sys.modules', {'app.services.supabase': MagicMock(side_effect=Exception("DB error"))}):
            with patch('builtins.__import__', side_effect=Exception("Import error")):
                # O fallback hora retorna True, 0 quando falha internamente
                ok, count = await _fallback_verificar_limite_hora()
                assert ok is True
                assert count == 0


class TestFallbackSupabaseDia:
    """Testes para fallback Supabase do limite por dia."""

    @pytest.mark.asyncio
    async def test_fallback_dia_sucesso(self):
        """Deve contar mensagens do dia no Supabase."""
        mock_result = MagicMock()
        mock_result.count = 50

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_dia()
                assert ok is True
                assert count == 50

    @pytest.mark.asyncio
    async def test_fallback_dia_limite_atingido(self):
        """Deve bloquear quando contagem diária excede limite."""
        mock_result = MagicMock()
        mock_result.count = LIMITE_POR_DIA + 5

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.in_.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_dia()
                assert ok is False

    @pytest.mark.asyncio
    async def test_fallback_dia_erro_supabase(self):
        """Deve retornar True quando Supabase falha (fail-open no fallback dia)."""
        with patch.dict('sys.modules', {'app.services.supabase': MagicMock(side_effect=Exception("DB error"))}):
            with patch('builtins.__import__', side_effect=Exception("Import error")):
                ok, count = await _fallback_verificar_limite_dia()
                assert ok is True
                assert count == 0


class TestFallbackSupabaseCliente:
    """Testes para fallback Supabase do limite por cliente."""

    @pytest.mark.asyncio
    async def test_fallback_cliente_sucesso(self):
        """Deve contar mensagens do cliente no Supabase."""
        mock_result = MagicMock()
        mock_result.count = 1

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_cliente("cliente-123")
                assert ok is True
                assert count == 1

    @pytest.mark.asyncio
    async def test_fallback_cliente_limite_atingido(self):
        """Deve bloquear quando contagem por cliente excede limite."""
        mock_result = MagicMock()
        mock_result.count = LIMITE_POR_CLIENTE_HORA + 1

        mock_table = MagicMock()
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.gte.return_value = mock_table
        mock_table.execute.return_value = mock_result

        mock_supabase = MagicMock()
        mock_supabase.table.return_value = mock_table

        with patch('app.services.rate_limiter.supabase', mock_supabase, create=True):
            with patch.dict('sys.modules', {'app.services.supabase': MagicMock(supabase=mock_supabase)}):
                ok, count = await _fallback_verificar_limite_cliente("cliente-123")
                assert ok is False

    @pytest.mark.asyncio
    async def test_fallback_cliente_erro_fail_closed(self):
        """Sprint 44: FAIL-CLOSED quando Supabase falha para cliente."""
        with patch.dict('sys.modules', {'app.services.supabase': MagicMock(side_effect=Exception("DB error"))}):
            with patch('builtins.__import__', side_effect=Exception("Import error")):
                ok, count = await _fallback_verificar_limite_cliente("cliente-123")
                assert ok is False
                assert count == 0


class TestPodeEnviarCompletoOrchestration:
    """Testes para pode_enviar_completo (Sprint 36 orquestração)."""

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_tudo_ok(self):
        """Deve permitir quando todas as verificações passam."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)

                ok, motivo = await pode_enviar_completo(
                    "5511999999999", cliente_id="cliente-123", tipo=TipoMensagem.RESPOSTA
                )
                assert ok is True
                assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_sem_cliente(self):
        """Deve funcionar sem cliente_id (pula verificação por cliente)."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.get = AsyncMock(return_value=None)

                ok, motivo = await pode_enviar_completo("5511999999999")
                assert ok is True
                assert motivo == "OK"

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_horario(self):
        """Deve bloquear fora do horário comercial."""
        mock_time = criar_mock_datetime(2025, 12, 13, 10)  # Sábado
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            ok, motivo = await pode_enviar_completo("5511999999999")
            assert ok is False
            assert "fim de semana" in motivo.lower()

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_limite_hora(self):
        """Deve bloquear quando limite hora atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "hora" in chave and "cliente" not in chave and "tipo" not in chave:
                        return str(LIMITE_POR_HORA)
                    return None

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar_completo("5511999999999")
                assert ok is False
                assert "limite por hora" in motivo.lower()

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_limite_dia(self):
        """Deve bloquear quando limite dia atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "dia" in chave:
                        return str(LIMITE_POR_DIA)
                    return "0"

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar_completo("5511999999999")
                assert ok is False
                assert "limite por dia" in motivo.lower()

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_limite_cliente(self):
        """Deve bloquear quando limite por cliente atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "cliente" in chave:
                        return str(LIMITE_POR_CLIENTE_HORA)
                    return "0"

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar_completo(
                    "5511999999999", cliente_id="cliente-123"
                )
                assert ok is False
                assert "limite por cliente" in motivo.lower()

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_limite_tipo(self):
        """Deve bloquear quando limite por tipo atingido."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        tipo = TipoMensagem.PROSPECCAO
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "tipo" in chave:
                        return str(LIMITES_POR_TIPO[tipo])
                    return "0"

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar_completo(
                    "5511999999999", tipo=tipo
                )
                assert ok is False
                assert "prospeccao" in motivo.lower()

    @pytest.mark.asyncio
    async def test_pode_enviar_completo_bloqueia_intervalo(self):
        """Deve bloquear quando intervalo mínimo não respeitado."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        agora_ts = mock_time.timestamp()

        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                async def mock_get(chave):
                    if "ultimo" in chave:
                        return str(agora_ts - 5)  # 5 segundos atrás
                    return "0"

                mock_redis.get = AsyncMock(side_effect=mock_get)
                ok, motivo = await pode_enviar_completo("5511999999999")
                assert ok is False
                assert "aguardar" in motivo.lower()


class TestRegistrarEnvioCompleto:
    """Testes para registrar_envio_completo (Sprint 36)."""

    @pytest.mark.asyncio
    async def test_registra_completo_com_cliente_e_tipo(self):
        """Deve registrar envio global, por cliente e por tipo."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock()
                mock_redis.expire = AsyncMock()
                mock_redis.set = AsyncMock()

                await registrar_envio_completo(
                    "5511999999999",
                    cliente_id="cliente-123",
                    tipo=TipoMensagem.PROSPECCAO
                )
                # Global: 2 incr (hora+dia) + cliente: 1 incr + tipo: 1 incr = 4
                assert mock_redis.incr.call_count == 4

    @pytest.mark.asyncio
    async def test_registra_completo_sem_cliente(self):
        """Deve registrar apenas global e tipo quando sem cliente_id."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock()
                mock_redis.expire = AsyncMock()
                mock_redis.set = AsyncMock()

                await registrar_envio_completo("5511999999999")
                # Global: 2 incr (hora+dia) + tipo: 1 incr = 3
                assert mock_redis.incr.call_count == 3

    @pytest.mark.asyncio
    async def test_registra_completo_tipo_default_resposta(self):
        """Tipo default deve ser RESPOSTA."""
        mock_time = criar_mock_datetime(2025, 12, 8, 10)
        with patch('app.services.rate_limiter.agora_brasilia', return_value=mock_time):
            with patch('app.services.rate_limiter.redis_client') as mock_redis:
                mock_redis.incr = AsyncMock()
                mock_redis.expire = AsyncMock()
                mock_redis.set = AsyncMock()

                await registrar_envio_completo("5511999999999")
                # Verifica que a chave de tipo contém "resposta"
                incr_calls = [str(c) for c in mock_redis.incr.call_args_list]
                assert any("resposta" in c for c in incr_calls)
