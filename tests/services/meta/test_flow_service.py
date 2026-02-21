"""
Testes para MetaFlowService.

Sprint 68 — Epic 68.2, Chunk 4.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_supabase_chain(data=None):
    mock = MagicMock()
    resp = MagicMock()
    resp.data = data or []
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.eq.return_value = mock
    mock.not_.is_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.execute.return_value = resp
    return mock


class TestMetaFlowService:

    @pytest.mark.asyncio
    async def test_criar_flow_sucesso(self):
        mock_sb = _mock_supabase_chain(data=[{"meta_access_token": "token_abc"}])
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "flow_123"}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with (
            patch("app.services.meta.flow_service.supabase", mock_sb),
            patch("app.services.http_client.get_http_client", return_value=mock_client),
        ):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.criar_flow("waba_1", "onboarding_flow")
            assert result["success"] is True
            assert result["flow_id"] == "flow_123"

    @pytest.mark.asyncio
    async def test_criar_flow_sem_token(self):
        mock_sb = _mock_supabase_chain(data=[])
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.criar_flow("waba_1", "test_flow")
            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_publicar_flow_sucesso(self):
        mock_sb = _mock_supabase_chain(data=[{"meta_access_token": "token_abc"}])
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with (
            patch("app.services.meta.flow_service.supabase", mock_sb),
            patch("app.services.http_client.get_http_client", return_value=mock_client),
        ):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.publicar_flow("waba_1", "flow_123")
            assert result["success"] is True
            assert result["status"] == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_listar_flows(self):
        mock_sb = _mock_supabase_chain(data=[
            {"id": "1", "name": "flow_a", "status": "PUBLISHED"},
            {"id": "2", "name": "flow_b", "status": "DRAFT"},
        ])
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            flows = await service.listar_flows("waba_1")
            assert len(flows) == 2

    @pytest.mark.asyncio
    async def test_buscar_flow_encontrado(self):
        mock_sb = _mock_supabase_chain(data=[{"meta_flow_id": "flow_123", "name": "test"}])
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            flow = await service.buscar_flow("flow_123")
            assert flow is not None
            assert flow["meta_flow_id"] == "flow_123"

    @pytest.mark.asyncio
    async def test_buscar_flow_nao_encontrado(self):
        mock_sb = _mock_supabase_chain(data=[])
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            flow = await service.buscar_flow("inexistente")
            assert flow is None

    @pytest.mark.asyncio
    async def test_deprecar_flow(self):
        mock_sb = _mock_supabase_chain(data=[{"meta_access_token": "token_abc"}])
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.delete.return_value = mock_response

        with (
            patch("app.services.meta.flow_service.supabase", mock_sb),
            patch("app.services.http_client.get_http_client", return_value=mock_client),
        ):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.deprecar_flow("waba_1", "flow_123")
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_processar_resposta_flow(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.processar_resposta_flow(
                flow_token="token_1",
                response_data={"flow_type": "onboarding", "nome": "Dr Test"},
                telefone="5511999",
            )
            assert result["success"] is True
            assert result["tipo"] == "onboarding"
