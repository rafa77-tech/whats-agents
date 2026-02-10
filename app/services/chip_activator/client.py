"""
Cliente para API de Ativacao de Chips (VPS).

Sprint 27 - E05

Este modulo permite chamar a API de ativacao automatizada
que roda no VPS DigitalOcean.
"""

import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class ChipActivatorError(Exception):
    """Erro ao interagir com API de ativacao."""

    pass


class ChipActivatorClient:
    """Cliente para API de Ativacao de Chips."""

    def __init__(self):
        self.base_url = (
            settings.CHIP_ACTIVATOR_URL.rstrip("/") if settings.CHIP_ACTIVATOR_URL else ""
        )
        self.api_key = settings.CHIP_ACTIVATOR_API_KEY
        self.timeout = 30  # Timeout para chamadas individuais

    @property
    def headers(self) -> dict:
        """Headers padrao para requisicoes."""
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @property
    def is_configured(self) -> bool:
        """Verifica se o cliente esta configurado."""
        return bool(self.base_url and self.api_key)

    async def health_check(self) -> dict:
        """
        Verifica status da API de ativacao.

        Returns:
            Status da API (healthy, degraded, unreachable)
        """
        if not self.base_url:
            return {"status": "not_configured", "error": "CHIP_ACTIVATOR_URL nao configurado"}

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=10,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"[ChipActivator] Health check HTTP error: {e.response.status_code}")
            return {"status": "error", "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"[ChipActivator] Health check falhou: {e}")
            return {"status": "unreachable", "error": str(e)}

    async def adicionar_ativacao(
        self,
        phone_number: str,
        country_code: str = "55",
        callback_url: Optional[str] = None,
    ) -> dict:
        """
        Adiciona um chip a fila de ativacao.

        Args:
            phone_number: Numero de telefone (sem +55)
            country_code: Codigo do pais (default: 55)
            callback_url: URL para callback quando ativacao completar (opcional)

        Returns:
            {
                "id": str,
                "status": "queued",
                "message": str,
                "position": int
            }

        Raises:
            ChipActivatorError: Se falhar ao chamar API
        """
        if not self.is_configured:
            raise ChipActivatorError("CHIP_ACTIVATOR_URL ou CHIP_ACTIVATOR_API_KEY nao configurado")

        # Limpar numero
        phone_clean = "".join(filter(str.isdigit, phone_number))

        logger.info(f"[ChipActivator] Adicionando ativacao: {phone_clean[:6]}****")

        payload = {
            "phone_number": phone_clean,
            "country_code": country_code,
        }
        if callback_url:
            payload["callback_url"] = callback_url

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.base_url}/activate",
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                )

                if response.status_code == 503:
                    raise ChipActivatorError("Fila de ativacao cheia. Tentar novamente depois.")

                response.raise_for_status()
                data = response.json()

                logger.info(f"[ChipActivator] Chip adicionado a fila: {data.get('id')}")
                return data

        except httpx.HTTPStatusError as e:
            logger.error(
                f"[ChipActivator] HTTP Error: {e.response.status_code} - {e.response.text}"
            )
            raise ChipActivatorError(f"Erro HTTP: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[ChipActivator] Request Error: {e}")
            raise ChipActivatorError(f"Erro de conexao: {e}")

    async def enviar_codigo_sms(self, activation_id: str, code: str) -> dict:
        """
        Envia codigo SMS para uma ativacao em andamento.

        Args:
            activation_id: ID da ativacao
            code: Codigo SMS recebido

        Returns:
            {"message": "Codigo SMS registrado", "activation_id": str}

        Raises:
            ChipActivatorError: Se falhar
        """
        if not self.is_configured:
            raise ChipActivatorError("CHIP_ACTIVATOR_URL ou CHIP_ACTIVATOR_API_KEY nao configurado")

        logger.info(f"[ChipActivator] Enviando codigo SMS para: {activation_id}")

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{self.base_url}/activate/{activation_id}/sms",
                    json={"code": code},
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"[ChipActivator] Erro ao enviar SMS: {e.response.status_code}")
            raise ChipActivatorError(f"Erro HTTP: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[ChipActivator] Request Error: {e}")
            raise ChipActivatorError(f"Erro de conexao: {e}")

    async def verificar_status(self, activation_id: str) -> dict:
        """
        Verifica status de uma ativacao.

        Args:
            activation_id: ID da ativacao

        Returns:
            {
                "id": str,
                "status": "queued" | "running" | "waiting_sms" | "success" | "failed",
                "message": str,
                "step": str (opcional),
                "error": str (opcional)
            }

        Raises:
            ChipActivatorError: Se falhar
        """
        if not self.is_configured:
            raise ChipActivatorError("CHIP_ACTIVATOR_URL ou CHIP_ACTIVATOR_API_KEY nao configurado")

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.base_url}/activate/{activation_id}",
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ChipActivatorError(f"Ativacao nao encontrada: {activation_id}")
            logger.error(f"[ChipActivator] Erro ao verificar status: {e.response.status_code}")
            raise ChipActivatorError(f"Erro HTTP: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"[ChipActivator] Request Error: {e}")
            raise ChipActivatorError(f"Erro de conexao: {e}")

    async def aguardar_ativacao(
        self,
        activation_id: str,
        timeout_seconds: int = 600,
        poll_interval: int = 10,
    ) -> dict:
        """
        Aguarda conclusao de uma ativacao (polling).

        Args:
            activation_id: ID da ativacao
            timeout_seconds: Tempo maximo de espera (default: 10 min)
            poll_interval: Intervalo entre verificacoes (default: 10s)

        Returns:
            Resultado final da ativacao
        """
        elapsed = 0

        while elapsed < timeout_seconds:
            try:
                status = await self.verificar_status(activation_id)
                current_status = status.get("status")

                if current_status == "success":
                    logger.info(f"[ChipActivator] Ativacao concluida: {activation_id}")
                    return {
                        "success": True,
                        "activation_id": activation_id,
                        "message": status.get("message", "Chip ativado com sucesso"),
                    }

                elif current_status == "failed":
                    logger.warning(f"[ChipActivator] Ativacao falhou: {activation_id}")
                    return {
                        "success": False,
                        "activation_id": activation_id,
                        "message": status.get("message", "Falha na ativacao"),
                        "error": status.get("error"),
                        "step": status.get("step"),
                    }

                elif current_status in ("queued", "running", "waiting_sms"):
                    logger.debug(f"[ChipActivator] Status: {current_status}, aguardando...")

            except ChipActivatorError as e:
                logger.warning(f"[ChipActivator] Erro no polling: {e}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout
        logger.error(f"[ChipActivator] Timeout aguardando ativacao: {activation_id}")
        return {
            "success": False,
            "activation_id": activation_id,
            "message": "Timeout aguardando ativacao",
        }

    async def verificar_fila(self) -> dict:
        """
        Verifica status da fila de ativacao.

        Returns:
            {
                "pending": int,
                "processing": int,
                "completed": int,
                "failed": int,
                "current_activation_id": str | None
            }
        """
        if not self.is_configured:
            return {"error": "CHIP_ACTIVATOR_URL nao configurado"}

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.base_url}/queue",
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[ChipActivator] Erro ao verificar fila: {e}")
            return {"error": str(e)}

    async def obter_metricas(self) -> dict:
        """
        Obtem metricas do servico de ativacao.

        Returns:
            {
                "uptime_seconds": int,
                "total_activations": int,
                "successful_activations": int,
                "failed_activations": int,
                "success_rate": float,
                "queue_size": int
            }
        """
        if not self.is_configured:
            return {"error": "CHIP_ACTIVATOR_URL nao configurado"}

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.base_url}/metrics",
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"[ChipActivator] Erro ao obter metricas: {e}")
            return {"error": str(e)}


# Singleton
chip_activator_client = ChipActivatorClient()
