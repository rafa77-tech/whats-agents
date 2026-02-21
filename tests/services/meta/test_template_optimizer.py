"""
Testes para MetaTemplateOptimizer.

Sprint 70+ — Chunk 28.
"""

import pytest
from unittest.mock import MagicMock, patch


def _mock_analytics(data):
    mock_sb = MagicMock()
    resp = MagicMock()
    resp.data = data
    mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = resp
    mock_sb.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value = resp
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = resp
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = resp
    return mock_sb


class TestMetaTemplateOptimizer:

    @pytest.mark.asyncio
    async def test_identificar_baixa_performance_delivery(self):
        mock_sb = _mock_analytics([
            {"template_name": "t1", "waba_id": "w1", "sent": 100, "delivered": 50, "read": 10, "delivery_rate": 0.5, "read_rate": 0.1},
        ])
        with patch("app.services.meta.template_optimizer.supabase", mock_sb):
            from app.services.meta.template_optimizer import MetaTemplateOptimizer

            optimizer = MetaTemplateOptimizer()
            problemas = await optimizer.identificar_baixa_performance()
            assert len(problemas) >= 1
            assert problemas[0]["delivery_rate"] < 0.8

    @pytest.mark.asyncio
    async def test_identificar_sem_problemas(self):
        mock_sb = _mock_analytics([
            {"template_name": "t1", "waba_id": "w1", "sent": 100, "delivered": 95, "read": 50, "delivery_rate": 0.95, "read_rate": 0.5},
        ])
        with patch("app.services.meta.template_optimizer.supabase", mock_sb):
            from app.services.meta.template_optimizer import MetaTemplateOptimizer

            optimizer = MetaTemplateOptimizer()
            problemas = await optimizer.identificar_baixa_performance()
            assert len(problemas) == 0

    @pytest.mark.asyncio
    async def test_sugerir_melhorias_delivery_baixo(self):
        mock_sb = _mock_analytics([
            {"sent": 100, "delivered": 50, "read": 10, "delivery_rate": 0.5, "read_rate": 0.1},
        ])
        with patch("app.services.meta.template_optimizer.supabase", mock_sb):
            from app.services.meta.template_optimizer import MetaTemplateOptimizer

            optimizer = MetaTemplateOptimizer()
            sugestoes = await optimizer.sugerir_melhorias("t1")
            assert any(s["tipo"] == "delivery" for s in sugestoes)

    @pytest.mark.asyncio
    async def test_sugerir_melhorias_sem_dados(self):
        mock_sb = _mock_analytics([])
        with patch("app.services.meta.template_optimizer.supabase", mock_sb):
            from app.services.meta.template_optimizer import MetaTemplateOptimizer

            optimizer = MetaTemplateOptimizer()
            sugestoes = await optimizer.sugerir_melhorias("inexistente")
            assert len(sugestoes) == 1
            assert sugestoes[0]["tipo"] == "info"

    @pytest.mark.asyncio
    async def test_comparar_variantes_ab(self):
        mock_sb = _mock_analytics([
            {"sent": 100, "delivered": 90, "read": 50},
        ])
        with patch("app.services.meta.template_optimizer.supabase", mock_sb):
            from app.services.meta.template_optimizer import MetaTemplateOptimizer

            optimizer = MetaTemplateOptimizer()
            result = await optimizer.comparar_variantes_ab("t_a", "t_b")
            assert "template_a" in result
            assert "template_b" in result
