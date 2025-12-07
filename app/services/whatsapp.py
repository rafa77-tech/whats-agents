"""
Cliente Evolution API para WhatsApp.
"""
import httpx
from typing import Literal, Tuple
import logging

from app.core.config import settings
from app.services.circuit_breaker import circuit_evolution, CircuitOpenError
from app.services.rate_limiter import pode_enviar, registrar_envio, calcular_delay_humanizado

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Exceção quando rate limit é atingido."""
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(f"Rate limit: {motivo}")


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

    async def _fazer_request(
        self,
        method: str,
        url: str,
        payload: dict = None,
        timeout: float = 30.0
    ) -> dict:
        """
        Faz request HTTP com proteção do circuit breaker.
        """
        async def _request():
            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(
                        url, json=payload, headers=self.headers, timeout=timeout
                    )
                else:
                    response = await client.get(
                        url, headers=self.headers, timeout=timeout
                    )
                response.raise_for_status()
                return response.json()

        return await circuit_evolution.executar(_request)

    async def enviar_mensagem(
        self,
        telefone: str,
        texto: str,
        verificar_rate_limit: bool = True
    ) -> dict:
        """
        Envia mensagem de texto para um numero.

        Args:
            telefone: Numero no formato 5511999999999
            texto: Texto da mensagem
            verificar_rate_limit: Se True, verifica rate limiting antes de enviar

        Returns:
            Resposta da API

        Raises:
            RateLimitError: Se rate limit foi atingido
            CircuitOpenError: Se circuit breaker está aberto
        """
        # Verificar rate limiting (apenas para mensagens proativas)
        if verificar_rate_limit:
            ok, motivo = await pode_enviar(telefone)
            if not ok:
                logger.warning(f"Rate limit para {telefone[:8]}...: {motivo}")
                raise RateLimitError(motivo)

        url = f"{self.base_url}/message/sendText/{self.instance}"
        payload = {
            "number": telefone,
            "text": texto,
        }

        result = await self._fazer_request("POST", url, payload, timeout=30.0)
        logger.info(f"Mensagem enviada para {telefone[:8]}...")

        # Registrar envio no rate limiter
        await registrar_envio(telefone)

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

        return await self._fazer_request("POST", url, payload, timeout=10.0)

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

        return await self._fazer_request("POST", url, payload, timeout=10.0)

    async def verificar_conexao(self) -> dict:
        """Verifica status da conexao WhatsApp."""
        url = f"{self.base_url}/instance/connectionState/{self.instance}"
        return await self._fazer_request("GET", url, timeout=10.0)

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

        result = await self._fazer_request("POST", webhook_url, payload, timeout=10.0)
        logger.info(f"Webhook configurado: {url}")
        return result


# Instancia global
evolution = EvolutionClient()


# Funcoes de conveniencia
async def enviar_whatsapp(
    telefone: str,
    texto: str,
    verificar_rate_limit: bool = True
) -> dict:
    """
    Funcao de conveniencia para enviar mensagem.

    Args:
        telefone: Número do destinatário
        texto: Texto da mensagem
        verificar_rate_limit: Se True, verifica rate limit antes de enviar

    Raises:
        RateLimitError: Se rate limit foi atingido
        CircuitOpenError: Se Evolution API está indisponível
    """
    return await evolution.enviar_mensagem(telefone, texto, verificar_rate_limit)


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


async def enviar_com_digitacao(
    telefone: str,
    texto: str,
    tempo_digitacao: float = None
) -> dict:
    """
    Envia mensagem com simulação de digitação.

    1. Mostra "composing" (digitando)
    2. Aguarda tempo proporcional
    3. Envia mensagem

    Args:
        telefone: Número do destinatário
        texto: Texto da mensagem
        tempo_digitacao: Tempo de digitação em segundos (opcional, calcula automaticamente)

    Returns:
        Resultado do envio
    """
    import asyncio
    from app.services.timing import calcular_tempo_digitacao

    tempo = tempo_digitacao or calcular_tempo_digitacao(texto)

    # Iniciar "digitando"
    await mostrar_digitando(telefone)

    # Aguardar tempo de digitação
    await asyncio.sleep(tempo)

    # Enviar mensagem
    return await evolution.enviar_mensagem(
        telefone=telefone,
        texto=texto,
        verificar_rate_limit=False  # Respostas não contam no rate limit
    )