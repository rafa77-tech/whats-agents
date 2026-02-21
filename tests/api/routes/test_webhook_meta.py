"""
Testes para Webhook Meta Cloud API.

Sprint 66 — Verificação, signature, conversão de payload, status updates.
"""

import hashlib
import hmac
import json
import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes.webhook_meta import (
    _validar_signature,
    _converter_meta_para_formato_evolution,
    _extrair_texto_mensagem,
)


# --- Helpers ---


def _make_request(headers=None, query_params=None):
    """Cria mock de FastAPI Request."""
    request = MagicMock()
    request.headers = headers or {}
    request.query_params = query_params or {}
    return request


def _sign_body(body: bytes, secret: str) -> str:
    """Gera signature HMAC SHA256."""
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# --- Tests ---


class TestVerificacaoWebhook:
    """Testes para GET /webhooks/meta (hub verification)."""

    @pytest.mark.asyncio
    async def test_verificacao_token_correto(self):
        from app.api.routes.webhook_meta import verificar_webhook

        request = _make_request(
            query_params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "challenge_abc",
            }
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_WEBHOOK_VERIFY_TOKEN = "test_verify_token"
            response = await verificar_webhook(request)

        assert response.body.decode() == "challenge_abc"
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_verificacao_token_errado(self):
        from app.api.routes.webhook_meta import verificar_webhook

        request = _make_request(
            query_params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "challenge_abc",
            }
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_WEBHOOK_VERIFY_TOKEN = "correct_token"
            response = await verificar_webhook(request)

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_verificacao_mode_errado(self):
        from app.api.routes.webhook_meta import verificar_webhook

        request = _make_request(
            query_params={
                "hub.mode": "wrong",
                "hub.verify_token": "correct_token",
                "hub.challenge": "challenge_abc",
            }
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_WEBHOOK_VERIFY_TOKEN = "correct_token"
            response = await verificar_webhook(request)

        assert response.status_code == 403


class TestSignatureValidation:
    """Testes para validação de X-Hub-Signature-256."""

    def test_signature_valida(self):
        body = b'{"test": "data"}'
        secret = "my_app_secret"
        signature = _sign_body(body, secret)

        request = _make_request(
            headers={"X-Hub-Signature-256": signature}
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_APP_SECRET = secret
            assert _validar_signature(request, body) is True

    def test_signature_invalida(self):
        body = b'{"test": "data"}'
        request = _make_request(
            headers={"X-Hub-Signature-256": "sha256=invalid_signature"}
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_APP_SECRET = "my_secret"
            assert _validar_signature(request, body) is False

    def test_sem_signature_header(self):
        body = b'{"test": "data"}'
        request = _make_request(headers={})

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_APP_SECRET = "my_secret"
            assert _validar_signature(request, body) is False

    def test_signature_sem_prefixo_sha256(self):
        body = b'{"test": "data"}'
        request = _make_request(
            headers={"X-Hub-Signature-256": "invalid_format"}
        )

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_APP_SECRET = "my_secret"
            assert _validar_signature(request, body) is False

    def test_sem_app_secret_aceita(self):
        """Em desenvolvimento sem META_APP_SECRET, aceita tudo."""
        body = b'{"test": "data"}'
        request = _make_request(headers={})

        with patch("app.api.routes.webhook_meta.settings") as mock_settings:
            mock_settings.META_APP_SECRET = ""
            assert _validar_signature(request, body) is True


class TestConversaoMetaEvolution:
    """Testes para conversão de payload Meta → Evolution."""

    def _make_chip(self):
        return {
            "id": "chip-123",
            "telefone": "5511988887777",
            "instance_name": "meta_instance",
        }

    def test_mensagem_texto(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.abc123",
            "timestamp": "1700000000",
            "type": "text",
            "text": {"body": "Olá, tudo bem?"},
        }
        contacts = [{"profile": {"name": "Dr Carlos"}}]

        result = _converter_meta_para_formato_evolution(
            message, contacts, self._make_chip()
        )

        assert result["key"]["remoteJid"] == "5511999999999@s.whatsapp.net"
        assert result["key"]["id"] == "wamid.abc123"
        assert result["key"]["fromMe"] is False
        assert result["message"]["conversation"] == "Olá, tudo bem?"
        assert result["pushName"] == "Dr Carlos"
        assert result["_provider"] == "meta"
        assert result["messageTimestamp"] == 1700000000

    def test_mensagem_imagem(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.img1",
            "timestamp": "1700000000",
            "type": "image",
            "image": {
                "id": "media_id_123",
                "caption": "Meu CRM",
                "mime_type": "image/jpeg",
            },
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["conversation"] == "Meu CRM"
        assert result["message"]["imageMessage"]["id"] == "media_id_123"

    def test_mensagem_audio(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.aud1",
            "timestamp": "1700000000",
            "type": "audio",
            "audio": {"id": "audio_id_123", "mime_type": "audio/ogg"},
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["audioMessage"]["id"] == "audio_id_123"

    def test_mensagem_documento(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.doc1",
            "timestamp": "1700000000",
            "type": "document",
            "document": {
                "id": "doc_id_123",
                "filename": "crm.pdf",
                "mime_type": "application/pdf",
            },
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["documentMessage"]["fileName"] == "crm.pdf"

    def test_mensagem_video(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.vid1",
            "timestamp": "1700000000",
            "type": "video",
            "video": {
                "id": "vid_id_123",
                "caption": "Video plantão",
                "mime_type": "video/mp4",
            },
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["videoMessage"]["id"] == "vid_id_123"
        assert result["message"]["conversation"] == "Video plantão"

    def test_mensagem_interactive_button_reply(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.btn1",
            "timestamp": "1700000000",
            "type": "interactive",
            "interactive": {
                "type": "button_reply",
                "button_reply": {"id": "sim", "title": "Sim"},
            },
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["conversation"] == "Sim"

    def test_mensagem_interactive_list_reply(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.list1",
            "timestamp": "1700000000",
            "type": "interactive",
            "interactive": {
                "type": "list_reply",
                "list_reply": {"id": "vaga1", "title": "Vaga UTI"},
            },
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["message"]["conversation"] == "Vaga UTI"

    def test_sem_contacts(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.nc1",
            "timestamp": "1700000000",
            "type": "text",
            "text": {"body": "Oi"},
        }

        result = _converter_meta_para_formato_evolution(
            message, [], self._make_chip()
        )

        assert result["pushName"] == ""

    def test_metadados_meta(self):
        message = {
            "from": "5511999999999",
            "id": "wamid.meta1",
            "timestamp": "1700000000",
            "type": "text",
            "text": {"body": "test"},
        }
        chip = self._make_chip()

        result = _converter_meta_para_formato_evolution(message, [], chip)

        assert result["_meta_chip_id"] == "chip-123"
        assert result["_meta_telefone"] == "5511988887777"
        assert result["_provider"] == "meta"


class TestExtrairTextoMensagem:
    """Testes para extração de texto de diferentes tipos."""

    def test_texto(self):
        msg = {"type": "text", "text": {"body": "Olá"}}
        assert _extrair_texto_mensagem(msg) == "Olá"

    def test_imagem_com_caption(self):
        msg = {"type": "image", "image": {"caption": "Foto do CRM"}}
        assert _extrair_texto_mensagem(msg) == "Foto do CRM"

    def test_imagem_sem_caption(self):
        msg = {"type": "image", "image": {}}
        assert _extrair_texto_mensagem(msg) == "[imagem]"

    def test_audio(self):
        msg = {"type": "audio", "audio": {}}
        assert _extrair_texto_mensagem(msg) == "[audio]"

    def test_reaction(self):
        msg = {"type": "reaction", "reaction": {"emoji": "👍"}}
        assert _extrair_texto_mensagem(msg) == "👍"

    def test_tipo_desconhecido(self):
        msg = {"type": "sticker"}
        assert _extrair_texto_mensagem(msg) == "[sticker]"


class TestDeliveryStatusMeta:
    """Testes para normalização de status Meta no delivery_status."""

    def test_meta_sent(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("SENT") == "sent"

    def test_meta_accepted(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("ACCEPTED") == "sent"

    def test_meta_delivered(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("DELIVERED") == "delivered"

    def test_meta_read(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("READ") == "read"

    def test_meta_failed(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("FAILED") == "failed"

    def test_evolution_delivery_ack_nao_afetado(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("DELIVERY_ACK") == "delivered"

    def test_zapi_played_nao_afetado(self):
        from app.services.delivery_status import _normalizar_status

        assert _normalizar_status("PLAYED") == "read"
