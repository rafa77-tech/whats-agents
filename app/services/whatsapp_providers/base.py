"""
Interface abstrata para providers WhatsApp.

Sprint 26 - E08: Multi-Provider Support

Define contrato que todos os providers devem implementar,
permitindo trocar entre Evolution API, Z-API, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ProviderType(str, Enum):
    """Tipos de providers suportados."""

    EVOLUTION = "evolution"
    ZAPI = "z-api"
    META = "meta"


@dataclass
class MessageResult:
    """Resultado do envio de mensagem."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    provider: Optional[str] = None
    meta_message_status: Optional[str] = None


@dataclass
class ConnectionStatus:
    """Status de conexão da instância."""

    connected: bool
    state: str  # 'open', 'close', 'connecting', 'error'
    qr_code: Optional[str] = None
    phone_number: Optional[str] = None


class WhatsAppProvider(ABC):
    """
    Interface abstrata para providers WhatsApp.

    Todos os providers (Evolution, Z-API, etc) devem implementar
    esta interface para garantir compatibilidade com o sistema.
    """

    provider_type: ProviderType

    @abstractmethod
    async def send_text(self, phone: str, message: str) -> MessageResult:
        """
        Envia mensagem de texto.

        Args:
            phone: Número do destinatário (formato: 5511999999999)
            message: Texto da mensagem

        Returns:
            MessageResult com status do envio
        """
        pass

    @abstractmethod
    async def send_media(
        self,
        phone: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
    ) -> MessageResult:
        """
        Envia mídia (imagem, documento, áudio, vídeo).

        Args:
            phone: Número do destinatário
            media_url: URL da mídia
            caption: Legenda (opcional)
            media_type: Tipo de mídia (image, document, audio, video)

        Returns:
            MessageResult com status do envio
        """
        pass

    @abstractmethod
    async def get_status(self) -> ConnectionStatus:
        """
        Retorna status da conexão.

        Returns:
            ConnectionStatus com informações da instância
        """
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Verifica se está conectado ao WhatsApp.

        Returns:
            True se conectado
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Desconecta a instância do WhatsApp.

        Returns:
            True se desconectou com sucesso
        """
        pass

    def format_phone(self, phone: str) -> str:
        """
        Formata número de telefone removendo caracteres especiais.

        Args:
            phone: Número em qualquer formato

        Returns:
            Número apenas com dígitos (ex: 5511999999999)
        """
        return "".join(filter(str.isdigit, phone))
