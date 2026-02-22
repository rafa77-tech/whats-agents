"""
Testes para WabaSelector.

Sprint 70+ — Chunk 29.
Sprint 72: Updated for v2 multi-WABA selection.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWabaSelector:

    @pytest.mark.asyncio
    async def test_selecionar_waba_com_chip_ativo(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 80},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

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
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba()
            assert result is None

    @pytest.mark.asyncio
    async def test_selecionar_waba_risk_level_discovery(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 80},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba(intent="discovery")
            assert result is not None
            assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_selecionar_waba_prefere_maior_trust(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 60},
            {"meta_waba_id": "waba_2", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 90},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba(intent="discovery")
            assert result is not None
            assert result.waba_id == "waba_2"

    @pytest.mark.asyncio
    async def test_selecionar_waba_evita_red_quality(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"meta_waba_id": "waba_1", "status": "active", "meta_quality_rating": "RED", "trust_score": 95},
            {"meta_waba_id": "waba_2", "status": "active", "meta_quality_rating": "GREEN", "trust_score": 50},
        ]
        mock_sb.table.return_value.select.return_value.not_.is_.return_value.execute.return_value = resp

        with patch("app.services.meta.waba_selector.supabase", mock_sb):
            from app.services.meta.waba_selector import WabaSelector

            selector = WabaSelector()
            result = await selector.selecionar_waba(intent="discovery")
            assert result is not None
            assert result.waba_id == "waba_2"

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

    def test_waba_stats_dataclass(self):
        from app.services.meta.waba_selector import WabaStats

        stats = WabaStats(
            waba_id="w1", chip_count=3, active_chips=2,
            avg_trust=85.0, min_quality="GREEN", has_red=False,
        )
        assert stats.active_chips == 2
        assert not stats.has_red
