"""
Webhook para receber SMS da Salvy.

Usado para receber codigo de verificacao do WhatsApp.
"""
import re
import logging
import hashlib
import hmac
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def verificar_assinatura_svix(
    payload: bytes,
    headers: dict,
) -> bool:
    """
    Verifica assinatura do webhook Svix (usado pela Salvy).

    Args:
        payload: Body raw do request
        headers: Headers do request

    Returns:
        True se assinatura valida
    """
    webhook_secret = getattr(settings, 'SALVY_WEBHOOK_SECRET', None)
    if not webhook_secret:
        logger.warning("[Salvy Webhook] SALVY_WEBHOOK_SECRET nao configurado")
        return True  # Permitir em dev

    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")

    if not all([svix_id, svix_timestamp, svix_signature]):
        logger.error("[Salvy Webhook] Headers Svix faltando")
        return False

    # Construir signed content
    signed_content = f"{svix_id}.{svix_timestamp}.{payload.decode()}"

    # Extrair secret (formato: whsec_xxxx)
    secret = webhook_secret.replace("whsec_", "")

    # Calcular assinatura
    expected = hmac.new(
        secret.encode(),
        signed_content.encode(),
        hashlib.sha256
    ).digest()

    # Comparar com assinaturas enviadas (podem ser multiplas)
    for sig in svix_signature.split():
        version, signature = sig.split(",", 1)
        if version == "v1":
            import base64
            expected_b64 = base64.b64encode(expected).decode()
            if hmac.compare_digest(signature, expected_b64):
                return True

    logger.error("[Salvy Webhook] Assinatura invalida")
    return False


def extrair_codigo_whatsapp(mensagem: str) -> Optional[str]:
    """
    Extrai codigo de verificacao do WhatsApp da mensagem SMS.

    Args:
        mensagem: Texto do SMS

    Returns:
        Codigo de 6 digitos ou None
    """
    # Padroes comuns de codigo WhatsApp
    patterns = [
        r'(?:codigo|code)[:\s]*(\d{6})',  # "Codigo: 123456" ou "Code 123456"
        r'(\d{6})\s*(?:e|is|seu)',         # "123456 e seu codigo"
        r'\b(\d{6})\b',                     # Qualquer sequencia de 6 digitos
    ]

    for pattern in patterns:
        match = re.search(pattern, mensagem, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


async def processar_sms_recebido(
    telefone: str,
    mensagem: str,
    remetente: str,
) -> dict:
    """
    Processa SMS recebido via webhook.

    Args:
        telefone: Numero que recebeu o SMS
        mensagem: Conteudo do SMS
        remetente: Quem enviou o SMS

    Returns:
        dict com resultado do processamento
    """
    logger.info(f"[Salvy Webhook] SMS para {telefone} de {remetente}: {mensagem[:50]}...")

    result = {
        "telefone": telefone,
        "remetente": remetente,
        "tipo": "unknown",
        "codigo": None,
        "processado": False,
    }

    # Detectar se e codigo WhatsApp
    if "whatsapp" in mensagem.lower() or remetente.lower() in ["whatsapp", "32665"]:
        codigo = extrair_codigo_whatsapp(mensagem)

        if codigo:
            result["tipo"] = "whatsapp_verification"
            result["codigo"] = codigo
            result["processado"] = True

            logger.info(f"[Salvy Webhook] Codigo WhatsApp extraido: {codigo} para {telefone}")

            # TODO: Atualizar chip com codigo para verificacao Evolution
            # await atualizar_chip_com_codigo(telefone, codigo)

    return result
