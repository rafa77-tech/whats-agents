"""
Testes para Meta Conversation Window Tracker.

Sprint 66 — Janela 24h para free-form vs template.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from app.services.meta.window_tracker import MetaWindowTracker, window_tracker


@pytest.fixture
def tracker():
    return MetaWindowTracker()


class TestEstaNaJanela:
    """Testes para verificação de janela ativa."""

    @pytest.mark.asyncio
    async def test_janela_ativa_retorna_true(self, tracker):
        mock_result = MagicMock()
        mock_result.data = [{"id": "some-id"}]

        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            result = await tracker.esta_na_janela("chip-1", "5511999999999")

        assert result is True

    @pytest.mark.asyncio
    async def test_janela_expirada_retorna_false(self, tracker):
        mock_result = MagicMock()
        mock_result.data = []

        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            result = await tracker.esta_na_janela("chip-1", "5511999999999")

        assert result is False

    @pytest.mark.asyncio
    async def test_sem_registro_retorna_false(self, tracker):
        mock_result = MagicMock()
        mock_result.data = None

        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gt.return_value.limit.return_value.execute.return_value = (
                mock_result
            )
            result = await tracker.esta_na_janela("chip-1", "5511999999999")

        assert result is False

    @pytest.mark.asyncio
    async def test_erro_retorna_false_conservador(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.side_effect = Exception("DB error")
            result = await tracker.esta_na_janela("chip-1", "5511999999999")

        assert result is False


class TestAbrirJanela:
    """Testes para abertura/renovação de janela."""

    @pytest.mark.asyncio
    async def test_abrir_janela_user_initiated(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_upsert = MagicMock()
            mock_sb.table.return_value.upsert.return_value.execute = mock_upsert

            await tracker.abrir_janela("chip-1", "5511999999999", "user_initiated")

            call_args = mock_sb.table.return_value.upsert.call_args
            row = call_args[0][0]
            assert row["chip_id"] == "chip-1"
            assert row["telefone"] == "5511999999999"
            assert row["window_type"] == "user_initiated"

    @pytest.mark.asyncio
    async def test_abrir_janela_click_to_whatsapp(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_upsert = MagicMock()
            mock_sb.table.return_value.upsert.return_value.execute = mock_upsert

            await tracker.abrir_janela(
                "chip-1", "5511999999999", "click_to_whatsapp"
            )

            call_args = mock_sb.table.return_value.upsert.call_args
            row = call_args[0][0]
            assert row["window_type"] == "click_to_whatsapp"

    @pytest.mark.asyncio
    async def test_abrir_janela_upsert_on_conflict(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_upsert = MagicMock()
            mock_sb.table.return_value.upsert.return_value.execute = mock_upsert

            await tracker.abrir_janela("chip-1", "5511999999999")

            upsert_kwargs = mock_sb.table.return_value.upsert.call_args
            assert upsert_kwargs.kwargs.get("on_conflict") == "chip_id,telefone"

    @pytest.mark.asyncio
    async def test_abrir_janela_erro_nao_propaga(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.side_effect = Exception("DB error")
            # Não deve levantar exceção
            await tracker.abrir_janela("chip-1", "5511999999999")


class TestLimparJanelasExpiradas:
    """Testes para limpeza de janelas expiradas."""

    @pytest.mark.asyncio
    async def test_limpar_remove_expiradas(self, tracker):
        mock_result = MagicMock()
        mock_result.data = [{"id": "1"}, {"id": "2"}]

        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.return_value.delete.return_value.lt.return_value.execute.return_value = (
                mock_result
            )
            count = await tracker.limpar_janelas_expiradas()

        assert count == 2

    @pytest.mark.asyncio
    async def test_limpar_sem_expiradas(self, tracker):
        mock_result = MagicMock()
        mock_result.data = []

        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.return_value.delete.return_value.lt.return_value.execute.return_value = (
                mock_result
            )
            count = await tracker.limpar_janelas_expiradas()

        assert count == 0

    @pytest.mark.asyncio
    async def test_limpar_erro_retorna_zero(self, tracker):
        with patch("app.services.meta.window_tracker.supabase") as mock_sb:
            mock_sb.table.side_effect = Exception("DB error")
            count = await tracker.limpar_janelas_expiradas()

        assert count == 0


class TestSingleton:
    """Teste que singleton existe."""

    def test_singleton_exportado(self):
        assert window_tracker is not None
        assert isinstance(window_tracker, MetaWindowTracker)
