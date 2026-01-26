"""
Instance Manager - Sprint 40

Gerenciamento de instancias WhatsApp via Evolution API.
Permite criar novas instancias, obter QR codes, verificar conexao
e deletar instancias.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class CreateInstanceResult:
    """Resultado da criacao de instancia."""

    success: bool
    instance_name: Optional[str] = None
    chip_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class QRCodeResult:
    """Resultado da obtencao do QR code."""

    success: bool
    qr_code: Optional[str] = None
    state: str = "close"
    pairing_code: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ConnectionStateResult:
    """Resultado da verificacao de conexao."""

    success: bool
    state: str = "close"
    connected: bool = False
    error: Optional[str] = None


@dataclass
class DeleteInstanceResult:
    """Resultado da delecao de instancia."""

    success: bool
    error: Optional[str] = None


class InstanceManager:
    """
    Gerenciador de instancias WhatsApp.

    Integra com Evolution API para:
    - Criar novas instancias
    - Obter QR codes para pareamento
    - Verificar estado da conexao
    - Deletar instancias
    """

    def __init__(self):
        """Inicializa o manager com configuracoes da Evolution API."""
        self.base_url = settings.EVOLUTION_API_URL.rstrip("/")
        self.api_key = settings.EVOLUTION_API_KEY
        self.timeout = 30

    @property
    def headers(self) -> dict:
        """Headers padrao para requisicoes."""
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _gerar_instance_name(self, telefone: str) -> str:
        """
        Gera nome de instancia padronizado.

        Formato: julia_{telefone}
        Ex: julia_5511999999999
        """
        telefone_limpo = "".join(filter(str.isdigit, telefone))
        return f"julia_{telefone_limpo}"

    async def criar_instancia(
        self,
        telefone: str,
        instance_name: Optional[str] = None,
    ) -> CreateInstanceResult:
        """
        Cria uma nova instancia WhatsApp na Evolution API.

        Args:
            telefone: Numero de telefone (ex: 5511999999999)
            instance_name: Nome customizado (opcional, gera automaticamente)

        Returns:
            CreateInstanceResult com dados da instancia criada
        """
        # Gerar nome se nao fornecido
        if not instance_name:
            instance_name = self._gerar_instance_name(telefone)

        logger.info(f"[InstanceManager] Criando instancia: {instance_name}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Criar instancia na Evolution API
                response = await client.post(
                    f"{self.base_url}/instance/create",
                    headers=self.headers,
                    json={
                        "instanceName": instance_name,
                        "qrcode": True,
                        "integration": "WHATSAPP-BAILEYS",
                    },
                )

                if response.status_code not in (200, 201):
                    error_msg = f"Evolution API error: {response.status_code} - {response.text}"
                    logger.error(f"[InstanceManager] {error_msg}")
                    return CreateInstanceResult(success=False, error=error_msg)

                data = response.json()
                logger.info(f"[InstanceManager] Instancia criada: {data}")

                # Registrar chip no banco de dados
                chip_data = {
                    "telefone": telefone,
                    "instance_name": instance_name,
                    "status": "provisioned",
                    "tipo": "julia",
                    "trust_score": 50,  # Score inicial
                    "trust_level": "amarelo",
                    "fase_warmup": "setup",
                }

                result = supabase.table("chips").insert(chip_data).execute()

                if not result.data:
                    logger.error("[InstanceManager] Falha ao inserir chip no banco")
                    return CreateInstanceResult(
                        success=False,
                        instance_name=instance_name,
                        error="Falha ao registrar chip no banco",
                    )

                chip_id = result.data[0]["id"]
                logger.info(f"[InstanceManager] Chip registrado: {chip_id}")

                return CreateInstanceResult(
                    success=True,
                    instance_name=instance_name,
                    chip_id=chip_id,
                )

        except httpx.TimeoutException:
            error_msg = "Timeout ao conectar com Evolution API"
            logger.error(f"[InstanceManager] {error_msg}")
            return CreateInstanceResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Erro ao criar instancia: {str(e)}"
            logger.exception(f"[InstanceManager] {error_msg}")
            return CreateInstanceResult(success=False, error=error_msg)

    async def obter_qr_code(self, instance_name: str) -> QRCodeResult:
        """
        Obtem QR code para pareamento da instancia.

        Args:
            instance_name: Nome da instancia

        Returns:
            QRCodeResult com dados do QR code
        """
        logger.info(f"[InstanceManager] Obtendo QR code: {instance_name}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/instance/connect/{instance_name}",
                    headers=self.headers,
                )

                if response.status_code != 200:
                    error_msg = f"Evolution API error: {response.status_code}"
                    logger.warning(f"[InstanceManager] {error_msg}")
                    return QRCodeResult(success=False, error=error_msg)

                data = response.json()

                # Extrair QR code da resposta
                qr_code = data.get("base64") or data.get("qrcode", {}).get("base64")
                pairing_code = data.get("pairingCode")
                state = data.get("state", "close")

                return QRCodeResult(
                    success=True,
                    qr_code=qr_code,
                    state=state,
                    pairing_code=pairing_code,
                )

        except httpx.TimeoutException:
            error_msg = "Timeout ao conectar com Evolution API"
            logger.error(f"[InstanceManager] {error_msg}")
            return QRCodeResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Erro ao obter QR code: {str(e)}"
            logger.exception(f"[InstanceManager] {error_msg}")
            return QRCodeResult(success=False, error=error_msg)

    async def verificar_conexao(self, instance_name: str) -> ConnectionStateResult:
        """
        Verifica o estado da conexao de uma instancia.

        Args:
            instance_name: Nome da instancia

        Returns:
            ConnectionStateResult com estado da conexao
        """
        logger.debug(f"[InstanceManager] Verificando conexao: {instance_name}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/instance/connectionState/{instance_name}",
                    headers=self.headers,
                )

                if response.status_code != 200:
                    error_msg = f"Evolution API error: {response.status_code}"
                    logger.warning(f"[InstanceManager] {error_msg}")
                    return ConnectionStateResult(success=False, error=error_msg)

                data = response.json()
                state = data.get("state", "close")
                connected = state == "open"

                # Se conectou, atualizar status do chip
                if connected:
                    await self._atualizar_chip_conectado(instance_name)

                return ConnectionStateResult(
                    success=True,
                    state=state,
                    connected=connected,
                )

        except httpx.TimeoutException:
            error_msg = "Timeout ao conectar com Evolution API"
            logger.error(f"[InstanceManager] {error_msg}")
            return ConnectionStateResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Erro ao verificar conexao: {str(e)}"
            logger.exception(f"[InstanceManager] {error_msg}")
            return ConnectionStateResult(success=False, error=error_msg)

    async def _atualizar_chip_conectado(self, instance_name: str) -> None:
        """Atualiza status do chip quando conectado."""
        try:
            supabase.table("chips").update({
                "status": "warming",
                "fase_warmup": "primeiros_contatos",
            }).eq("instance_name", instance_name).execute()

            logger.info(f"[InstanceManager] Chip {instance_name} atualizado para warming")

        except Exception as e:
            logger.error(f"[InstanceManager] Erro ao atualizar chip: {e}")

    async def deletar_instancia(self, instance_name: str) -> DeleteInstanceResult:
        """
        Deleta uma instancia WhatsApp.

        Args:
            instance_name: Nome da instancia

        Returns:
            DeleteInstanceResult com resultado da operacao
        """
        logger.info(f"[InstanceManager] Deletando instancia: {instance_name}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    f"{self.base_url}/instance/delete/{instance_name}",
                    headers=self.headers,
                )

                if response.status_code not in (200, 201, 204):
                    error_msg = f"Evolution API error: {response.status_code}"
                    logger.warning(f"[InstanceManager] {error_msg}")
                    return DeleteInstanceResult(success=False, error=error_msg)

                # Atualizar status do chip no banco
                supabase.table("chips").update({
                    "status": "cancelled",
                }).eq("instance_name", instance_name).execute()

                logger.info(f"[InstanceManager] Instancia {instance_name} deletada")

                return DeleteInstanceResult(success=True)

        except httpx.TimeoutException:
            error_msg = "Timeout ao conectar com Evolution API"
            logger.error(f"[InstanceManager] {error_msg}")
            return DeleteInstanceResult(success=False, error=error_msg)

        except Exception as e:
            error_msg = f"Erro ao deletar instancia: {str(e)}"
            logger.exception(f"[InstanceManager] {error_msg}")
            return DeleteInstanceResult(success=False, error=error_msg)


# Singleton global
instance_manager = InstanceManager()
