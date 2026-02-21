"""
Testes para WabaSelector.

Sprint 70+ — Chunk 29.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestWabaSelector:

    @pytest.mark.asyncio
    async def test_selecionar_waba_com_chip_ativo(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 80}]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba()
            assert result is not None
            assert result.waba_id == "waba_1"

    @pytest.mark.asyncio
    async def test_selecionar_waba_sem_chip(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba()
            assert result is None

    @pytest.mark.asyncio
    async def test_selecionar_waba_risk_level_discovery(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 80}]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba(intent="discovery")
            assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_listar_wabas_disponiveis(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"meta_waba_id": "waba_1", "nome": "Chip A", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 80},
            {"meta_waba_id": "waba_1", "nome": "Chip B", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 70},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            wabas = await selector.listar_wabas_disponiveis()
            assert len(wabas) == 1
            assert wabas[0]["active_chips"] == 2

    def test_waba_selection_dataclass(self):
        from app.services.meta.waba_selector import WabaSelection

        sel = WabaSelection(waba_id="w1", reason="test", risk_level="low")
        assert sel.waba_id == "w1"
