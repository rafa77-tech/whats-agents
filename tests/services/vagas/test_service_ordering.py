"""
Testes para ordenação por criticidade no service de vagas.

Sprint 64 - Issue #121: Cobertura de criticidade e multiplicidade.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.vagas.service import buscar_vagas_compativeis


@pytest.fixture
def vagas_desordenadas():
    """Vagas com diferentes criticidades e datas, fora de ordem."""
    return [
        {
            "id": "v1",
            "data": "2026-03-01",
            "criticidade": "normal",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
        {
            "id": "v2",
            "data": "2026-03-02",
            "criticidade": "urgente",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
        {
            "id": "v3",
            "data": "2026-02-28",
            "criticidade": "critica",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
        {
            "id": "v4",
            "data": "2026-02-25",
            "criticidade": "urgente",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
        {
            "id": "v5",
            "data": "2026-03-05",
            "criticidade": "normal",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
    ]


@pytest.mark.asyncio
async def test_ordenacao_critica_antes_de_urgente_antes_de_normal(vagas_desordenadas):
    """Vagas críticas devem aparecer primeiro, depois urgentes, depois normais."""
    with (
        patch(
            "app.services.vagas.cache.get_cached", new_callable=AsyncMock, return_value=None
        ),
        patch(
            "app.services.vagas.repository.listar_disponiveis",
            new_callable=AsyncMock,
            return_value=vagas_desordenadas,
        ),
        patch("app.services.vagas.cache.set_cached", new_callable=AsyncMock),
    ):
        resultado = await buscar_vagas_compativeis(especialidade_id="esp1", limite=10)

    criticidades = [v["criticidade"] for v in resultado]
    assert criticidades == ["critica", "urgente", "urgente", "normal", "normal"]


@pytest.mark.asyncio
async def test_ordenacao_preserva_data_dentro_da_mesma_criticidade(vagas_desordenadas):
    """Dentro do mesmo nível de criticidade, vagas devem ser ordenadas por data."""
    with (
        patch(
            "app.services.vagas.cache.get_cached", new_callable=AsyncMock, return_value=None
        ),
        patch(
            "app.services.vagas.repository.listar_disponiveis",
            new_callable=AsyncMock,
            return_value=vagas_desordenadas,
        ),
        patch("app.services.vagas.cache.set_cached", new_callable=AsyncMock),
    ):
        resultado = await buscar_vagas_compativeis(especialidade_id="esp1", limite=10)

    # Urgentes: v4 (02-25) antes de v2 (03-02)
    urgentes = [v for v in resultado if v["criticidade"] == "urgente"]
    assert urgentes[0]["id"] == "v4"
    assert urgentes[1]["id"] == "v2"

    # Normais: v1 (03-01) antes de v5 (03-05)
    normais = [v for v in resultado if v["criticidade"] == "normal"]
    assert normais[0]["id"] == "v1"
    assert normais[1]["id"] == "v5"


@pytest.mark.asyncio
async def test_ordenacao_criticidade_desconhecida_tratada_como_normal():
    """Vagas sem criticidade ou com valor desconhecido devem ser tratadas como normal."""
    vagas = [
        {"id": "v1", "data": "2026-03-01", "especialidade_id": "esp1", "status": "aberta"},
        {
            "id": "v2",
            "data": "2026-03-01",
            "criticidade": "urgente",
            "especialidade_id": "esp1",
            "status": "aberta",
        },
    ]

    with (
        patch(
            "app.services.vagas.cache.get_cached", new_callable=AsyncMock, return_value=None
        ),
        patch(
            "app.services.vagas.repository.listar_disponiveis",
            new_callable=AsyncMock,
            return_value=vagas,
        ),
        patch("app.services.vagas.cache.set_cached", new_callable=AsyncMock),
    ):
        resultado = await buscar_vagas_compativeis(especialidade_id="esp1", limite=10)

    assert resultado[0]["id"] == "v2"  # urgente first
    assert resultado[1]["id"] == "v1"  # sem criticidade = normal
