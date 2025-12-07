"""
Parser de mensagens da Evolution API.
"""
from datetime import datetime
from typing import Optional
import logging

from app.schemas.mensagem import MensagemRecebida

logger = logging.getLogger(__name__)


def extrair_telefone(jid: str) -> str:
    """
    Extrai número de telefone do JID do WhatsApp.

    Exemplo:
        "5511999999999@s.whatsapp.net" -> "5511999999999"
        "5511999999999-123456@g.us" -> "5511999999999" (grupo)
    """
    if not jid:
        return ""

    # Remover sufixo
    telefone = jid.split("@")[0]

    # Se for grupo, pegar só o primeiro número
    if "-" in telefone:
        telefone = telefone.split("-")[0]

    return telefone


def is_grupo(jid: str) -> bool:
    """Verifica se JID é de grupo."""
    return "@g.us" in jid if jid else False


def is_status(jid: str) -> bool:
    """Verifica se é status/story."""
    return "status@broadcast" in jid if jid else False


def extrair_texto(message: dict) -> Optional[str]:
    """
    Extrai texto da mensagem.
    WhatsApp tem vários formatos possíveis.
    """
    if not message:
        return None

    # Texto simples
    if "conversation" in message:
        return message["conversation"]

    # Texto com preview de link
    if "extendedTextMessage" in message:
        return message["extendedTextMessage"].get("text")

    # Legenda de imagem
    if "imageMessage" in message:
        return message["imageMessage"].get("caption")

    # Legenda de documento
    if "documentMessage" in message:
        return message["documentMessage"].get("caption")

    # Legenda de vídeo
    if "videoMessage" in message:
        return message["videoMessage"].get("caption")

    return None


def identificar_tipo(message: dict) -> str:
    """Identifica o tipo de mensagem."""
    if not message:
        return "outro"

    if "conversation" in message or "extendedTextMessage" in message:
        return "texto"
    elif "audioMessage" in message:
        return "audio"
    elif "imageMessage" in message:
        return "imagem"
    elif "documentMessage" in message:
        return "documento"
    elif "videoMessage" in message:
        return "video"
    elif "stickerMessage" in message:
        return "sticker"
    else:
        return "outro"


def parsear_mensagem(data: dict) -> Optional[MensagemRecebida]:
    """
    Converte payload da Evolution para nosso formato interno.

    Args:
        data: Payload do evento messages.upsert

    Returns:
        MensagemRecebida ou None se não for válida
    """
    try:
        # Extrair estrutura
        key = data.get("key", {})
        message = data.get("message", {})

        jid = key.get("remoteJid", "")
        from_me = key.get("fromMe", False)
        message_id = key.get("id", "")

        # Validar campos obrigatórios
        if not jid or not message_id:
            logger.warning(f"Mensagem sem JID ou ID: {data}")
            return None

        # Verificar se é grupo ou status
        if is_grupo(jid):
            logger.debug(f"Mensagem de grupo: {jid}")
            return MensagemRecebida(
                telefone=extrair_telefone(jid),
                message_id=message_id,
                from_me=from_me,
                tipo=identificar_tipo(message),
                texto=extrair_texto(message),
                nome_contato=data.get("pushName"),
                timestamp=datetime.fromtimestamp(data.get("messageTimestamp", 0)),
                is_grupo=True,
            )

        if is_status(jid):
            logger.debug("Status/story recebido")
            return MensagemRecebida(
                telefone=extrair_telefone(jid),
                message_id=message_id,
                from_me=from_me,
                tipo="outro",
                timestamp=datetime.now(),
                is_status=True,
            )

        # Mensagem normal
        return MensagemRecebida(
            telefone=extrair_telefone(jid),
            message_id=message_id,
            from_me=from_me,
            tipo=identificar_tipo(message),
            texto=extrair_texto(message),
            nome_contato=data.get("pushName"),
            timestamp=datetime.fromtimestamp(data.get("messageTimestamp", 0)),
        )

    except Exception as e:
        logger.error(f"Erro ao parsear mensagem: {e}")
        return None


def deve_processar(mensagem: MensagemRecebida) -> bool:
    """Verifica se mensagem deve ser processada."""

    # Ignorar nossas próprias mensagens
    if mensagem.from_me:
        return False

    # Ignorar grupos
    if mensagem.is_grupo:
        return False

    # Ignorar status/stories
    if mensagem.is_status:
        return False

    # Ignorar se não tem telefone válido
    if not mensagem.telefone or len(mensagem.telefone) < 10:
        return False

    return True
