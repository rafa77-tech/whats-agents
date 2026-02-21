"""
Testes para MetaOtpConfirmation.

Sprint 69 — Epic 69.1, Chunk 14.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMetaOtpConfirmation:

    @pytest.mark.asyncio
    async def test_enviar_confirmacao_plantao_sucesso(self):
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with (
            patch("app.services.redis.redis_client", mock_redis),
            patch("app.services.meta.otp_confirmation.settings") as mock_settings,
        ):
            mock_settings.is_production = False
            from app.services.meta.otp_confirmation import MetaOtpConfirmation

            service = MetaOtpConfirmation()
            result = await service.enviar_confirmacao_plantao("5511999", "plantao_1")
            assert result["success"] is True
            assert result["telefone"] == "5511999"
            assert "codigo" in result  # Dev mode includes code

    @pytest.mark.asyncio
    async def test_verificar_codigo_valido(self):
        mock_redis = AsyncMock()
        # First get: failures key (None = no previous failures)
        # Second get: OTP key
        mock_redis.get = AsyncMock(side_effect=[None, "123456:plantao_1"])
        mock_redis.delete = AsyncMock()

        with patch("app.services.redis.redis_client", mock_redis):
            from app.services.meta.otp_confirmation import MetaOtpConfirmation

            service = MetaOtpConfirmation()
            result = await service.verificar_codigo_otp("5511999", "123456")
            assert result["valido"] is True
            assert result["plantao_id"] == "plantao_1"

    @pytest.mark.asyncio
    async def test_verificar_codigo_invalido(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=[None, "123456:plantao_1"])
        mock_redis.incr = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.services.redis.redis_client", mock_redis):
            from app.services.meta.otp_confirmation import MetaOtpConfirmation

            service = MetaOtpConfirmation()
            result = await service.verificar_codigo_otp("5511999", "999999")
            assert result["valido"] is False
            assert "incorreto" in result["motivo"].lower()
            mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_verificar_codigo_expirado(self):
        mock_redis = AsyncMock()
        # First get: failures (None), second get: OTP (None = expired)
        mock_redis.get = AsyncMock(side_effect=[None, None])

        with patch("app.services.redis.redis_client", mock_redis):
            from app.services.meta.otp_confirmation import MetaOtpConfirmation

            service = MetaOtpConfirmation()
            result = await service.verificar_codigo_otp("5511999", "123456")
            assert result["valido"] is False
            assert "expirado" in result["motivo"].lower()

    @pytest.mark.asyncio
    async def test_verificar_codigo_lockout(self):
        mock_redis = AsyncMock()
        # First get: failures key returns 5 (at max)
        mock_redis.get = AsyncMock(return_value="5")

        with patch("app.services.redis.redis_client", mock_redis):
            from app.services.meta.otp_confirmation import MetaOtpConfirmation

            service = MetaOtpConfirmation()
            result = await service.verificar_codigo_otp("5511999", "123456")
            assert result["valido"] is False
            assert "muitas tentativas" in result["motivo"].lower()

    def test_gerar_codigo_6_digitos(self):
        from app.services.meta.otp_confirmation import MetaOtpConfirmation

        service = MetaOtpConfirmation()
        codigo = service._gerar_codigo()
        assert len(codigo) == 6
        assert codigo.isdigit()

    def test_redis_key_format(self):
        from app.services.meta.otp_confirmation import MetaOtpConfirmation

        service = MetaOtpConfirmation()
        key = service._redis_key("5511999")
        assert key == "meta:otp:5511999"
