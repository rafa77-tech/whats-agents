"""
Testes para MetaWindowKeeper.

Sprint 70+ — Chunk 27.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone


class TestMetaWindowKeeper:

    @pytest.mark.asyncio
    async def test_identificar_janelas_expirando(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"chip_id": "c1", "telefone": "5511999", "window_type": "user_initiated", "expires_at": "2026-02-21T16:00:00Z"},
        ]
        mock_sb.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = resp

        with patch("app.services.meta.window_keeper.supabase", mock_sb):
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            janelas = await keeper.identificar_janelas_expirando()
            assert len(janelas) == 1

    @pytest.mark.asyncio
    async def test_executar_check_in_fora_horario(self):
        mock_now = MagicMock()
        mock_now.hour = 22
        mock_now.weekday.return_value = 0

        with (
            patch("app.core.timezone.agora_brasilia", return_value=mock_now),
            patch("app.services.meta.window_keeper.settings") as mock_s,
        ):
            mock_s.HORARIO_INICIO = "08:00"
            mock_s.HORARIO_FIM = "20:00"
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            result = await keeper.executar_check_in()
            assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_executar_check_in_fim_de_semana(self):
        mock_now = MagicMock()
        mock_now.hour = 10
        mock_now.weekday.return_value = 5  # Saturday

        with (
            patch("app.core.timezone.agora_brasilia", return_value=mock_now),
            patch("app.services.meta.window_keeper.settings") as mock_s,
        ):
            mock_s.HORARIO_INICIO = "08:00"
            mock_s.HORARIO_FIM = "20:00"
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            result = await keeper.executar_check_in()
            assert result["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_executar_check_in_sem_janelas(self):
        mock_now = MagicMock()
        mock_now.hour = 10
        mock_now.weekday.return_value = 1

        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.gte.return_value.lte.return_value.execute.return_value = resp

        with (
            patch("app.core.timezone.agora_brasilia", return_value=mock_now),
            patch("app.services.meta.window_keeper.supabase", mock_sb),
            patch("app.services.meta.window_keeper.settings") as mock_s,
        ):
            mock_s.HORARIO_INICIO = "08:00"
            mock_s.HORARIO_FIM = "20:00"
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            result = await keeper.executar_check_in()
            assert result["status"] == "ok"
            assert result["enviados"] == 0

    @pytest.mark.asyncio
    async def test_conversa_engajada_com_mensagens(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"id": "interacao_1"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.window_keeper.supabase", mock_sb):
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            result = await keeper._conversa_engajada("c1", "5511999")
            assert result is True

    @pytest.mark.asyncio
    async def test_conversa_nao_engajada(self):
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.limit.return_value.execute.return_value = resp

        with patch("app.services.meta.window_keeper.supabase", mock_sb):
            from app.services.meta.window_keeper import MetaWindowKeeper

            keeper = MetaWindowKeeper()
            result = await keeper._conversa_engajada("c1", "5511999")
            assert result is False
