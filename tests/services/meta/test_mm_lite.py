"""
Testes para MMLiteService.

Sprint 68 — Epic 68.1, Chunk 1.
"""

import pytest
from unittest.mock import MagicMock, patch


def _mock_supabase_chain(data=None):
    """Helper para mockar cadeia Supabase."""
    mock = MagicMock()
    resp = MagicMock()
    resp.data = data or []
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.eq.return_value = mock
    mock.not_.is_.return_value = mock
    mock.gte.return_value = mock
    mock.lte.return_value = mock
    mock.limit.return_value = mock
    mock.order.return_value = mock
    mock.execute.return_value = resp
    return mock


class TestMMLiteService:
    """Testes do MMLiteService."""

    @pytest.mark.asyncio
    async def test_verificar_elegibilidade_desabilitado(self):
        """MM Lite desabilitado retorna não elegível."""
        with (
            patch("app.services.meta.mm_lite.settings") as mock_settings,
            patch("app.services.meta.mm_lite.supabase", _mock_supabase_chain()),
        ):
            mock_settings.META_MM_LITE_ENABLED = False
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            result = await service.verificar_elegibilidade("waba_123")
            assert result["elegivel"] is False
            assert "desabilitado" in result["motivo"]

    @pytest.mark.asyncio
    async def test_verificar_elegibilidade_habilitado(self):
        """MM Lite habilitado com WABA ativa retorna elegível."""
        mock_sb = _mock_supabase_chain(
            data=[{"id": "chip1", "meta_waba_id": "waba_123", "meta_access_token": "token", "status": "active"}]
        )
        with (
            patch("app.services.meta.mm_lite.settings") as mock_settings,
            patch("app.services.meta.mm_lite.supabase", mock_sb),
        ):
            mock_settings.META_MM_LITE_ENABLED = True
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            result = await service.verificar_elegibilidade("waba_123")
            assert result["elegivel"] is True

    @pytest.mark.asyncio
    async def test_esta_habilitado_retorna_bool(self):
        """esta_habilitado retorna bool."""
        with (
            patch("app.services.meta.mm_lite.settings") as mock_settings,
            patch("app.services.meta.mm_lite.supabase", _mock_supabase_chain()),
        ):
            mock_settings.META_MM_LITE_ENABLED = False
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            result = await service.esta_habilitado("waba_123")
            assert result is False

    def test_deve_usar_mm_lite_campanha(self):
        """Campanha de marketing deve usar MM Lite."""
        with patch("app.services.meta.mm_lite.settings") as mock_settings:
            mock_settings.META_MM_LITE_ENABLED = True
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            assert service.deve_usar_mm_lite({"tipo": "marketing", "campanha_id": "camp1"}) is True

    def test_deve_usar_mm_lite_urgente_false(self):
        """Mensagens urgentes nunca usam MM Lite."""
        with patch("app.services.meta.mm_lite.settings") as mock_settings:
            mock_settings.META_MM_LITE_ENABLED = True
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            assert service.deve_usar_mm_lite({"tipo": "marketing", "urgente": True}) is False
