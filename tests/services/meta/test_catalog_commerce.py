"""
Testes para Catalog Commerce Messages.

Sprint 68 — Epic 68.4, Chunk 12.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCatalogCommerceMessages:

    @pytest.mark.asyncio
    async def test_send_product(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_product(
                "5511999", "catalog_1", "vaga_abc", "Vaga disponível"
            )
            assert result.success is True
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert payload["interactive"]["type"] == "product"

    @pytest.mark.asyncio
    async def test_send_product_list(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_2"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        sections = [
            {"title": "Plantões", "product_items": [{"product_retailer_id": "vaga_1"}]}
        ]

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_product_list(
                "5511999", "catalog_1", sections, "Vagas", "Confira"
            )
            assert result.success is True
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert payload["interactive"]["type"] == "product_list"

    @pytest.mark.asyncio
    async def test_send_flow(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_3"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_flow(
                "5511999", "flow_123", "token_abc", "Header", "Body", "Abrir"
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_authentication_template(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_4"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_authentication_template(
                "5511999", "otp_template", code="123456"
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_carousel(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_5"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        cards = [{"card_index": 0, "components": []}]

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_carousel(
                "5511999", "carousel_tmpl", "Vagas", cards
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_send_product_payload_structure(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_6"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            await provider.send_product("5511999", "cat_1", "vaga_1", "Confira")
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert payload["messaging_product"] == "whatsapp"
            assert payload["type"] == "interactive"
            assert payload["interactive"]["action"]["catalog_id"] == "cat_1"

    @pytest.mark.asyncio
    async def test_send_flow_without_header(self):
        from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider

        provider = MetaCloudProvider("phone_123", "token_abc")
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "msg_7"}]}
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("app.services.http_client.get_http_client", return_value=mock_client):
            result = await provider.send_flow("5511999", "flow_1", "tok_1")
            assert result.success is True
            payload = mock_client.post.call_args.kwargs.get("json") or mock_client.post.call_args[1].get("json")
            assert "header" not in payload["interactive"]
