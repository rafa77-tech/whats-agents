"""
Testes para MetaBudgetAlerts.

Sprint 69 — Epic 69.3, Chunk 24.
"""

import pytest
from unittest.mock import MagicMock, patch


def _mock_costs(data):
    mock_sb = MagicMock()
    resp = MagicMock()
    resp.data = data
    mock_sb.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = resp
    mock_sb.table.return_value.select.return_value.gte.return_value.lte.return_value.eq.return_value.execute.return_value = resp
    return mock_sb


class TestMetaBudgetAlerts:

    @pytest.mark.asyncio
    async def test_verificar_budget_diario_ok(self):
        mock_sb = _mock_costs([{"cost_usd": "10.0"}, {"cost_usd": "5.0"}])
        with (
            patch("app.services.meta.budget_alerts.supabase", mock_sb),
            patch("app.services.meta.budget_alerts.settings") as mock_s,
        ):
            mock_s.META_BUDGET_DIARIO_USD = 50.0
            from app.services.meta.budget_alerts import MetaBudgetAlerts

            service = MetaBudgetAlerts()
            result = await service.verificar_budget_diario()
            assert result["nivel"] == "ok"
            assert result["gasto_usd"] == 15.0

    @pytest.mark.asyncio
    async def test_verificar_budget_diario_warning(self):
        mock_sb = _mock_costs([{"cost_usd": "42.0"}])
        with (
            patch("app.services.meta.budget_alerts.supabase", mock_sb),
            patch("app.services.meta.budget_alerts.settings") as mock_s,
        ):
            mock_s.META_BUDGET_DIARIO_USD = 50.0
            from app.services.meta.budget_alerts import MetaBudgetAlerts

            service = MetaBudgetAlerts()
            result = await service.verificar_budget_diario()
            assert result["nivel"] == "warning"

    @pytest.mark.asyncio
    async def test_verificar_budget_diario_critical(self):
        mock_sb = _mock_costs([{"cost_usd": "48.0"}])
        with (
            patch("app.services.meta.budget_alerts.supabase", mock_sb),
            patch("app.services.meta.budget_alerts.settings") as mock_s,
        ):
            mock_s.META_BUDGET_DIARIO_USD = 50.0
            from app.services.meta.budget_alerts import MetaBudgetAlerts

            service = MetaBudgetAlerts()
            result = await service.verificar_budget_diario()
            assert result["nivel"] == "critical"

    @pytest.mark.asyncio
    async def test_verificar_budget_diario_block(self):
        mock_sb = _mock_costs([{"cost_usd": "55.0"}])
        with (
            patch("app.services.meta.budget_alerts.supabase", mock_sb),
            patch("app.services.meta.budget_alerts.settings") as mock_s,
        ):
            mock_s.META_BUDGET_DIARIO_USD = 50.0
            from app.services.meta.budget_alerts import MetaBudgetAlerts

            service = MetaBudgetAlerts()
            result = await service.verificar_budget_diario()
            assert result["nivel"] == "block"

    def test_classificar_nivel(self):
        from app.services.meta.budget_alerts import MetaBudgetAlerts

        service = MetaBudgetAlerts()
        assert service._classificar_nivel(0.5) == "ok"
        assert service._classificar_nivel(0.8) == "warning"
        assert service._classificar_nivel(0.95) == "critical"
        assert service._classificar_nivel(1.0) == "block"
        assert service._classificar_nivel(1.5) == "block"

    @pytest.mark.asyncio
    async def test_verificar_budget_semanal(self):
        mock_sb = _mock_costs([{"cost_usd": "100.0"}])
        with (
            patch("app.services.meta.budget_alerts.supabase", mock_sb),
            patch("app.services.meta.budget_alerts.settings") as mock_s,
        ):
            mock_s.META_BUDGET_SEMANAL_USD = 300.0
            from app.services.meta.budget_alerts import MetaBudgetAlerts

            service = MetaBudgetAlerts()
            result = await service.verificar_budget_semanal()
            assert result["periodo"] == "semanal"
            assert result["nivel"] == "ok"
