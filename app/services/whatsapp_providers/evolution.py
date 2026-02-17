"""
Provider para Evolution API.

Sprint 26 - E08: Multi-Provider Support

Adapta a Evolution API existente para a interface WhatsAppProvider.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.http_client import get_http_client
from app.services.whatsapp_providers.base import (
    WhatsAppProvider,
    ProviderType,
    MessageResult,
    ConnectionStatus,
)

logger = logging.getLogger(__name__)


class EvolutionProvider(WhatsAppProvider):
    """Provider para Evolution API (self-hosted)."""

    provider_type = ProviderType.EVOLUTION

    def __init__(self, instance_name: str):
        """
        Inicializa provider Evolution.

        Args:
            instance_name: Nome da instância no Evolution
        """
        self.instance_name = instance_name
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.timeout = 30

    @property
    def headers(self) -> dict:
        """Headers padrão para requisições."""
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_text(self, phone: str, message: str) -> MessageResult:
        """Envia mensagem de texto via Evolution API."""
        phone_clean = self.format_phone(phone)

        try:
            client = await get_http_client()
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance_name}",
                headers=self.headers,
                json={
                    "number": phone_clean,
                    "text": message,
                },
                timeout=self.timeout,
            )

            if response.status_code in (200, 201):
                data = response.json()
                message_id = data.get("key", {}).get("id")
                return MessageResult(
                    success=True,
                    message_id=message_id,
                    provider=self.provider_type.value,
                )

            logger.warning(f"[Evolution] Erro ao enviar: {response.status_code} - {response.text}")
            return MessageResult(
                success=False,
                error=f"HTTP {response.status_code}: {response.text}",
                provider=self.provider_type.value,
            )

        except Exception as e:
            logger.error(f"[Evolution] Exceção ao enviar texto: {e}")
            return MessageResult(
                success=False,
                error=str(e),
                provider=self.provider_type.value,
            )

    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
    ) -> MessageResult:
        """Envia mídia via Evolution API."""
        phone_clean = self.format_phone(phone)

        # Mapear tipo de mídia para endpoint Evolution
        endpoint_map = {
            "image": "sendMedia",
            "document": "sendMedia",
            "audio": "sendWhatsAppAudio",
            "video": "sendMedia",
        }
        endpoint = endpoint_map.get(media_type, "sendMedia")

        try:
            client = await get_http_client()
            payload = {
                "number": phone_clean,
                "mediatype": media_type,
                "media": media_url,
            }
            if caption:
                payload["caption"] = caption

            response = await client.post(
                f"{self.base_url}/message/{endpoint}/{self.instance_name}",
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code in (200, 201):
                data = response.json()
                message_id = data.get("key", {}).get("id")
                return MessageResult(
                    success=True,
                    message_id=message_id,
                    provider=self.provider_type.value,
                )

            return MessageResult(
                success=False,
                error=f"HTTP {response.status_code}: {response.text}",
                provider=self.provider_type.value,
            )

        except Exception as e:
            logger.error(f"[Evolution] Exceção ao enviar mídia: {e}")
            return MessageResult(
                success=False,
                error=str(e),
                provider=self.provider_type.value,
            )

    async def get_status(self) -> ConnectionStatus:
        """Retorna status da conexão Evolution."""
        try:
            client = await get_http_client()
            response = await client.get(
                f"{self.base_url}/instance/connectionState/{self.instance_name}",
                headers=self.headers,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                state = data.get("state", "close")
                return ConnectionStatus(
                    connected=(state == "open"),
                    state=state,
                    qr_code=data.get("qrcode"),
                )

            return ConnectionStatus(connected=False, state="error")

        except Exception as e:
            logger.error(f"[Evolution] Exceção ao verificar status: {e}")
            return ConnectionStatus(connected=False, state="error")

    async def is_connected(self) -> bool:
        """Verifica se está conectado."""
        status = await self.get_status()
        return status.connected

    async def disconnect(self) -> bool:
        """Desconecta a instância."""
        try:
            client = await get_http_client()
            response = await client.delete(
                f"{self.base_url}/instance/logout/{self.instance_name}",
                headers=self.headers,
                timeout=self.timeout,
            )
            return response.status_code in (200, 201)

        except Exception as e:
            logger.error(f"[Evolution] Exceção ao desconectar: {e}")
            return False
