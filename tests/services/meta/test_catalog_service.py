"""
Testes para MetaCatalogService.

Sprint 68 — Epic 68.4, Chunk 11.
"""

import pytest
from unittest.mock import MagicMock, patch


def _mock_supabase_chain(data=None):
    mock = MagicMock()
    resp = MagicMock()
    resp.data = data or []
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.upsert.return_value = mock
    mock.eq.return_value = mock
    mock.not_.is_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.execute.return_value = resp
    return mock


class TestMetaCatalogService:

    def test_mapear_vaga_para_produto(self):
        from app.services.meta.catalog_service import MetaCatalogService

        service = MetaCatalogService()
        vaga = {"id": "abc12345-6789", "status": "aberta", "valor": 2500, "data": "15/03"}
        hospital = {"nome": "São Luiz"}
        especialidade = {"nome": "Cardiologia"}

        produto = service.mapear_vaga_para_produto(vaga, hospital, especialidade)
        assert produto["product_retailer_id"] == "vaga_abc12345"
        assert "Cardiologia" in produto["name"]
        assert "São Luiz" in produto["name"]
        assert produto["price_milliunits"] == 2500000
        assert produto["availability"] == "in stock"

    def test_mapear_vaga_sem_hospital(self):
        from app.services.meta.catalog_service import MetaCatalogService

        service = MetaCatalogService()
        vaga = {"id": "def12345-6789", "status": "aberta", "valor": 1500, "hospital_nome": "Einstein"}
        produto = service.mapear_vaga_para_produto(vaga)
        assert "Einstein" in produto["name"]

    def test_mapear_vaga_fechada(self):
        from app.services.meta.catalog_service import MetaCatalogService

        service = MetaCatalogService()
        vaga = {"id": "ghi12345-6789", "status": "fechada", "valor": 0}
        produto = service.mapear_vaga_para_produto(vaga)
        assert produto["availability"] == "out of stock"

    def test_construir_descricao_produto(self):
        from app.services.meta.catalog_service import MetaCatalogService

        service = MetaCatalogService()
        vaga = {"data": "20/03", "horario": "19h-7h", "periodo": "Noturno", "setor": "UTI"}
        desc = service._construir_descricao_produto(vaga)
        assert "20/03" in desc
        assert "19h-7h" in desc

    @pytest.mark.asyncio
    async def test_sincronizar_vagas_desabilitado(self):
        with patch("app.services.meta.catalog_service.settings") as mock_settings:
            mock_settings.META_CATALOG_SYNC_ENABLED = False
            from app.services.meta.catalog_service import MetaCatalogService

            service = MetaCatalogService()
            result = await service.sincronizar_vagas_catalogo("waba_1", "cat_1")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_listar_produtos(self):
        mock_sb = _mock_supabase_chain(data=[
            {"product_retailer_id": "vaga_abc", "product_name": "Plantão"},
        ])
        with patch("app.services.meta.catalog_service.supabase", mock_sb):
            from app.services.meta.catalog_service import MetaCatalogService

            service = MetaCatalogService()
            produtos = await service.listar_produtos()
            assert len(produtos) == 1

    @pytest.mark.asyncio
    async def test_buscar_produto_por_vaga_encontrado(self):
        mock_sb = _mock_supabase_chain(data=[{"vaga_id": "v1", "product_name": "Plantão"}])
        with patch("app.services.meta.catalog_service.supabase", mock_sb):
            from app.services.meta.catalog_service import MetaCatalogService

            service = MetaCatalogService()
            produto = await service.buscar_produto_por_vaga("v1")
            assert produto is not None

    @pytest.mark.asyncio
    async def test_buscar_produto_por_vaga_nao_encontrado(self):
        mock_sb = _mock_supabase_chain(data=[])
        with patch("app.services.meta.catalog_service.supabase", mock_sb):
            from app.services.meta.catalog_service import MetaCatalogService

            service = MetaCatalogService()
            produto = await service.buscar_produto_por_vaga("inexistente")
            assert produto is None
