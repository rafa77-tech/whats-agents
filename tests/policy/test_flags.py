"""
Testes para feature flags do Policy Engine.

Sprint 16 - Kill Switch
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.services.policy.flags import (
    PolicyEngineFlags,
    SafeModeFlags,
    CampaignsFlags,
    DisabledRulesFlags,
    get_policy_engine_flags,
    get_safe_mode_flags,
    get_campaigns_flags,
    get_disabled_rules,
    is_rule_disabled,
    is_policy_engine_enabled,
    is_safe_mode_active,
    get_safe_mode_action,
    are_campaigns_enabled,
)


class TestFlagDataclasses:
    """Testes para dataclasses de flags."""

    def test_policy_engine_flags_defaults(self):
        """PolicyEngineFlags tem enabled=True por padrão."""
        flags = PolicyEngineFlags()
        assert flags.enabled is True

    def test_safe_mode_flags_defaults(self):
        """SafeModeFlags tem enabled=False e mode=wait."""
        flags = SafeModeFlags()
        assert flags.enabled is False
        assert flags.mode == "wait"

    def test_campaigns_flags_defaults(self):
        """CampaignsFlags tem enabled=True."""
        flags = CampaignsFlags()
        assert flags.enabled is True

    def test_disabled_rules_defaults(self):
        """DisabledRulesFlags tem lista vazia."""
        flags = DisabledRulesFlags()
        assert flags.rules == []


class TestGetFlags:
    """Testes para funções de busca de flags."""

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_policy_engine_flags_from_db(self, mock_get):
        """Busca flag do banco."""
        mock_get.return_value = {"enabled": False}

        flags = await get_policy_engine_flags()

        assert flags.enabled is False
        mock_get.assert_called_once_with("policy_engine")

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_policy_engine_flags_fallback(self, mock_get):
        """Fallback para enabled=True se não encontrar."""
        mock_get.return_value = None

        flags = await get_policy_engine_flags()

        assert flags.enabled is True

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_safe_mode_flags_from_db(self, mock_get):
        """Busca safe_mode do banco."""
        mock_get.return_value = {"enabled": True, "mode": "handoff"}

        flags = await get_safe_mode_flags()

        assert flags.enabled is True
        assert flags.mode == "handoff"

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_safe_mode_flags_fallback(self, mock_get):
        """Fallback para enabled=False se não encontrar."""
        mock_get.return_value = None

        flags = await get_safe_mode_flags()

        assert flags.enabled is False
        assert flags.mode == "wait"

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_disabled_rules_from_db(self, mock_get):
        """Busca regras desabilitadas."""
        mock_get.return_value = {"rules": ["rule_1", "rule_2"]}

        flags = await get_disabled_rules()

        assert "rule_1" in flags.rules
        assert "rule_2" in flags.rules

    @pytest.mark.asyncio
    @patch("app.services.policy.flags._get_flag_value")
    async def test_get_disabled_rules_fallback(self, mock_get):
        """Fallback para lista vazia."""
        mock_get.return_value = None

        flags = await get_disabled_rules()

        assert flags.rules == []


class TestConvenienceFunctions:
    """Testes para funções de conveniência."""

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_disabled_rules")
    async def test_is_rule_disabled_true(self, mock_get):
        """Detecta regra desabilitada."""
        mock_get.return_value = DisabledRulesFlags(rules=["rule_test"])

        result = await is_rule_disabled("rule_test")

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_disabled_rules")
    async def test_is_rule_disabled_false(self, mock_get):
        """Regra não está na lista."""
        mock_get.return_value = DisabledRulesFlags(rules=["other_rule"])

        result = await is_rule_disabled("rule_test")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_policy_engine_flags")
    async def test_is_policy_engine_enabled(self, mock_get):
        """Verifica se engine está habilitado."""
        mock_get.return_value = PolicyEngineFlags(enabled=True)

        result = await is_policy_engine_enabled()

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_safe_mode_flags")
    async def test_is_safe_mode_active(self, mock_get):
        """Verifica se safe mode está ativo."""
        mock_get.return_value = SafeModeFlags(enabled=True, mode="handoff")

        result = await is_safe_mode_active()

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_safe_mode_flags")
    async def test_get_safe_mode_action(self, mock_get):
        """Retorna ação do safe mode."""
        mock_get.return_value = SafeModeFlags(enabled=True, mode="handoff")

        result = await get_safe_mode_action()

        assert result == "handoff"

    @pytest.mark.asyncio
    @patch("app.services.policy.flags.get_campaigns_flags")
    async def test_are_campaigns_enabled(self, mock_get):
        """Verifica se campanhas estão habilitadas."""
        mock_get.return_value = CampaignsFlags(enabled=False)

        result = await are_campaigns_enabled()

        assert result is False
