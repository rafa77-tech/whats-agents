"""
Testes unitarios para o servico de rate limiting.

Sprint 21 - E03 - Rate limit para endpoints sensiveis.
Cobre: check_rate_limit, get_rate_limit_status, render_rate_limit_page.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.unit
class TestCheckRateLimitPermitido:
    """Testes para requests dentro do limite permitido."""

    @pytest.mark.asyncio
    async def test_permite_request_dentro_do_limite_por_minuto(self):
        """Request deve ser permitido quando contador esta abaixo do limite por minuto."""
        mock_pipe = AsyncMock()
        # zremrangebyscore (min), zremrangebyscore (hour), zcard (min), zcard (hour)
        mock_pipe.execute.return_value = [0, 0, 5, 10]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("192.168.1.1")

        assert allowed is True
        assert reason == ""
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_permite_request_com_contadores_zerados(self):
        """Primeiro request de um IP deve ser permitido (contadores zerados)."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 0, 0]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("10.0.0.1")

        assert allowed is True
        assert reason == ""
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_permite_request_no_limite_exato_menos_um(self):
        """Request deve ser permitido quando contador esta em limite - 1."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 29, 50]  # 29 < 30 (default)

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("10.0.0.2")

        assert allowed is True

    @pytest.mark.asyncio
    async def test_registra_request_no_redis_apos_permitir(self):
        """Apos permitir, deve adicionar request nas janelas de minuto e hora."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 5, 10]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            await check_rate_limit("10.0.0.3")

        # Segundo pipeline deve ter sido chamado para registrar o request
        assert mock_pipe2.zadd.call_count == 2
        assert mock_pipe2.expire.call_count == 2
        mock_pipe2.execute.assert_awaited_once()


@pytest.mark.unit
class TestCheckRateLimitBloqueado:
    """Testes para requests que excedem o limite."""

    @pytest.mark.asyncio
    async def test_bloqueia_quando_excede_limite_por_minuto(self):
        """Request deve ser bloqueado quando atinge limite por minuto."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 30, 50]  # 30 >= 30 (default)

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("192.168.1.2")

        assert allowed is False
        assert reason == "rate_limit_minute"
        assert retry_after >= 1

    @pytest.mark.asyncio
    async def test_bloqueia_quando_excede_limite_por_hora(self):
        """Request deve ser bloqueado quando atinge limite por hora."""
        mock_pipe = AsyncMock()
        # Minuto OK (10 < 30), hora excedida (200 >= 200)
        mock_pipe.execute.return_value = [0, 0, 10, 200]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("192.168.1.3")

        assert allowed is False
        assert reason == "rate_limit_hour"
        assert retry_after >= 1

    @pytest.mark.asyncio
    async def test_bloqueia_com_limites_customizados(self):
        """Deve respeitar limites customizados passados como parametro."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 5, 10]  # 5 >= 5 (custom)

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit(
                "192.168.1.4",
                limit_per_minute=5,
                limit_per_hour=50,
            )

        assert allowed is False
        assert reason == "rate_limit_minute"

    @pytest.mark.asyncio
    async def test_prioriza_bloqueio_por_minuto_sobre_hora(self):
        """Quando ambos limites excedidos, deve reportar o de minuto primeiro."""
        mock_pipe = AsyncMock()
        # Ambos excedidos
        mock_pipe.execute.return_value = [0, 0, 30, 200]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("192.168.1.5")

        assert allowed is False
        assert reason == "rate_limit_minute"

    @pytest.mark.asyncio
    async def test_retry_after_minimo_eh_1(self):
        """retry_after nunca deve ser menor que 1 segundo."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 30, 50]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("192.168.1.6")

        assert retry_after >= 1


@pytest.mark.unit
class TestCheckRateLimitFallback:
    """Testes para comportamento fail-open quando Redis esta indisponivel."""

    @pytest.mark.asyncio
    async def test_permite_quando_redis_indisponivel(self):
        """Deve permitir request quando Redis lanca excecao (fail-open)."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.side_effect = ConnectionError("Redis unavailable")

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("10.0.0.5")

        assert allowed is True
        assert reason == ""
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_permite_quando_redis_timeout(self):
        """Deve permitir request quando Redis tem timeout."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.side_effect = TimeoutError("Connection timed out")

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            allowed, reason, retry_after = await check_rate_limit("10.0.0.6")

        assert allowed is True
        assert reason == ""
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_loga_erro_quando_redis_falha(self):
        """Deve registrar log de erro quando Redis falha."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.side_effect = ConnectionError("Redis down")

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with (
            patch("app.services.rate_limit.redis_client", mock_redis),
            patch("app.services.rate_limit.logger") as mock_logger,
        ):
            from app.services.rate_limit import check_rate_limit

            await check_rate_limit("10.0.0.7")

        mock_logger.error.assert_called_once()
        assert "Erro no rate limit" in mock_logger.error.call_args[0][0]


@pytest.mark.unit
class TestCheckRateLimitResetJanela:
    """Testes para verificar que janelas de tempo sao limpas corretamente."""

    @pytest.mark.asyncio
    async def test_limpa_entradas_antigas_da_janela_de_minuto(self):
        """Deve chamar zremrangebyscore para limpar entradas com mais de 1 minuto."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 0, 0]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            await check_rate_limit("10.0.0.8")

        # Deve ter chamado zremrangebyscore para ambas as janelas
        assert mock_pipe.zremrangebyscore.call_count == 2

        # Primeiro call: chave de minuto
        minute_call = mock_pipe.zremrangebyscore.call_args_list[0]
        assert "ratelimit:min:10.0.0.8" == minute_call[0][0]

        # Segundo call: chave de hora
        hour_call = mock_pipe.zremrangebyscore.call_args_list[1]
        assert "ratelimit:hour:10.0.0.8" == hour_call[0][0]

    @pytest.mark.asyncio
    async def test_define_ttl_para_chaves_de_janela(self):
        """Deve definir TTL nas chaves para auto-limpeza no Redis."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 0, 0]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            await check_rate_limit("10.0.0.9")

        # TTL de 120s para minuto, 7200s para hora
        expire_calls = mock_pipe2.expire.call_args_list
        assert expire_calls[0][0][1] == 120
        assert expire_calls[1][0][1] == 7200


@pytest.mark.unit
class TestGetRateLimitStatus:
    """Testes para consulta de status do rate limit."""

    @pytest.mark.asyncio
    async def test_retorna_contadores_atuais(self):
        """Deve retornar contadores de requests no ultimo minuto e hora."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [15, 87]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import get_rate_limit_status

            status = await get_rate_limit_status("192.168.1.10")

        assert status == {
            "requests_last_minute": 15,
            "requests_last_hour": 87,
        }

    @pytest.mark.asyncio
    async def test_retorna_zeros_quando_sem_requests(self):
        """Deve retornar zeros para IP sem historico."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import get_rate_limit_status

            status = await get_rate_limit_status("10.0.0.99")

        assert status["requests_last_minute"] == 0
        assert status["requests_last_hour"] == 0

    @pytest.mark.asyncio
    async def test_retorna_zeros_quando_redis_falha(self):
        """Deve retornar zeros quando Redis esta indisponivel."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.side_effect = ConnectionError("Redis down")

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import get_rate_limit_status

            status = await get_rate_limit_status("10.0.0.100")

        assert status == {
            "requests_last_minute": 0,
            "requests_last_hour": 0,
        }

    @pytest.mark.asyncio
    async def test_usa_chaves_corretas_no_redis(self):
        """Deve usar o prefixo e formato correto nas chaves Redis."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0]

        mock_redis = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import get_rate_limit_status

            await get_rate_limit_status("minha_chave")

        zcount_calls = mock_pipe.zcount.call_args_list
        assert zcount_calls[0][0][0] == "ratelimit:min:minha_chave"
        assert zcount_calls[1][0][0] == "ratelimit:hour:minha_chave"


@pytest.mark.unit
class TestRenderRateLimitPage:
    """Testes para renderizacao da pagina HTML de rate limit."""

    def test_retorna_html_valido(self):
        """Deve retornar uma string HTML com estrutura basica."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(120)

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "Revoluna" in html

    def test_exibe_minutos_no_singular(self):
        """Deve exibir 'minuto' (sem s) quando retry_after equivale a 1 minuto."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(60)

        assert "1 minuto." in html

    def test_exibe_minutos_no_plural(self):
        """Deve exibir 'minutos' (com s) quando retry_after maior que 1 minuto."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(180)

        assert "3 minutos" in html

    def test_retry_after_menor_que_60_mostra_1_minuto(self):
        """Deve exibir minimo de 1 minuto mesmo com retry_after < 60."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(30)

        assert "1 minuto" in html

    def test_contem_mensagem_de_aguardar(self):
        """Deve conter mensagem orientando o usuario a aguardar."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(120)

        assert "Um Momento" in html
        assert "muitos acessos" in html

    def test_contem_titulo_revoluna(self):
        """Deve conter titulo da pagina com Revoluna."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(60)

        assert "<title>Aguarde - Revoluna</title>" in html

    def test_retry_after_zero_mostra_1_minuto(self):
        """Deve exibir 1 minuto mesmo com retry_after = 0."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(0)

        assert "1 minuto" in html

    def test_contem_estilos_css(self):
        """Deve conter estilos CSS inline para funcionar standalone."""
        from app.services.rate_limit import render_rate_limit_page

        html = render_rate_limit_page(60)

        assert "<style>" in html
        assert "font-family" in html


@pytest.mark.unit
class TestCheckRateLimitChaves:
    """Testes para verificar formato das chaves no Redis."""

    @pytest.mark.asyncio
    async def test_usa_prefixo_correto_nas_chaves(self):
        """Deve usar prefixo 'ratelimit' nas chaves Redis."""
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [0, 0, 0, 0]

        mock_pipe2 = AsyncMock()
        mock_pipe2.execute.return_value = [True, True, True, True]

        mock_redis = MagicMock()
        mock_redis.pipeline.side_effect = [mock_pipe, mock_pipe2]

        with patch("app.services.rate_limit.redis_client", mock_redis):
            from app.services.rate_limit import check_rate_limit

            await check_rate_limit("meu_ip")

        # Verifica chaves de minuto e hora no zremrangebyscore
        calls = mock_pipe.zremrangebyscore.call_args_list
        assert calls[0][0][0] == "ratelimit:min:meu_ip"
        assert calls[1][0][0] == "ratelimit:hour:meu_ip"

        # Verifica chaves no zadd do segundo pipeline
        zadd_calls = mock_pipe2.zadd.call_args_list
        assert zadd_calls[0][0][0] == "ratelimit:min:meu_ip"
        assert zadd_calls[1][0][0] == "ratelimit:hour:meu_ip"
