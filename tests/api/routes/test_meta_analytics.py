"""
Testes para endpoints de Meta Analytics.

Sprint 67 (Chunk 6a) — 3 testes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture
def api_key():
    from app.core.config import settings

    return settings.SUPABASE_SERVICE_KEY


class TestMetaAnalyticsEndpoints:
    """Testes dos endpoints de analytics."""

    def test_ranking_sem_api_key(self, client):
        """Deve retornar 401 sem API key."""
        resp = client.get("/meta/analytics/templates/ranking")
        assert resp.status_code == 401

    def test_ranking_com_api_key(self, client, api_key):
        """Deve retornar 200 com API key válida."""
        with patch(
            "app.services.meta.template_analytics.template_analytics.obter_ranking_templates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = client.get(
                "/meta/analytics/templates/ranking",
                headers={"X-API-Key": api_key},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    def test_template_detail(self, client, api_key):
        """Deve retornar analytics de um template."""
        with patch(
            "app.services.meta.template_analytics.template_analytics.obter_analytics_template",
            new_callable=AsyncMock,
            return_value=[{"template_name": "test", "sent_count": 10}],
        ):
            resp = client.get(
                "/meta/analytics/templates/test_template",
                headers={"X-API-Key": api_key},
            )
            assert resp.status_code == 200
