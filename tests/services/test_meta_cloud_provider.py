"""
Testes para MetaCloudProvider.

Sprint 66 — Meta Cloud API provider.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.whatsapp_providers.meta_cloud import MetaCloudProvider
from app.services.whatsapp_providers.base import ProviderType, MessageResult


@pytest.fixture
def provider():
    """Provider Meta com credenciais de teste."""
    with patch("app.services.whatsapp_providers.meta_cloud.settings") as mock_settings:
        mock_settings.META_GRAPH_API_VERSION = "v21.0"
        return MetaCloudProvider(
            phone_number_id="123456789",
            access_token="test_token_abc",
            waba_id="waba_test",
        )


@pytest.fixture
def mock_http_client():
    """Mock do HTTP client."""
    client = AsyncMock()
    return client


class TestProviderSetup:
    """Testes de inicialização do provider."""

    def test_provider_type_is_meta(self, provider):
        assert provider.provider_type == ProviderType.META
        assert provider.provider_type.value == "meta"

    def test_messages_url(self, provider):
        assert provider.messages_url == (
            "https://graph.facebook.com/v21.0/123456789/messages"
        )

    def test_headers_contain_bearer_token(self, provider):
        headers = provider.headers
        assert headers["Authorization"] == "Bearer test_token_abc"
        assert headers["Content-Type"] == "application/json"


class TestSendText:
    """Testes para envio de texto."""

    @pytest.mark.asyncio
    async def test_send_text_sucesso(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.abc123"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "Olá!")

        assert result.success is True
        assert result.message_id == "wamid.abc123"
        assert result.provider == "meta"

        # Verificar payload
        call_kwargs = mock_http_client.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "5511999999999"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Olá!"

    @pytest.mark.asyncio
    async def test_send_text_erro_400(self, provider, mock_http_client):
        response = MagicMock()
        response.status_code = 400
        response.json.return_value = {
            "error": {"code": 131026, "message": "Outside 24h window"}
        }
        response.text = '{"error":{"code":131026}}'
        error = httpx.HTTPStatusError("400", request=MagicMock(), response=response)
        mock_http_client.post = AsyncMock(side_effect=error)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "Olá!")

        assert result.success is False
        assert "131026" in result.error
        assert result.provider == "meta"

    @pytest.mark.asyncio
    async def test_send_text_timeout(self, provider, mock_http_client):
        mock_http_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "Olá!")

        assert result.success is False
        assert result.error == "meta_timeout"

    @pytest.mark.asyncio
    async def test_send_text_connect_error(self, provider, mock_http_client):
        mock_http_client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "Olá!")

        assert result.success is False
        assert result.error == "meta_connect_error"


class TestSendTemplate:
    """Testes para envio de template."""

    @pytest.mark.asyncio
    async def test_send_template_sucesso(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "messages": [{"id": "wamid.template123"}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        components = [
            {"type": "body", "parameters": [{"type": "text", "text": "Carlos"}]}
        ]

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_template(
                "5511999999999", "julia_discovery_v1", "pt_BR", components
            )

        assert result.success is True
        assert result.message_id == "wamid.template123"

        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["type"] == "template"
        assert payload["template"]["name"] == "julia_discovery_v1"
        assert payload["template"]["language"]["code"] == "pt_BR"
        assert payload["template"]["components"] == components

    @pytest.mark.asyncio
    async def test_send_template_sem_components(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.t2"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_template(
                "5511999999999", "julia_confirmacao_v1", "pt_BR"
            )

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert "components" not in payload["template"]


class TestSendInteractive:
    """Testes para mensagens interativas."""

    @pytest.mark.asyncio
    async def test_send_interactive_buttons(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.btn1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        interactive = {
            "type": "button",
            "body": {"text": "Tem interesse?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "sim", "title": "Sim"}},
                    {"type": "reply", "reply": {"id": "nao", "title": "Não"}},
                ]
            },
        }

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_interactive("5511999999999", interactive)

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["type"] == "interactive"
        assert payload["interactive"]["type"] == "button"

    @pytest.mark.asyncio
    async def test_send_interactive_list(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.list1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        interactive = {
            "type": "list",
            "body": {"text": "Escolha uma vaga"},
            "action": {
                "button": "Ver vagas",
                "sections": [{"title": "Vagas", "rows": []}],
            },
        }

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_interactive("5511999999999", interactive)

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["interactive"]["type"] == "list"


class TestSendMedia:
    """Testes para envio de mídia."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "media_type",
        ["image", "video", "document", "audio"],
    )
    async def test_send_media_tipos(self, provider, mock_http_client, media_type):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.media1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_media(
                "5511999999999",
                "https://example.com/file.jpg",
                caption="Foto" if media_type != "audio" else None,
                media_type=media_type,
            )

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["type"] == media_type
        assert payload[media_type]["link"] == "https://example.com/file.jpg"

    @pytest.mark.asyncio
    async def test_send_media_audio_sem_caption(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.audio1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_media(
                "5511999999999",
                "https://example.com/audio.ogg",
                caption="caption ignorado",
                media_type="audio",
            )

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert "caption" not in payload["audio"]


class TestSendReaction:
    """Testes para reações."""

    @pytest.mark.asyncio
    async def test_send_reaction(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": [{"id": "wamid.react1"}]}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_reaction(
                "5511999999999", "wamid.original", "👍"
            )

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["type"] == "reaction"
        assert payload["reaction"]["message_id"] == "wamid.original"
        assert payload["reaction"]["emoji"] == "👍"


class TestMarkAsRead:
    """Testes para read receipts."""

    @pytest.mark.asyncio
    async def test_mark_as_read_sucesso(self, provider, mock_http_client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()
        mock_http_client.post = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.mark_as_read("wamid.abc123")

        assert result.success is True
        payload = mock_http_client.post.call_args.kwargs["json"]
        assert payload["status"] == "read"
        assert payload["message_id"] == "wamid.abc123"


class TestConnectionStatus:
    """Testes para status de conexão."""

    @pytest.mark.asyncio
    async def test_get_status_always_connected(self, provider):
        status = await provider.get_status()
        assert status.connected is True
        assert status.state == "open"

    @pytest.mark.asyncio
    async def test_is_connected_always_true(self, provider):
        assert await provider.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect_returns_false(self, provider):
        assert await provider.disconnect() is False


class TestErrorHandling:
    """Testes para tratamento de erros."""

    @pytest.mark.asyncio
    async def test_http_401_token_invalido(self, provider, mock_http_client):
        response = MagicMock()
        response.status_code = 401
        response.json.return_value = {
            "error": {"code": 190, "message": "Invalid OAuth access token"}
        }
        response.text = "Unauthorized"
        error = httpx.HTTPStatusError("401", request=MagicMock(), response=response)
        mock_http_client.post = AsyncMock(side_effect=error)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "test")

        assert result.success is False
        assert "190" in result.error

    @pytest.mark.asyncio
    async def test_http_429_rate_limit(self, provider, mock_http_client):
        response = MagicMock()
        response.status_code = 429
        response.json.return_value = {
            "error": {"code": 4, "message": "Rate limit exceeded"}
        }
        response.text = "Too Many Requests"
        error = httpx.HTTPStatusError("429", request=MagicMock(), response=response)
        mock_http_client.post = AsyncMock(side_effect=error)

        with patch(
            "app.services.http_client.get_http_client",
            return_value=mock_http_client,
        ):
            result = await provider.send_text("5511999999999", "test")

        assert result.success is False
        assert "meta_error_4" in result.error


class TestMessageResultExtension:
    """Testes para extensão do MessageResult."""

    def test_meta_message_status_field(self):
        result = MessageResult(
            success=True,
            message_id="wamid.123",
            provider="meta",
            meta_message_status="accepted",
        )
        assert result.meta_message_status == "accepted"

    def test_meta_message_status_default_none(self):
        result = MessageResult(success=True)
        assert result.meta_message_status is None
