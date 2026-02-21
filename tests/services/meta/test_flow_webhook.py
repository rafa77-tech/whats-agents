"""
Testes para Flow webhook handler (decrypt + process).

Sprint 68 — Epic 68.2, Chunk 6.
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
    mock.eq.return_value = mock
    mock.execute.return_value = resp
    return mock


class TestFlowWebhookHandler:

    @pytest.mark.asyncio
    async def test_decriptar_resposta_sem_chave(self):
        """Sem chave privada, retorna dados raw."""
        with patch("app.services.meta.flow_service.settings") as mock_settings:
            mock_settings.META_FLOW_PRIVATE_KEY = ""
            mock_settings.META_GRAPH_API_VERSION = "v21.0"
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            data = {"campo": "valor"}
            result = await service.decriptar_resposta_flow(data)
            assert result == data

    @pytest.mark.asyncio
    async def test_decriptar_resposta_com_dados_encrypted(self):
        """Com dados encrypted mas sem chave, retorna raw."""
        with patch("app.services.meta.flow_service.settings") as mock_settings:
            mock_settings.META_FLOW_PRIVATE_KEY = ""
            mock_settings.META_GRAPH_API_VERSION = "v21.0"
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            data = {"encrypted_flow_data": "abc123encrypted"}
            result = await service.decriptar_resposta_flow(data)
            assert result == data

    @pytest.mark.asyncio
    async def test_processar_resposta_onboarding(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.processar_resposta_flow(
                flow_token="tok_1",
                response_data={"flow_type": "onboarding"},
                telefone="5511999",
            )
            assert result["tipo"] == "onboarding"
            assert result["processado"] is True

    @pytest.mark.asyncio
    async def test_processar_resposta_confirmacao(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.processar_resposta_flow(
                flow_token="tok_2",
                response_data={"flow_type": "confirmacao"},
                telefone="5511888",
            )
            assert result["tipo"] == "confirmacao"

    @pytest.mark.asyncio
    async def test_processar_resposta_avaliacao(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.processar_resposta_flow(
                flow_token="tok_3",
                response_data={"flow_type": "avaliacao"},
                telefone="5511777",
            )
            assert result["tipo"] == "avaliacao"

    @pytest.mark.asyncio
    async def test_processar_resposta_tipo_desconhecido(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            result = await service.processar_resposta_flow(
                flow_token="tok_4",
                response_data={"flow_type": "custom_tipo"},
                telefone="5511666",
            )
            assert result["tipo"] == "unknown"
            assert result["processado"] is False

    @pytest.mark.asyncio
    async def test_processar_resposta_salva_no_banco(self):
        mock_sb = _mock_supabase_chain()
        with patch("app.services.meta.flow_service.supabase", mock_sb):
            from app.services.meta.flow_service import MetaFlowService

            service = MetaFlowService()
            await service.processar_resposta_flow(
                flow_token="tok_5",
                response_data={"flow_type": "onboarding"},
                telefone="5511555",
            )
            mock_sb.table.assert_any_call("meta_flow_responses")
