"""Testes dos metodos listar e buscar_stats_fila do CampanhaRepository.

Sprint 72 - Epic 04
"""

import pytest
from unittest.mock import patch

from app.services.campanhas.repository import CampanhaRepository


@pytest.fixture
def repository():
    """Instancia do repository."""
    return CampanhaRepository()


PATCH_TARGET = "app.services.campanhas.repository.supabase"

# Dados mock completos para CampanhaData.from_db_row
_ROW_1 = {
    "id": 1,
    "nome_template": "Test",
    "tipo_campanha": "discovery",
    "status": "rascunho",
    "total_destinatarios": 0,
    "enviados": 0,
    "entregues": 0,
    "respondidos": 0,
    "created_at": None,
    "agendar_para": None,
    "iniciada_em": None,
    "concluida_em": None,
    "corpo": None,
    "tom": "amigavel",
    "objetivo": None,
    "audience_filters": None,
    "pode_ofertar": True,
}

_ROW_2 = {**_ROW_1, "id": 2, "nome_template": "Test 2", "status": "ativa"}


class TestListar:
    """Testes do metodo listar."""

    @pytest.mark.asyncio
    async def test_sem_filtros(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                _ROW_1,
                _ROW_2,
            ]

            result = await repository.listar()

            assert len(result) == 2
            assert result[0].id == 1
            mock_supabase.table.assert_called_with("campanhas")

    @pytest.mark.asyncio
    async def test_com_filtro_status(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {**_ROW_1, "status": "ativa"},
            ]

            result = await repository.listar(status="ativa")

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_com_filtro_tipo(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                {**_ROW_1, "tipo_campanha": "discovery"},
            ]

            result = await repository.listar(tipo="discovery")

            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_com_ambos_filtros(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

            result = await repository.listar(status="ativa", tipo="discovery")

            assert result == []

    @pytest.mark.asyncio
    async def test_erro_retorna_vazio(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.order.return_value.limit.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.listar()

            assert result == []


class TestBuscarStatsFila:
    """Testes do metodo buscar_stats_fila."""

    @pytest.mark.asyncio
    async def test_com_dados(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
                {"status": "enviada"},
                {"status": "enviada"},
                {"status": "erro"},
                {"status": "pendente"},
            ]

            result = await repository.buscar_stats_fila(16)

            assert result["total"] == 4
            assert result["enviados"] == 2
            assert result["erros"] == 1
            assert result["pendentes"] == 1
            assert result["taxa_entrega"] == 0.5
            mock_supabase.table.assert_called_with("fila_mensagens")

    @pytest.mark.asyncio
    async def test_sem_dados(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

            result = await repository.buscar_stats_fila(16)

            assert result["total"] == 0
            assert result["taxa_entrega"] == 0

    @pytest.mark.asyncio
    async def test_erro_retorna_zeros(self, repository):
        with patch(PATCH_TARGET) as mock_supabase:
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception(
                "DB error"
            )

            result = await repository.buscar_stats_fila(16)

            assert result["total"] == 0
            assert result["enviados"] == 0
