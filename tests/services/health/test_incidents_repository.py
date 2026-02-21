"""Testes do repository de incidentes.

Sprint 72 - Epic 01
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.health.incidents_repository import IncidentsRepository


@pytest.fixture
def repository():
    """Instancia do repository."""
    return IncidentsRepository()


@pytest.fixture
def mock_incident_row():
    """Linha do banco mockada."""
    return {
        "id": "abc-123",
        "from_status": "healthy",
        "to_status": "critical",
        "from_score": 95,
        "to_score": 30,
        "trigger_source": "api",
        "details": {},
        "started_at": "2026-02-21T10:00:00+00:00",
        "resolved_at": None,
        "duration_seconds": None,
    }


PATCH_TARGET = "app.services.health.incidents_repository.supabase"


class TestRegistrar:
    """Testes do metodo registrar."""

    @pytest.mark.asyncio
    async def test_sucesso(self, repository, mock_incident_row):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
                mock_incident_row
            ]

            result = await repository.registrar(
                {
                    "from_status": "healthy",
                    "to_status": "critical",
                    "from_score": 95,
                    "to_score": 30,
                    "trigger_source": "api",
                    "details": {},
                }
            )

            assert result is not None
            assert result["id"] == "abc-123"
            mock_supabase.table.assert_called_with("health_incidents")

    @pytest.mark.asyncio
    async def test_erro(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.insert.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.registrar({"to_status": "critical", "to_score": 30})

            assert result is None


class TestListar:
    """Testes do metodo listar."""

    @pytest.mark.asyncio
    async def test_sem_filtros(self, repository, mock_incident_row):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                mock_incident_row
            ]

            result = await repository.listar()

            assert len(result) == 1
            assert result[0]["id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_com_filtro_status(self, repository, mock_incident_row):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                mock_incident_row
            ]

            result = await repository.listar(status="critical")

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_com_filtro_since(self, repository, mock_incident_row):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                mock_incident_row
            ]

            result = await repository.listar(since="2026-02-20T00:00:00+00:00")

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_erro_retorna_lista_vazia(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.listar()

            assert result == []


class TestBuscarEstatisticas:
    """Testes do metodo buscar_estatisticas."""

    @pytest.mark.asyncio
    async def test_retorna_dados(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.gte.return_value.execute.return_value.data = [
                {"to_status": "critical", "duration_seconds": 300},
                {"to_status": "degraded", "duration_seconds": 120},
            ]

            result = await repository.buscar_estatisticas(dias=30)

            assert len(result) == 2
            assert result[0]["to_status"] == "critical"


class TestBuscarIncidenteAtivoCritico:
    """Testes do metodo buscar_incidente_ativo_critico."""

    @pytest.mark.asyncio
    async def test_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {"id": "abc-123", "started_at": "2026-02-21T10:00:00+00:00"}
            ]

            result = await repository.buscar_incidente_ativo_critico()

            assert result is not None
            assert result["id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_nao_encontrado(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value.data = []

            result = await repository.buscar_incidente_ativo_critico()

            assert result is None


class TestResolver:
    """Testes do metodo resolver."""

    @pytest.mark.asyncio
    async def test_sucesso(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = (
                MagicMock()
            )

            result = await repository.resolver(
                incident_id="abc-123",
                resolved_at="2026-02-21T10:05:00+00:00",
                duration_seconds=300,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_erro(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.update.return_value.eq.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.resolver(
                incident_id="abc-123",
                resolved_at="2026-02-21T10:05:00+00:00",
                duration_seconds=300,
            )

            assert result is False
