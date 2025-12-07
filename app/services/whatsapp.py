"""
Cliente Evolution API para WhatsApp.
"""
import httpx
from typing import Literal
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EvolutionClient:
    """Cliente para Evolution API."""

    def __init__(self):
        self.base_url = settings.EVOLUTION_API_URL
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance = settings.EVOLUTION_INSTANCE

        if not self.api_key:
            raise ValueError("EVOLUTION_API_KEY e obrigatorio")

    @property
    def headers(self) -> dict:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    async def enviar_mensagem(self, telefone: str, texto: str) -> dict:
        """
        Envia mensagem de texto para um numero.

        Args:
            telefone: Numero no formato 5511999999999
            texto: Texto da mensagem

        Returns:
            Resposta da API
        """
        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": telefone,
            "text": texto,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Mensagem enviada para {telefone[:8]}...")
            return result

    async def enviar_presenca(
        self,
        telefone: str,
        presenca: Literal["available", "composing", "recording", "paused"],
        delay: int = 3000
    ) -> dict:
        """
        Envia status de presenca (online, digitando, etc).

        Args:
            telefone: Numero do destinatario
            presenca: Tipo de presenca
            delay: Tempo em ms para manter a presenca
        """
        url = f"{self.base_url}/chat/sendPresence/{self.instance}"
        payload = {
            "number": telefone,
            "presence": presenca,
            "delay": delay,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def marcar_como_lida(self, telefone: str, message_id: str, from_me: bool = False) -> dict:
        """Marca mensagem como lida."""
        url = f"{self.base_url}/chat/markMessageAsRead/{self.instance}"
        payload = {
            "readMessages": [
                {
                    "remoteJid": telefone if "@" in telefone else f"{telefone}@s.whatsapp.net",
                    "fromMe": from_me,
                    "id": message_id
                }
            ]
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def verificar_conexao(self) -> dict:
        """Verifica status da conexao WhatsApp."""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            return response.json()

    async def set_webhook(self, url: str, events: list = None) -> dict:
        """Configura webhook da instancia."""
        if events is None:
            events = ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]

        webhook_url = f"{self.base_url}/webhook/set/{self.instance}"
        payload = {
            "webhook": {
                "enabled": True,
                "url": url,
                "webhookByEvents": False,
                "events": events
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Webhook configurado: {url}")
            return response.json()


# Instancia global
evolution = EvolutionClient()


# Funcoes de conveniencia
async def enviar_whatsapp(telefone: str, texto: str) -> dict:
    """Funcao de conveniencia para enviar mensagem."""
    return await evolution.enviar_mensagem(telefone, texto)


async def mostrar_digitando(telefone: str) -> dict:
    """Mostra 'digitando...' para o contato."""
    return await evolution.enviar_presenca(telefone, "composing")


async def mostrar_online(telefone: str) -> dict:
    """Mostra status online para o contato."""
    return await evolution.enviar_presenca(telefone, "available")


async def manter_digitando(telefone: str, duracao_max: int = 30):
    """
    Mantém status 'digitando' por até X segundos.
    Útil enquanto aguarda resposta do LLM.
    """
    import asyncio
    inicio = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - inicio < duracao_max:
        await mostrar_digitando(telefone)
        await asyncio.sleep(5)  # Reenviar a cada 5s
