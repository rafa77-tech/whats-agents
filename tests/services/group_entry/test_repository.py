"""Testes do repository de group entry.

Sprint 72 - Epic 03
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.group_entry.repository import GroupEntryRepository


@pytest.fixture
def repository():
    """Instancia do repository."""
    return GroupEntryRepository()


PATCH_TARGET = "app.services.group_entry.repository.supabase"


class TestBuscarLinkPorId:
    """Testes do metodo buscar_link_por_id."""

    @pytest.mark.asyncio
    async def test_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "id": "link-123",
                "invite_code": "ABC123",
                "status": "valid",
            }

            result = await repository.buscar_link_por_id("link-123")

            assert result is not None
            assert result["id"] == "link-123"
            assert result["invite_code"] == "ABC123"
            mock_supabase.table.assert_called_with("group_links")

    @pytest.mark.asyncio
    async def test_nao_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

            result = await repository.buscar_link_por_id("link-999")

            assert result is None

    @pytest.mark.asyncio
    async def test_erro(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.buscar_link_por_id("link-123")

            assert result is None


class TestBuscarInviteCode:
    """Testes do metodo buscar_invite_code."""

    @pytest.mark.asyncio
    async def test_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
                "invite_code": "ABC123"
            }

            result = await repository.buscar_invite_code("link-123")

            assert result == "ABC123"

    @pytest.mark.asyncio
    async def test_nao_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = None

            result = await repository.buscar_invite_code("link-999")

            assert result is None


class TestBuscarConfig:
    """Testes do metodo buscar_config."""

    @pytest.mark.asyncio
    async def test_encontrada(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [
                {"max_entradas_por_dia": 10, "max_grupos_por_chip": 5}
            ]

            result = await repository.buscar_config()

            assert result is not None
            assert result["max_entradas_por_dia"] == 10
            mock_supabase.table.assert_called_with("group_entry_config")

    @pytest.mark.asyncio
    async def test_nao_encontrada(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []

            result = await repository.buscar_config()

            assert result is None


class TestAtualizarConfig:
    """Testes do metodo atualizar_config."""

    @pytest.mark.asyncio
    async def test_sucesso(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.update.return_value.execute.return_value = MagicMock()

            result = await repository.atualizar_config({"max_entradas_por_dia": 20})

            assert result is True
            mock_supabase.table.assert_called_with("group_entry_config")

    @pytest.mark.asyncio
    async def test_erro(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.update.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.atualizar_config({"max_entradas_por_dia": 20})

            assert result is False
