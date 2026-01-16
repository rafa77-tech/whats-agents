"""
Testes para utilitários de Modo Piloto.

Sprint 32 E03 - Modo Piloto.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.workers.pilot_mode import (
    AutonomousFeature,
    is_pilot_mode,
    require_pilot_disabled,
    skip_if_pilot,
    get_pilot_status,
    log_pilot_status,
)


class TestAutonomousFeature:
    """Testes para enum AutonomousFeature."""

    def test_quatro_features_definidas(self):
        """Deve ter 4 tipos de funcionalidades autônomas."""
        features = list(AutonomousFeature)
        assert len(features) == 4

    def test_valores_esperados(self):
        """Deve ter os valores esperados."""
        assert AutonomousFeature.DISCOVERY.value == "discovery_automatico"
        assert AutonomousFeature.OFERTA.value == "oferta_automatica"
        assert AutonomousFeature.REATIVACAO.value == "reativacao_automatica"
        assert AutonomousFeature.FEEDBACK.value == "feedback_automatico"


class TestIsPilotMode:
    """Testes para is_pilot_mode()."""

    def test_retorna_true_quando_piloto_ativo(self):
        """Deve retornar True quando PILOT_MODE=True."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            resultado = is_pilot_mode()

            assert resultado is True

    def test_retorna_false_quando_piloto_inativo(self):
        """Deve retornar False quando PILOT_MODE=False."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            resultado = is_pilot_mode()

            assert resultado is False


class TestRequirePilotDisabled:
    """Testes para require_pilot_disabled()."""

    def test_retorna_false_quando_piloto_ativo(self):
        """Deve retornar False e logar quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            resultado = require_pilot_disabled(AutonomousFeature.DISCOVERY)

            assert resultado is False

    def test_retorna_true_quando_piloto_inativo(self):
        """Deve retornar True quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            resultado = require_pilot_disabled(AutonomousFeature.OFERTA)

            assert resultado is True

    def test_loga_feature_desabilitada(self):
        """Deve logar quando feature está desabilitada."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                mock_settings.is_pilot_mode = True

                require_pilot_disabled(AutonomousFeature.REATIVACAO)

                mock_logger.info.assert_called_once()
                call_args = str(mock_logger.info.call_args)
                assert "reativacao_automatica" in call_args


class TestSkipIfPilot:
    """Testes para decorator skip_if_pilot()."""

    @pytest.mark.asyncio
    async def test_pula_funcao_async_quando_piloto_ativo(self):
        """Deve retornar None para função async quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            async def funcao_async():
                return "executado"

            resultado = await funcao_async()

            assert resultado is None

    @pytest.mark.asyncio
    async def test_executa_funcao_async_quando_piloto_inativo(self):
        """Deve executar função async quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            async def funcao_async():
                return "executado"

            resultado = await funcao_async()

            assert resultado == "executado"

    def test_pula_funcao_sync_quando_piloto_ativo(self):
        """Deve retornar None para função sync quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            @skip_if_pilot(AutonomousFeature.OFERTA)
            def funcao_sync():
                return "executado"

            resultado = funcao_sync()

            assert resultado is None

    def test_executa_funcao_sync_quando_piloto_inativo(self):
        """Deve executar função sync quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            @skip_if_pilot(AutonomousFeature.OFERTA)
            def funcao_sync():
                return "executado"

            resultado = funcao_sync()

            assert resultado == "executado"

    @pytest.mark.asyncio
    async def test_preserva_argumentos(self):
        """Deve preservar argumentos da função decorada."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            @skip_if_pilot(AutonomousFeature.FEEDBACK)
            async def funcao_com_args(a, b, c=None):
                return f"{a}-{b}-{c}"

            resultado = await funcao_com_args("x", "y", c="z")

            assert resultado == "x-y-z"

    @pytest.mark.asyncio
    async def test_loga_quando_pula(self):
        """Deve logar quando pula execução."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                mock_settings.is_pilot_mode = True

                @skip_if_pilot(AutonomousFeature.DISCOVERY)
                async def minha_funcao():
                    return "executado"

                await minha_funcao()

                mock_logger.info.assert_called()
                call_args = str(mock_logger.info.call_args)
                assert "minha_funcao" in call_args


class TestGetPilotStatus:
    """Testes para get_pilot_status()."""

    def test_retorna_status_quando_ativo(self):
        """Deve retornar status correto quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

            status = get_pilot_status()

            assert status["pilot_mode"] is True
            assert "desabilitadas" in status["message"]
            assert status["features"]["discovery_automatico"] is False

    def test_retorna_status_quando_inativo(self):
        """Deve retornar status correto quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False
            mock_settings.autonomous_features_status = {
                "discovery_automatico": True,
                "oferta_automatica": True,
                "reativacao_automatica": True,
                "feedback_automatico": True,
            }

            status = get_pilot_status()

            assert status["pilot_mode"] is False
            assert "habilitadas" in status["message"]
            assert status["features"]["discovery_automatico"] is True


class TestLogPilotStatus:
    """Testes para log_pilot_status()."""

    def test_loga_warning_quando_ativo(self):
        """Deve logar warning quando piloto ativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                mock_settings.is_pilot_mode = True
                mock_settings.autonomous_features_status = {}

                log_pilot_status()

                mock_logger.warning.assert_called_once()
                call_args = str(mock_logger.warning.call_args)
                assert "PILOTO" in call_args.upper()

    def test_loga_info_quando_inativo(self):
        """Deve logar info quando piloto inativo."""
        with patch("app.workers.pilot_mode.settings") as mock_settings:
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                mock_settings.is_pilot_mode = False
                mock_settings.autonomous_features_status = {}

                log_pilot_status()

                mock_logger.info.assert_called_once()
                call_args = str(mock_logger.info.call_args)
                assert "INATIVO" in call_args.upper()


class TestHealthEndpointPilot:
    """Testes para endpoint /health/pilot."""

    @pytest.mark.asyncio
    async def test_endpoint_retorna_status(self):
        """Endpoint deve retornar status do piloto."""
        from app.api.routes.health import pilot_mode_status

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True
            mock_settings.autonomous_features_status = {
                "discovery_automatico": False,
            }

            resultado = await pilot_mode_status()

            assert "pilot_mode" in resultado
            assert "features" in resultado
            assert "timestamp" in resultado
            assert resultado["pilot_mode"] is True
