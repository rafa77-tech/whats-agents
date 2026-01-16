"""
Testes E2E: Modo piloto bloqueia ações autônomas.

Sprint 32 - Cenário: PILOT_MODE = True
Comportamento esperado: Ações autônomas não executam.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestModoPilotoConfig:
    """Testes da configuração de modo piloto."""

    def test_pilot_mode_existe_em_settings(self):
        """PILOT_MODE deve existir em settings."""
        from app.core.config import settings
        assert hasattr(settings, "PILOT_MODE")

    def test_pilot_mode_e_booleano(self):
        """PILOT_MODE deve ser booleano."""
        from app.core.config import settings
        assert isinstance(settings.PILOT_MODE, bool)

    def test_is_pilot_mode_existe(self):
        """Propriedade is_pilot_mode deve existir."""
        from app.core.config import settings
        assert hasattr(settings, "is_pilot_mode")

    def test_is_pilot_mode_retorna_bool(self):
        """is_pilot_mode deve retornar booleano."""
        from app.core.config import settings
        resultado = settings.is_pilot_mode
        assert isinstance(resultado, bool)


class TestModoPilotoFuncoes:
    """Testes das funções de modo piloto."""

    def test_is_pilot_mode_funcao_existe(self):
        """Função is_pilot_mode deve existir."""
        from app.workers.pilot_mode import is_pilot_mode
        assert callable(is_pilot_mode)

    def test_is_pilot_mode_retorna_bool(self):
        """is_pilot_mode deve retornar booleano."""
        from app.workers.pilot_mode import is_pilot_mode
        resultado = is_pilot_mode()
        assert isinstance(resultado, bool)

    def test_require_pilot_disabled_existe(self):
        """Função require_pilot_disabled deve existir."""
        from app.workers.pilot_mode import require_pilot_disabled
        assert callable(require_pilot_disabled)

    def test_skip_if_pilot_existe(self):
        """Decorator skip_if_pilot deve existir."""
        from app.workers.pilot_mode import skip_if_pilot
        assert callable(skip_if_pilot)


class TestAutonomousFeature:
    """Testes do enum AutonomousFeature."""

    def test_autonomous_feature_existe(self):
        """Enum AutonomousFeature deve existir."""
        from app.workers.pilot_mode import AutonomousFeature
        assert AutonomousFeature is not None

    def test_autonomous_feature_tem_discovery(self):
        """AutonomousFeature deve ter DISCOVERY."""
        from app.workers.pilot_mode import AutonomousFeature
        assert hasattr(AutonomousFeature, "DISCOVERY")

    def test_autonomous_feature_tem_oferta(self):
        """AutonomousFeature deve ter OFERTA."""
        from app.workers.pilot_mode import AutonomousFeature
        assert hasattr(AutonomousFeature, "OFERTA")

    def test_autonomous_feature_tem_reativacao(self):
        """AutonomousFeature deve ter REATIVACAO."""
        from app.workers.pilot_mode import AutonomousFeature
        assert hasattr(AutonomousFeature, "REATIVACAO")

    def test_autonomous_feature_tem_feedback(self):
        """AutonomousFeature deve ter FEEDBACK."""
        from app.workers.pilot_mode import AutonomousFeature
        assert hasattr(AutonomousFeature, "FEEDBACK")


class TestModoPilotoComportamento:
    """Testes de comportamento do modo piloto."""

    def test_require_pilot_disabled_bloqueia_em_piloto(self):
        """require_pilot_disabled deve retornar False em modo piloto."""
        from app.workers.pilot_mode import require_pilot_disabled, AutonomousFeature

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = True

            resultado = require_pilot_disabled(AutonomousFeature.DISCOVERY)
            assert resultado is False

    def test_require_pilot_disabled_permite_sem_piloto(self):
        """require_pilot_disabled deve retornar True sem modo piloto."""
        from app.workers.pilot_mode import require_pilot_disabled, AutonomousFeature

        with patch("app.workers.pilot_mode.settings") as mock_settings:
            mock_settings.is_pilot_mode = False

            resultado = require_pilot_disabled(AutonomousFeature.DISCOVERY)
            assert resultado is True


class TestGatilhosAutonomos:
    """Testes de gatilhos autônomos com modo piloto."""

    def test_importar_gatilhos_autonomos(self):
        """Módulo de gatilhos autônomos deve existir."""
        from app.services import gatilhos_autonomos
        assert gatilhos_autonomos is not None

    def test_constantes_gatilhos_existem(self):
        """Constantes de gatilhos devem existir."""
        from app.services.gatilhos_autonomos import (
            DISCOVERY_CAMPOS_ENRIQUECIMENTO,
            OFERTA_THRESHOLD_DIAS,
            REATIVACAO_DIAS_INATIVO,
            FEEDBACK_DIAS_RECENTES,
        )

        assert len(DISCOVERY_CAMPOS_ENRIQUECIMENTO) > 0
        assert OFERTA_THRESHOLD_DIAS > 0
        assert REATIVACAO_DIAS_INATIVO > 0
        assert FEEDBACK_DIAS_RECENTES > 0

    def test_limites_gatilhos_existem(self):
        """Limites de gatilhos devem existir."""
        from app.services.gatilhos_autonomos import (
            LIMITE_DISCOVERY_POR_CICLO,
            LIMITE_OFERTA_POR_CICLO,
            LIMITE_REATIVACAO_POR_CICLO,
            LIMITE_FEEDBACK_POR_CICLO,
        )

        assert LIMITE_DISCOVERY_POR_CICLO > 0
        assert LIMITE_OFERTA_POR_CICLO > 0
        assert LIMITE_REATIVACAO_POR_CICLO > 0
        assert LIMITE_FEEDBACK_POR_CICLO > 0
