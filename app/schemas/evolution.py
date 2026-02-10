"""
Schemas para payloads da Evolution API.
"""

from pydantic import BaseModel
from typing import Optional, Any


class MessageKey(BaseModel):
    """Identificador da mensagem."""

    remoteJid: str  # Número do remetente (5511999999999@s.whatsapp.net)
    fromMe: bool  # Se foi enviada por nós
    id: str  # ID único da mensagem


class MessageContent(BaseModel):
    """Conteúdo da mensagem."""

    conversation: Optional[str] = None  # Texto simples
    extendedTextMessage: Optional[dict] = None  # Texto com preview
    imageMessage: Optional[dict] = None
    audioMessage: Optional[dict] = None
    documentMessage: Optional[dict] = None
    # Adicionar outros tipos conforme necessário


class MessageData(BaseModel):
    """Dados da mensagem recebida."""

    key: MessageKey
    message: Optional[MessageContent] = None
    messageTimestamp: Optional[int] = None
    pushName: Optional[str] = None  # Nome do contato


class EvolutionWebhookPayload(BaseModel):
    """Payload completo do webhook Evolution."""

    event: str  # Tipo de evento (messages.upsert, connection.update, etc)
    instance: str  # Nome da instância (Revoluna)
    data: Any  # Dados variam por tipo de evento


class ConnectionUpdate(BaseModel):
    """Dados de atualização de conexão."""

    state: str  # open, close, connecting
    statusReason: Optional[int] = None
