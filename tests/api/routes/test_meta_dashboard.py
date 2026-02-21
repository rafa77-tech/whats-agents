"""
Testes para API routes Meta Dashboard.

Sprint 69 — Epic 69.2, Chunk 16.
"""

import pytest


class TestMetaDashboardRoutes:

    def test_dashboard_router_has_quality_routes(self):
        from app.api.routes.meta_dashboard import router

        paths = [r.path for r in router.routes]
        assert "/meta/dashboard/quality/overview" in paths
        assert "/meta/dashboard/quality/history" in paths
        assert "/meta/dashboard/quality/kill-switch" in paths

    def test_dashboard_router_has_cost_routes(self):
        from app.api.routes.meta_dashboard import router

        paths = [r.path for r in router.routes]
        assert "/meta/dashboard/costs/summary" in paths
        assert "/meta/dashboard/costs/by-chip" in paths
        assert "/meta/dashboard/costs/by-template" in paths

    def test_dashboard_router_has_template_route(self):
        from app.api.routes.meta_dashboard import router

        paths = [r.path for r in router.routes]
        assert "/meta/dashboard/templates/list" in paths

    def test_dashboard_router_prefix(self):
        from app.api.routes.meta_dashboard import router

        assert router.prefix == "/meta/dashboard"

    def test_dashboard_router_tags(self):
        from app.api.routes.meta_dashboard import router

        assert "Meta Dashboard" in router.tags

    @pytest.mark.asyncio
    async def test_quality_overview_service(self):
        """Dashboard service retorna overview."""
        from unittest.mock import MagicMock, patch

        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"id": "c1", "nome": "Chip1", "status": "active", "meta_waba_id": "w1", "meta_quality_rating": "GREEN", "trust_score": 80},
            {"id": "c2", "nome": "Chip2", "status": "active", "meta_waba_id": "w2", "meta_quality_rating": "YELLOW", "trust_score": 40},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.dashboard_service.supabase", mock_sb):
            from app.services.meta.dashboard_service import MetaDashboardService

            service = MetaDashboardService()
            overview = await service.obter_quality_overview()
            assert overview["total"] == 2
            assert overview["green"] == 1
            assert overview["yellow"] == 1

    @pytest.mark.asyncio
    async def test_cost_summary_service(self):
        """Dashboard service retorna cost summary."""
        from unittest.mock import MagicMock, patch

        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"message_category": "marketing", "cost_usd": "0.0625", "is_free": False},
            {"message_category": "service", "cost_usd": "0", "is_free": True},
        ]
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = resp

        with patch("app.services.meta.dashboard_service.supabase", mock_sb):
            from app.services.meta.dashboard_service import MetaDashboardService

            service = MetaDashboardService()
            summary = await service.obter_cost_summary()
            assert summary["total_messages"] == 2
            assert summary["free_messages"] == 1

    @pytest.mark.asyncio
    async def test_cost_by_chip_service(self):
        """Dashboard service retorna cost by chip."""
        from unittest.mock import MagicMock, patch

        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"chip_id": "c1", "cost_usd": "0.0625"},
            {"chip_id": "c1", "cost_usd": "0.035"},
        ]
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = resp

        with patch("app.services.meta.dashboard_service.supabase", mock_sb):
            from app.services.meta.dashboard_service import MetaDashboardService

            service = MetaDashboardService()
            by_chip = await service.obter_cost_by_chip()
            assert len(by_chip) == 1
            assert by_chip[0]["chip_id"] == "c1"
            assert by_chip[0]["total_messages"] == 2

    @pytest.mark.asyncio
    async def test_cost_by_template_service(self):
        """Dashboard service retorna cost by template."""
        from unittest.mock import MagicMock, patch

        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"template_name": "promo_v1", "cost_usd": "0.0625"},
            {"template_name": "promo_v1", "cost_usd": "0.0625"},
        ]
        mock_sb.table.return_value.select.return_value.gte.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.dashboard_service.supabase", mock_sb):
            from app.services.meta.dashboard_service import MetaDashboardService

            service = MetaDashboardService()
            by_template = await service.obter_cost_by_template()
            assert len(by_template) == 1
            assert by_template[0]["total_sent"] == 2
