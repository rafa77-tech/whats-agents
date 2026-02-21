"""
Testes para API routes MM Lite.

Sprint 68 — Epic 68.1, Chunk 3.
"""

import json

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestMetaMMLiteRoutes:

    @pytest.mark.asyncio
    async def test_job_mm_lite_metrics(self):
        """Job coleta métricas MM Lite."""
        from app.api.routes.jobs.meta_mm_lite import job_meta_mm_lite_metrics

        mock_service = MagicMock()
        mock_service.obter_metricas = AsyncMock(return_value={
            "total_sent": 50, "delivered": 40, "read": 20, "delivery_rate": 0.8, "read_rate": 0.4
        })

        with patch("app.services.meta.mm_lite.mm_lite_service", mock_service):
            result = await job_meta_mm_lite_metrics()
            # job_endpoint wraps in JSONResponse
            body = json.loads(result.body)
            assert body["status"] == "ok"
            assert body["processados"] == 50

    def test_mm_lite_analytics_endpoint_exists(self):
        """Endpoint de stats MM Lite existe."""
        from app.api.routes.meta_analytics import router

        routes = [r.path for r in router.routes]
        assert "/meta/analytics/mm-lite/stats" in routes

    def test_mm_lite_job_endpoint_exists(self):
        """Endpoint do job MM Lite existe."""
        from app.api.routes.jobs.meta_mm_lite import router

        routes = [r.path for r in router.routes]
        assert "/meta-mm-lite-metrics" in routes
