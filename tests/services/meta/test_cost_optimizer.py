"""
Testes para MetaCostOptimizer.

Sprint 69 — Epic 69.3, Chunk 23.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMetaCostOptimizer:

    @pytest.mark.asyncio
    async def test_decidir_dentro_janela_gratuito(self):
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=True)

        with patch("app.services.meta.window_tracker.window_tracker", mock_wt):
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            decision = await optimizer.decidir_tipo_envio("chip1", "5511999")
            assert decision.method == "free_window"
            assert decision.estimated_cost == 0.0

    @pytest.mark.asyncio
    async def test_decidir_fora_janela_utility(self):
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch("app.services.meta.window_tracker.window_tracker", mock_wt):
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            decision = await optimizer.decidir_tipo_envio("chip1", "5511999", intent="utility")
            assert decision.method == "utility_template"

    @pytest.mark.asyncio
    async def test_decidir_fora_janela_marketing(self):
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with (
            patch("app.services.meta.window_tracker.window_tracker", mock_wt),
            patch("app.services.meta.cost_optimizer.settings") as mock_s,
        ):
            mock_s.META_MM_LITE_ENABLED = False
            mock_s.META_PRICING_MARKETING_USD = 0.0625
            mock_s.META_PRICING_UTILITY_USD = 0.035
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            decision = await optimizer.decidir_tipo_envio("chip1", "5511999")
            assert decision.method == "marketing_template"

    @pytest.mark.asyncio
    async def test_decidir_mm_lite_quando_habilitado(self):
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with (
            patch("app.services.meta.window_tracker.window_tracker", mock_wt),
            patch("app.services.meta.cost_optimizer.settings") as mock_s,
        ):
            mock_s.META_MM_LITE_ENABLED = True
            mock_s.META_PRICING_MARKETING_USD = 0.0625
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            decision = await optimizer.decidir_tipo_envio("chip1", "5511999")
            assert decision.method == "mm_lite"

    @pytest.mark.asyncio
    async def test_decidir_confirmation_usa_utility(self):
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(return_value=False)

        with patch("app.services.meta.window_tracker.window_tracker", mock_wt):
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            for intent in ("confirmation", "update", "followup"):
                decision = await optimizer.decidir_tipo_envio("chip1", "5511999", intent=intent)
                assert decision.method == "utility_template"

    @pytest.mark.asyncio
    async def test_estimar_custo_campanha_sem_envios(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = resp

        with patch("app.services.meta.cost_optimizer.supabase", mock_sb):
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            estimate = await optimizer.estimar_custo_campanha("camp_1")
            assert estimate.total == 0.0

    @pytest.mark.asyncio
    async def test_sugerir_otimizacao_sem_envios(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = resp

        with patch("app.services.meta.cost_optimizer.supabase", mock_sb):
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            sugestoes = await optimizer.sugerir_otimizacao("camp_1")
            assert len(sugestoes) >= 1

    @pytest.mark.asyncio
    async def test_decidir_window_error_fallback(self):
        """Se window tracker falha, assume fora da janela."""
        mock_wt = MagicMock()
        mock_wt.esta_na_janela = AsyncMock(side_effect=Exception("Redis down"))

        with (
            patch("app.services.meta.window_tracker.window_tracker", mock_wt),
            patch("app.services.meta.cost_optimizer.settings") as mock_s,
        ):
            mock_s.META_MM_LITE_ENABLED = False
            mock_s.META_PRICING_MARKETING_USD = 0.0625
            mock_s.META_PRICING_UTILITY_USD = 0.035
            from app.services.meta.cost_optimizer import MetaCostOptimizer

            optimizer = MetaCostOptimizer()
            decision = await optimizer.decidir_tipo_envio("chip1", "5511999")
            assert decision.method == "marketing_template"

    def test_send_decision_dataclass(self):
        from app.services.meta.cost_optimizer import SendDecision

        d = SendDecision(method="free_window", estimated_cost=0.0, reason="test")
        assert d.method == "free_window"
        assert d.template_name is None

    def test_cost_estimate_dataclass(self):
        from app.services.meta.cost_optimizer import CostEstimate

        e = CostEstimate(total=1.5, recipients_in_window=10, recipients_outside=5)
        assert e.total == 1.5
        assert e.by_category == {}
