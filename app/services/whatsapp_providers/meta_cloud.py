"""
MetaCloudProvider — Provider para Meta WhatsApp Cloud API.

Sprint 66 — Integração com API oficial da Meta via Graph API.

Segue o padrão exato de EvolutionProvider e ZApiProvider.
"""

import logging
from typing import Optional, List

from app.services.whatsapp_providers.base import (
    WhatsAppProvider,
    ProviderType,
    MessageResult,
    ConnectionStatus,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base URL do Graph API (sem trailing slash)
_GRAPH_API_BASE = "https://graph.facebook.com"


class MetaCloudProvider(WhatsAppProvider):
    """
    Provider para Meta WhatsApp Cloud API.

    Usa Graph API para enviar mensagens via número registrado na WABA.
    Credenciais são por chip (phone_number_id, access_token, waba_id).
    """

    provider_type = ProviderType.META

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        waba_id: Optional[str] = None,
    ):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.waba_id = waba_id
        self.api_version = settings.META_GRAPH_API_VERSION or "v21.0"
        self.base_url = f"{_GRAPH_API_BASE}/{self.api_version}"
        self.timeout = 30

    @property
    def messages_url(self) -> str:
        """URL para envio de mensagens."""
        return f"{self.base_url}/{self.phone_number_id}/messages"

    @property
    def headers(self) -> dict:
        """Headers de autenticação."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _post_message(self, payload: dict) -> MessageResult:
        """
        Envia payload para o endpoint de mensagens.

        Args:
            payload: Corpo da requisição

        Returns:
            MessageResult com resultado do envio
        """
        from app.services.http_client import get_http_client

        try:
            client = await get_http_client()
            response = await client.post(
                self.messages_url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            message_id = None
            if data.get("messages"):
                message_id = data["messages"][0].get("id")

            return MessageResult(
                success=True,
                message_id=message_id,
                provider="meta",
                meta_message_status="accepted",
            )

        except Exception as e:
            error_msg = self._extract_error(e)
            logger.warning(
                f"[MetaCloud] Erro ao enviar para {self.phone_number_id}: {error_msg}"
            )
            return MessageResult(
                success=False,
                error=error_msg,
                provider="meta",
            )

    def _extract_error(self, exc: Exception) -> str:
        """Extrai mensagem de erro de exceções httpx."""
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            try:
                data = exc.response.json()
                error = data.get("error", {})
                code = error.get("code", "unknown")
                msg = error.get("message", str(exc))
                return f"meta_error_{code}: {msg}"
            except Exception:
                return f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        if isinstance(exc, httpx.TimeoutException):
            return "meta_timeout"
        if isinstance(exc, httpx.ConnectError):
            return "meta_connect_error"
        return str(exc)

    async def send_text(self, phone: str, message: str) -> MessageResult:
        """
        Envia mensagem de texto.

        Args:
            phone: Número do destinatário (ex: 5511999999999)
            message: Texto da mensagem

        Returns:
            MessageResult com status do envio
        """
        phone_clean = self.format_phone(phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_clean,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }
        return await self._post_message(payload)

    async def send_template(
        self,
        phone: str,
        template_name: str,
        language: str = "pt_BR",
        components: Optional[List[dict]] = None,
    ) -> MessageResult:
        """
        Envia mensagem de template.

        Args:
            phone: Número do destinatário
            template_name: Nome do template aprovado
            language: Código do idioma (default: pt_BR)
            components: Componentes do template (parâmetros)

        Returns:
            MessageResult com status do envio
        """
        phone_clean = self.format_phone(phone)
        template_obj = {
            "name": template_name,
            "language": {"code": language},
        }
        if components:
            template_obj["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_clean,
            "type": "template",
            "template": template_obj,
        }
        return await self._post_message(payload)

    async def send_interactive(
        self,
        phone: str,
        interactive: dict,
    ) -> MessageResult:
        """
        Envia mensagem interativa (botões ou lista).

        Args:
            phone: Número do destinatário
            interactive: Objeto interactive (type=button ou type=list)

        Returns:
            MessageResult com status do envio
        """
        phone_clean = self.format_phone(phone)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_clean,
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._post_message(payload)

    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
    ) -> MessageResult:
        """
        Envia mídia (imagem, vídeo, documento, áudio).

        Args:
            phone: Número do destinatário
            media_url: URL da mídia
            caption: Legenda (não suportado para audio/sticker)
            media_type: Tipo (image, video, document, audio, sticker)

        Returns:
            MessageResult com status do envio
        """
        phone_clean = self.format_phone(phone)
        media_obj: dict = {"link": media_url}
        if caption and media_type in ("image", "video", "document"):
            media_obj["caption"] = caption

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_clean,
            "type": media_type,
            media_type: media_obj,
        }
        return await self._post_message(payload)

    async def send_reaction(
        self,
        phone: str,
        message_id: str,
        emoji: str,
    ) -> MessageResult:
        """
        Envia reação a uma mensagem.

        Args:
            phone: Número do destinatário
            message_id: ID da mensagem a reagir
            emoji: Emoji da reação

        Returns:
            MessageResult com status do envio
        """
        phone_clean = self.format_phone(phone)
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_clean,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji,
            },
        }
        return await self._post_message(payload)

    async def mark_as_read(self, message_id: str) -> MessageResult:
        """
        Marca mensagem como lida (read receipt).

        Args:
            message_id: ID da mensagem (wamid.XXX)

        Returns:
            MessageResult com status
        """
        from app.services.http_client import get_http_client

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            client = await get_http_client()
            response = await client.post(
                self.messages_url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return MessageResult(success=True, provider="meta")
        except Exception as e:
            return MessageResult(success=False, error=str(e), provider="meta")

    async def get_status(self) -> ConnectionStatus:
        """
        Retorna status de conexão.

        Meta Cloud API está sempre "conectada" — não depende de sessão WhatsApp Web.
        """
        return ConnectionStatus(
            connected=True,
            state="open",
            phone_number=self.phone_number_id,
        )

    async def is_connected(self) -> bool:
        """Meta Cloud API está sempre conectada."""
        return True

    async def disconnect(self) -> bool:
        """Meta Cloud API não tem conceito de desconexão."""
        return False
