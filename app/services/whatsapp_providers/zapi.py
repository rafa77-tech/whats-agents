"""
Provider para Z-API.

Sprint 26 - E08: Multi-Provider Support

Implementa a interface WhatsAppProvider para Z-API (SaaS).
Docs: https://developer.z-api.io/en/
"""

import logging
from typing import Optional

import httpx

from app.services.whatsapp_providers.base import (
    WhatsAppProvider,
    ProviderType,
    MessageResult,
    ConnectionStatus,
)

logger = logging.getLogger(__name__)


class ZApiProvider(WhatsAppProvider):
    """Provider para Z-API (SaaS pago)."""

    provider_type = ProviderType.ZAPI
    BASE_URL = "https://api.z-api.io"

    def __init__(
        self,
        instance_id: str,
        token: str,
        client_token: Optional[str] = None,
    ):
        """
        Inicializa provider Z-API.

        Args:
            instance_id: ID da instância no Z-API
            token: Token da instância
            client_token: Token de segurança da conta (header Client-Token)
        """
        self.instance_id = instance_id
        self.token = token
        self.client_token = client_token
        self.timeout = 30

    @property
    def base_endpoint(self) -> str:
        """URL base para endpoints da instância."""
        return f"{self.BASE_URL}/instances/{self.instance_id}/token/{self.token}"

    @property
    def headers(self) -> dict:
        """Headers padrão para requisições."""
        headers = {"Content-Type": "application/json"}
        if self.client_token:
            headers["Client-Token"] = self.client_token
        return headers

    async def send_text(self, phone: str, message: str) -> MessageResult:
        """
        Envia mensagem de texto via Z-API.

        Docs: https://developer.z-api.io/en/message/send-message-text
        Sprint 56: Melhor captura de mensagens de erro.
        """
        phone_clean = self.format_phone(phone)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_endpoint}/send-text",
                    headers=self.headers,
                    json={
                        "phone": phone_clean,
                        "message": message,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return MessageResult(
                        success=True,
                        message_id=data.get("messageId"),
                        provider=self.provider_type.value,
                    )

                # Sprint 56: Garantir mensagem de erro descritiva
                error_text = response.text.strip() if response.text else "Resposta vazia"
                error_msg = f"HTTP {response.status_code}: {error_text}"
                logger.warning(f"[Z-API] Erro ao enviar: {error_msg}")
                return MessageResult(
                    success=False,
                    error=error_msg,
                    provider=self.provider_type.value,
                )

        except httpx.TimeoutException:
            error_msg = f"Timeout ao enviar para {phone_clean} (>{self.timeout}s)"
            logger.error(f"[Z-API] {error_msg}")
            return MessageResult(
                success=False,
                error=error_msg,
                provider=self.provider_type.value,
            )

        except httpx.ConnectError as e:
            error_msg = f"Erro de conexao com Z-API: {e}"
            logger.error(f"[Z-API] {error_msg}")
            return MessageResult(
                success=False,
                error=error_msg,
                provider=self.provider_type.value,
            )

        except Exception as e:
            error_msg = str(e) if str(e) else f"Erro desconhecido: {type(e).__name__}"
            logger.error(f"[Z-API] Exceção ao enviar texto: {error_msg}")
            return MessageResult(
                success=False,
                error=error_msg,
                provider=self.provider_type.value,
            )

    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
    ) -> MessageResult:
        """
        Envia mídia via Z-API.

        Docs: https://developer.z-api.io/en/message/send-message-image
        """
        phone_clean = self.format_phone(phone)

        # Mapear tipo de mídia para endpoint Z-API
        endpoint_map = {
            "image": "send-image",
            "document": "send-document/pdf",  # Ajustar extensão conforme necessário
            "audio": "send-audio",
            "video": "send-video",
        }
        endpoint = endpoint_map.get(media_type, "send-image")

        # Z-API usa nomes de campo diferentes por tipo
        media_field_map = {
            "image": "image",
            "document": "document",
            "audio": "audio",
            "video": "video",
        }
        media_field = media_field_map.get(media_type, "image")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "phone": phone_clean,
                    media_field: media_url,
                }
                if caption:
                    payload["caption"] = caption

                response = await client.post(
                    f"{self.base_endpoint}/{endpoint}",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code == 200:
                    data = response.json()
                    return MessageResult(
                        success=True,
                        message_id=data.get("messageId"),
                        provider=self.provider_type.value,
                    )

                # Sprint 56: Garantir mensagem de erro descritiva
                error_text = response.text.strip() if response.text else "Resposta vazia"
                error_msg = f"HTTP {response.status_code}: {error_text}"
                logger.warning(f"[Z-API] Erro ao enviar midia: {error_msg}")
                return MessageResult(
                    success=False,
                    error=error_msg,
                    provider=self.provider_type.value,
                )

        except httpx.TimeoutException:
            error_msg = f"Timeout ao enviar midia para {phone_clean} (>{self.timeout}s)"
            logger.error(f"[Z-API] {error_msg}")
            return MessageResult(
                success=False,
                error=error_msg,
                provider=self.provider_type.value,
            )

        except Exception as e:
            error_msg = str(e) if str(e) else f"Erro desconhecido: {type(e).__name__}"
            logger.error(f"[Z-API] Exceção ao enviar mídia: {error_msg}")
            return MessageResult(
                success=False,
                error=error_msg,
                provider=self.provider_type.value,
            )

    async def get_status(self) -> ConnectionStatus:
        """
        Retorna status da conexão Z-API.

        Docs: https://developer.z-api.io/en/instance/status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_endpoint}/status",
                    headers=self.headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    connected = data.get("connected", False)
                    return ConnectionStatus(
                        connected=connected,
                        state="open" if connected else "close",
                        phone_number=data.get("smartphoneConnected"),
                    )

                return ConnectionStatus(connected=False, state="error")

        except Exception as e:
            logger.error(f"[Z-API] Exceção ao verificar status: {e}")
            return ConnectionStatus(connected=False, state="error")

    async def is_connected(self) -> bool:
        """Verifica se está conectado."""
        status = await self.get_status()
        return status.connected

    async def disconnect(self) -> bool:
        """
        Desconecta a instância Z-API.

        Docs: https://developer.z-api.io/en/instance/disconnect
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_endpoint}/disconnect",
                    headers=self.headers,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"[Z-API] Exceção ao desconectar: {e}")
            return False

    async def restart(self) -> bool:
        """
        Reinicia a instância Z-API.

        Docs: https://developer.z-api.io/en/instance/restart
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_endpoint}/restart",
                    headers=self.headers,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"[Z-API] Exceção ao reiniciar: {e}")
            return False
