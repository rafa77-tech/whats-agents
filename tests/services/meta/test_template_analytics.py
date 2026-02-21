"""
Testes para MetaTemplateAnalytics.

Sprint 67 (Epic 67.3, Chunk 6a) — 11 testes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date


def _mock_chain(data=None, count=None):
    mock = MagicMock()
    mock_resp = MagicMock()
    mock_resp.data = data or []
    mock_resp.count = count

    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.upsert.return_value = mock
    mock.eq.return_value = mock
    mock.in_.return_value = mock
    mock.not_.is_.return_value = mock
    mock.gte.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.rpc.return_value = mock
    mock.execute.return_value = mock_resp
    return mock


class TestMetaTemplateAnalytics:
    """Testes do MetaTemplateAnalytics."""

    @pytest.mark.asyncio
    async def test_coletar_analytics_sem_wabas(self):
        """Deve retornar 0 quando não há WABAs."""
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=[])

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics.coletar_analytics()

            assert result["total_wabas"] == 0
            assert result["templates_atualizados"] == 0

    @pytest.mark.asyncio
    async def test_coletar_analytics_com_wabas(self):
        """Deve coletar de WABAs ativas."""
        chips = [
            {"meta_waba_id": "waba-1", "meta_access_token": "token-1"},
        ]

        with patch("app.services.meta.template_analytics.supabase") as mock_sb, \
             patch("app.services.meta.template_analytics.get_http_client") as mock_http:

            mock_sb.table.return_value = _mock_chain(data=chips)

            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": [
                    {"name": "template_1", "language": "pt_BR", "status": "APPROVED"},
                ]
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics.coletar_analytics()

            assert result["total_wabas"] == 1

    @pytest.mark.asyncio
    async def test_consultar_analytics_api_sucesso(self):
        """Deve retornar lista de templates."""
        with patch("app.services.meta.template_analytics.get_http_client") as mock_http:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": [
                    {"name": "tpl1", "language": "pt_BR"},
                    {"name": "tpl2", "language": "en_US"},
                ]
            }
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics._consultar_analytics_api("waba-1", "token-1")

            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_consultar_analytics_api_erro(self):
        """Deve retornar None em erro."""
        with patch("app.services.meta.template_analytics.get_http_client") as mock_http:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_client.get.return_value = mock_resp
            mock_http.return_value = mock_client

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics._consultar_analytics_api("waba-1", "bad-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_salvar_analytics(self):
        """Deve fazer upsert de templates."""
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            chain = _mock_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            count = await analytics._salvar_analytics(
                "waba-1",
                [{"name": "tpl1", "language": "pt_BR"}],
            )

            assert count == 1
            chain.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_salvar_analytics_sem_nome(self):
        """Deve ignorar templates sem nome."""
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            chain = _mock_chain()
            mock_sb.table.return_value = chain

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            count = await analytics._salvar_analytics(
                "waba-1",
                [{"language": "pt_BR"}],  # sem name
            )

            assert count == 0

    @pytest.mark.asyncio
    async def test_obter_analytics_template(self):
        """Deve retornar analytics de um template."""
        data = [
            {"template_name": "tpl1", "sent_count": 100, "delivery_rate": 0.95},
        ]
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=data)

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics.obter_analytics_template("tpl1")

            assert len(result) == 1
            assert result[0]["delivery_rate"] == 0.95

    @pytest.mark.asyncio
    async def test_obter_ranking_templates_fallback(self):
        """Deve usar fallback quando rpc falha."""
        data = [
            {"template_name": "tpl1", "sent_count": 50, "delivery_rate": 0.90, "read_rate": 0.5, "cost_usd": 1.0},
        ]
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            # rpc raises exception → fallback to table query
            mock_sb.rpc.side_effect = Exception("rpc not available")
            mock_sb.table.return_value = _mock_chain(data=data)

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            result = await analytics.obter_ranking_templates()

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_detectar_templates_baixa_performance(self):
        """Deve detectar templates abaixo do threshold."""
        data = [
            {
                "template_name": "tpl_bad",
                "waba_id": "waba-1",
                "sent_count": 50,
                "delivery_rate": 0.60,
                "read_rate": 0.10,
                "date": "2026-02-20",
            },
        ]
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=data)

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            alertas = await analytics.detectar_templates_baixa_performance()

            assert len(alertas) == 1
            assert alertas[0]["template_name"] == "tpl_bad"
            assert len(alertas[0]["motivos"]) == 2  # delivery e read

    @pytest.mark.asyncio
    async def test_detectar_templates_sem_problemas(self):
        """Deve retornar vazio quando todos estão OK."""
        data = [
            {
                "template_name": "tpl_good",
                "waba_id": "waba-1",
                "sent_count": 50,
                "delivery_rate": 0.95,
                "read_rate": 0.50,
                "date": "2026-02-20",
            },
        ]
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            mock_sb.table.return_value = _mock_chain(data=data)

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            alertas = await analytics.detectar_templates_baixa_performance()

            assert len(alertas) == 0

    @pytest.mark.asyncio
    async def test_obter_analytics_template_com_waba(self):
        """Deve filtrar por waba_id quando fornecido."""
        with patch("app.services.meta.template_analytics.supabase") as mock_sb:
            chain = _mock_chain(data=[])
            mock_sb.table.return_value = chain

            from app.services.meta.template_analytics import MetaTemplateAnalytics

            analytics = MetaTemplateAnalytics()
            await analytics.obter_analytics_template("tpl1", waba_id="waba-1")

            # Should have called eq for both template_name and waba_id
            assert chain.eq.call_count >= 2
