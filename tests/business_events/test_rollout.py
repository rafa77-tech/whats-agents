"""
Testes para controle de rollout de business events.

Sprint 17 - E08
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.business_events.rollout import (
    should_emit_event,
    get_rollout_status,
    get_canary_config,
    clear_cache,
    _get_phase_name,
)


class TestShouldEmitEvent:
    """Testes para should_emit_event."""

    @pytest.fixture(autouse=True)
    def clear_rollout_cache(self):
        """Limpa cache antes de cada teste."""
        clear_cache()
        yield
        clear_cache()

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_disabled(self, mock_supabase):
        """Nao emite quando desabilitado."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": False, "percentage": 0, "force_on": []}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        result = await should_emit_event("cliente-123", "doctor_inbound")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_100_percent(self, mock_supabase):
        """Emite para todos quando 100%."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 100, "force_on": []}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        result = await should_emit_event("cliente-123", "doctor_inbound")

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_force_on(self, mock_supabase):
        """Emite para cliente na allowlist."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 0, "force_on": ["cliente-vip"]}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        result = await should_emit_event("cliente-vip", "doctor_inbound")

        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_not_in_force_on(self, mock_supabase):
        """Nao emite para cliente fora da allowlist com 0%."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 0, "force_on": ["cliente-vip"]}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        result = await should_emit_event("cliente-normal", "doctor_inbound")

        assert result is False

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_percentage_consistent(self, mock_supabase):
        """Hash consistente - mesmo cliente sempre no mesmo bucket."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 50, "force_on": []}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        cliente_id = "cliente-teste-123"

        # Chamar varias vezes - deve sempre retornar o mesmo resultado
        results = []
        for _ in range(5):
            clear_cache()  # Limpa cache para forcar nova query
            result = await should_emit_event(cliente_id, "doctor_inbound")
            results.append(result)

        # Todos os resultados devem ser iguais
        assert all(r == results[0] for r in results)

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_should_emit_db_error(self, mock_supabase):
        """Nao emite em caso de erro no banco."""
        mock_supabase.table.side_effect = Exception("DB error")

        result = await should_emit_event("cliente-123", "doctor_inbound")

        assert result is False


class TestGetRolloutStatus:
    """Testes para get_rollout_status."""

    @pytest.fixture(autouse=True)
    def clear_rollout_cache(self):
        """Limpa cache antes de cada teste."""
        clear_cache()
        yield
        clear_cache()

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_get_rollout_status(self, mock_supabase):
        """Retorna status formatado."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 10, "force_on": ["a", "b"]}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        status = await get_rollout_status()

        assert status["enabled"] is True
        assert status["percentage"] == 10
        assert status["force_on_count"] == 2
        assert status["phase"] == "canary_10pct"


class TestGetPhaseName:
    """Testes para _get_phase_name."""

    def test_phase_disabled(self):
        assert _get_phase_name(0) == "disabled"

    def test_phase_canary_2pct(self):
        assert _get_phase_name(2) == "canary_2pct"
        assert _get_phase_name(5) == "canary_2pct"

    def test_phase_canary_10pct(self):
        assert _get_phase_name(10) == "canary_10pct"
        assert _get_phase_name(15) == "canary_10pct"

    def test_phase_canary_50pct(self):
        assert _get_phase_name(50) == "canary_50pct"
        assert _get_phase_name(60) == "canary_50pct"

    def test_phase_full_rollout(self):
        assert _get_phase_name(100) == "full_rollout"
        assert _get_phase_name(75) == "full_rollout"


class TestCanaryCache:
    """Testes para cache do canary."""

    @pytest.fixture(autouse=True)
    def clear_rollout_cache(self):
        """Limpa cache antes de cada teste."""
        clear_cache()
        yield
        clear_cache()

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_cache_is_used(self, mock_supabase):
        """Cache evita queries repetidas."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 100, "force_on": []}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        # Primeira chamada - vai ao banco
        await get_canary_config()
        assert mock_supabase.table.call_count == 1

        # Segunda chamada - usa cache
        await get_canary_config()
        assert mock_supabase.table.call_count == 1  # Nao incrementou

    @pytest.mark.asyncio
    @patch("app.services.business_events.rollout.supabase")
    async def test_clear_cache_works(self, mock_supabase):
        """clear_cache limpa o cache."""
        mock_response = MagicMock()
        mock_response.data = {"value": {"enabled": True, "percentage": 100, "force_on": []}}
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

        # Primeira chamada
        await get_canary_config()
        assert mock_supabase.table.call_count == 1

        # Limpar cache
        clear_cache()

        # Terceira chamada - vai ao banco novamente
        await get_canary_config()
        assert mock_supabase.table.call_count == 2
