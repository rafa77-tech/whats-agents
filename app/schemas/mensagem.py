"""
Schema para mensagem parseada (nosso formato interno).
"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class MensagemRecebida(BaseModel):
    """Mensagem recebida e parseada do WhatsApp."""

    # Identificação
    telefone: str  # Formato: 5511999999999
    message_id: str  # ID único da mensagem
    from_me: bool  # Se foi enviada por nós

    # Conteúdo
    tipo: Literal["texto", "audio", "imagem", "documento", "video", "sticker", "outro"]
    texto: Optional[str] = None  # Texto da mensagem (se houver)

    # Metadados
    nome_contato: Optional[str] = None  # Nome salvo no WhatsApp
    timestamp: datetime

    # Flags
    is_grupo: bool = False  # Se veio de grupo
    is_status: bool = False  # Se é status/story
    is_lid: bool = False  # Se é formato LID (dispositivo vinculado)

    # Dados do Chatwoot (para resolver LID)
    chatwoot_conversation_id: Optional[int] = None
    chatwoot_inbox_id: Optional[int] = None
    remote_jid: Optional[str] = None  # JID original (para enviar resposta)
    remote_jid_alt: Optional[str] = None  # JID alternativo com telefone real (quando remoteJid é LID)


class MensagemParaEnviar(BaseModel):
    """Mensagem a ser enviada."""
    telefone: str
    texto: str
