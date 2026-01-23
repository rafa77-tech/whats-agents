"""
Testes para utilitários de Modo Piloto.

Sprint 32 E03 - Modo Piloto.
Sprint 35 - Controle granular de features autonomas.
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


def create_mock_settings(pilot_mode: bool, features_enabled: dict[str, bool] | None = None):
    """Helper para criar mock de settings com comportamento correto."""
    mock = MagicMock()
    mock.is_pilot_mode = pilot_mode

    # Default: todas features desabilitadas se pilot_mode=True
    if features_enabled is None:
        if pilot_mode:
            features_enabled = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }
        else:
            features_enabled = {
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            }

    mock.autonomous_features_status = features_enabled

    def is_feature_enabled(feature: str) -> bool:
        return features_enabled.get(feature, False)

    mock.is_feature_enabled = is_feature_enabled
    return mock


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
        """Deve retornar False quando piloto ativo (master switch)."""
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):
            resultado = require_pilot_disabled(AutonomousFeature.DISCOVERY)
            assert resultado is False

    def test_retorna_false_quando_feature_desabilitada(self):
        """Deve retornar False quando feature individual desabilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"oferta_automatica": False},
        )
        with patch("app.workers.pilot_mode.settings", mock):
            resultado = require_pilot_disabled(AutonomousFeature.OFERTA)
            assert resultado is False

    def test_retorna_true_quando_feature_habilitada(self):
        """Deve retornar True quando piloto inativo e feature habilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"oferta_automatica": True},
        )
        with patch("app.workers.pilot_mode.settings", mock):
            resultado = require_pilot_disabled(AutonomousFeature.OFERTA)
            assert resultado is True

    def test_loga_feature_desabilitada(self):
        """Deve logar quando feature está desabilitada."""
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                require_pilot_disabled(AutonomousFeature.REATIVACAO)

                mock_logger.info.assert_called_once()
                call_args = str(mock_logger.info.call_args)
                assert "reativacao_automatica" in call_args


class TestSkipIfPilot:
    """Testes para decorator skip_if_pilot()."""

    @pytest.mark.asyncio
    async def test_pula_funcao_async_quando_piloto_ativo(self):
        """Deve retornar None para função async quando piloto ativo (master switch)."""
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            async def funcao_async():
                return "executado"

            resultado = await funcao_async()
            assert resultado is None

    @pytest.mark.asyncio
    async def test_pula_funcao_async_quando_feature_desabilitada(self):
        """Deve retornar None quando feature individual desabilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"discovery_automatico": False},
        )
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            async def funcao_async():
                return "executado"

            resultado = await funcao_async()
            assert resultado is None

    @pytest.mark.asyncio
    async def test_executa_funcao_async_quando_feature_habilitada(self):
        """Deve executar função async quando feature habilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"discovery_automatico": True},
        )
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.DISCOVERY)
            async def funcao_async():
                return "executado"

            resultado = await funcao_async()
            assert resultado == "executado"

    def test_pula_funcao_sync_quando_piloto_ativo(self):
        """Deve retornar None para função sync quando piloto ativo."""
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.OFERTA)
            def funcao_sync():
                return "executado"

            resultado = funcao_sync()
            assert resultado is None

    def test_executa_funcao_sync_quando_feature_habilitada(self):
        """Deve executar função sync quando feature habilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"oferta_automatica": True},
        )
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.OFERTA)
            def funcao_sync():
                return "executado"

            resultado = funcao_sync()
            assert resultado == "executado"

    @pytest.mark.asyncio
    async def test_preserva_argumentos(self):
        """Deve preservar argumentos da função decorada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={"feedback_automatico": True},
        )
        with patch("app.workers.pilot_mode.settings", mock):

            @skip_if_pilot(AutonomousFeature.FEEDBACK)
            async def funcao_com_args(a, b, c=None):
                return f"{a}-{b}-{c}"

            resultado = await funcao_com_args("x", "y", c="z")
            assert resultado == "x-y-z"

    @pytest.mark.asyncio
    async def test_loga_quando_pula(self):
        """Deve logar quando pula execução."""
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:

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
        mock = create_mock_settings(pilot_mode=True)
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                log_pilot_status()

                mock_logger.warning.assert_called_once()
                call_args = str(mock_logger.warning.call_args)
                assert "PILOTO" in call_args.upper()

    def test_loga_info_quando_todas_features_habilitadas(self):
        """Deve logar info quando todas features habilitadas."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={
                "discovery_automatico": True,
                "oferta_automatica": True,
                "reativacao_automatica": True,
                "feedback_automatico": True,
            },
        )
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                log_pilot_status()

                mock_logger.info.assert_called_once()
                call_args = str(mock_logger.info.call_args)
                assert "habilitadas" in call_args.lower()

    def test_loga_warning_quando_nenhuma_feature_habilitada(self):
        """Deve logar warning quando nenhuma feature habilitada."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={
                "discovery_automatico": False,
                "oferta_automatica": False,
                "reativacao_automatica": False,
                "feedback_automatico": False,
            },
        )
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                log_pilot_status()

                mock_logger.warning.assert_called_once()
                call_args = str(mock_logger.warning.call_args)
                assert "desabilitadas" in call_args.lower()

    def test_loga_info_quando_algumas_features_habilitadas(self):
        """Deve logar info com contagem quando algumas features habilitadas."""
        mock = create_mock_settings(
            pilot_mode=False,
            features_enabled={
                "discovery_automatico": True,
                "oferta_automatica": False,
                "reativacao_automatica": True,
                "feedback_automatico": False,
            },
        )
        with patch("app.workers.pilot_mode.settings", mock):
            with patch("app.workers.pilot_mode.logger") as mock_logger:
                log_pilot_status()

                mock_logger.info.assert_called_once()
                call_args = str(mock_logger.info.call_args)
                assert "2/4" in call_args


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
