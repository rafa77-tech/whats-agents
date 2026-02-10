"""
Cliente para Evolution API
Documentação: https://doc.evolution-api.com/
"""

import httpx
import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


class EvolutionClient:
    def __init__(self):
        self.base_url = settings.evolution_api_url
        self.api_key = settings.evolution_api_key
        self.instance = settings.evolution_instance
        self.headers = {"apikey": self.api_key, "Content-Type": "application/json"}

    async def send_text(self, phone: str, message: str) -> dict:
        """Envia mensagem de texto."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers=self.headers,
                json={"number": phone, "text": message},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Mensagem enviada para {phone[:8]}...")
            return result

    async def send_presence(
        self, phone: str, presence: str = "composing", delay: int = 3000
    ) -> dict:
        """
        Envia status de presenca.
        presence: 'composing' (digitando), 'recording' (gravando audio), 'available' (online)
        delay: tempo em ms para manter a presenca (obrigatorio na Evolution API)
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/sendPresence/{self.instance}",
                headers=self.headers,
                json={"number": phone, "presence": presence, "delay": delay},
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def mark_as_read(self, phone: str, message_id: str) -> dict:
        """Marca mensagem como lida."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/markMessageAsRead/{self.instance}",
                headers=self.headers,
                json={
                    "readMessages": [
                        {
                            "remoteJid": phone if "@" in phone else f"{phone}@s.whatsapp.net",
                            "id": message_id,
                        }
                    ]
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def set_webhook(self, url: str, events: Optional[list] = None) -> dict:
        """Configura webhook da instancia."""
        if events is None:
            events = ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/webhook/set/{self.instance}",
                headers=self.headers,
                json={
                    "webhook": {
                        "enabled": True,
                        "url": url,
                        "webhookByEvents": False,
                        "events": events,
                    }
                },
                timeout=10.0,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Webhook configurado: {url}")
            return result

    async def get_webhook(self) -> dict:
        """Retorna configuracao atual do webhook."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/webhook/find/{self.instance}", headers=self.headers, timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def get_connection_state(self) -> dict:
        """Retorna estado da conexao."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/instance/connectionState/{self.instance}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()


# Singleton
evolution_client = EvolutionClient()
