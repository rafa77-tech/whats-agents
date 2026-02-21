"""
Testes de integração MM Lite com provider.

Sprint 68 — Epic 68.1, Chunk 2.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMMLiteProviderIntegration:
    """Testes de integração MM Lite com MetaCloudProvider."""

    @pytest.mark.asyncio
    async def test_send_text_sem_mm_lite(self):
        """send_text sem mm_lite não adiciona biz_opaque_callback_data."""
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_text("5511999999999", "Olá")
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert "biz_opaque_callback_data" not in payload
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_text_mm_lite_adiciona_flag(self):
        """send_text_mm_lite com mm_lite=True adiciona flag."""
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_text_mm_lite("5511999999999", "Olá", mm_lite=True)
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["biz_opaque_callback_data"] == "mm_lite"

    @pytest.mark.asyncio
    async def test_send_template_mm_lite(self):
        """send_template com mm_lite=True adiciona flag."""
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_template(
                "5511999999999", "promo_template", mm_lite=True
            )
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert payload["biz_opaque_callback_data"] == "mm_lite"

    @pytest.mark.asyncio
    async def test_send_template_sem_mm_lite(self):
        """send_template sem mm_lite não adiciona flag."""
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_template("5511999999999", "promo_template")
            call_args = mock_client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert "biz_opaque_callback_data" not in payload

    @pytest.mark.asyncio
    async def test_registrar_envio_mm_lite(self):
        """Registra envio MM Lite no banco."""
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [{"id": "metric_1", "delivery_status": "sent"}]
        mock_sb.table.return_value.insert.return_value.execute.return_value = resp

        with patch("app.services.meta.mm_lite.supabase", mock_sb):
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            result = await service.registrar_envio_mm_lite(
                chip_id="chip1", waba_id="waba1", telefone="5511999", template_name="promo"
            )
            assert result is not None
            assert result["delivery_status"] == "sent"

    @pytest.mark.asyncio
    async def test_obter_metricas_mm_lite(self):
        """Obtém métricas de MM Lite."""
        mock_sb = MagicMock()
        resp = MagicMock()
        resp.data = [
            {"delivery_status": "delivered"},
            {"delivery_status": "read"},
            {"delivery_status": "sent"},
        ]
        mock_sb.table.return_value.select.return_value.gte.return_value.execute.return_value = resp
        mock_sb.table.return_value.select.return_value.gte.return_value.eq.return_value.execute.return_value = resp

        with patch("app.services.meta.mm_lite.supabase", mock_sb):
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            result = await service.obter_metricas()
            assert result["total_sent"] == 3
            assert result["delivered"] == 2
            assert result["read"] == 1

    @pytest.mark.asyncio
    async def test_mm_lite_confirmacao_nao_usa(self):
        """Confirmações nunca usam MM Lite."""
        with patch("app.services.meta.mm_lite.settings") as mock_settings:
            mock_settings.META_MM_LITE_ENABLED = True
            from app.services.meta.mm_lite import MMLiteService

            service = MMLiteService()
            assert service.deve_usar_mm_lite({"tipo": "confirmacao"}) is False
            assert service.deve_usar_mm_lite({"tipo": "utility"}) is False
            assert service.deve_usar_mm_lite({"tipo": "authentication"}) is False
