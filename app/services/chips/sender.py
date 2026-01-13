"""
Chip Sender - Envio de mensagens via chip com provider abstraction.

Sprint 26 - E08: Multi-Provider Support

Integra o Chip Selector com WhatsApp Providers para enviar
mensagens pelo chip correto usando o provider apropriado.
"""

import logging
from typing import Optional, Dict, Literal

from app.services.supabase import supabase
from app.services.whatsapp_providers import get_provider, MessageResult
from app.services.chips.selector import ChipSelector

logger = logging.getLogger(__name__)

TipoMensagem = Literal["prospeccao", "followup", "resposta"]

# Singleton do selector
_chip_selector: Optional[ChipSelector] = None


def _get_selector() -> ChipSelector:
    """Retorna singleton do chip selector."""
    global _chip_selector
    if _chip_selector is None:
        _chip_selector = ChipSelector()
    return _chip_selector


async def enviar_via_chip(
    chip: Dict,
    telefone: str,
    texto: str,
) -> MessageResult:
    """
    Envia mensagem usando o provider do chip.

    Args:
        chip: Dict com dados do chip (da tabela chips)
        telefone: Número do destinatário
        texto: Texto da mensagem

    Returns:
        MessageResult com status do envio
    """
    try:
        provider = get_provider(chip)
        result = await provider.send_text(telefone, texto)

        # Atualizar métricas do chip
        if result.success:
            await _atualizar_metricas_envio(chip["id"])

        logger.info(
            f"[ChipSender] Enviado via {result.provider}: "
            f"chip={chip.get('telefone', 'N/A')[-4:]}, "
            f"destino={telefone[-4:]}, success={result.success}"
        )

        return result

    except Exception as e:
        logger.error(f"[ChipSender] Erro ao enviar: {e}")
        return MessageResult(success=False, error=str(e))


async def enviar_mensagem_inteligente(
    tipo_mensagem: TipoMensagem,
    telefone: str,
    texto: str,
    conversa_id: Optional[str] = None,
) -> Dict:
    """
    Seleciona melhor chip e envia mensagem.

    Combina ChipSelector + Provider para envio inteligente.

    Args:
        tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
        telefone: Número do destinatário
        texto: Texto da mensagem
        conversa_id: ID da conversa (para continuidade)

    Returns:
        {
            "success": bool,
            "chip_id": str | None,
            "chip_telefone": str | None,
            "provider": str | None,
            "message_id": str | None,
            "error": str | None
        }
    """
    selector = _get_selector()

    # 1. Selecionar chip
    chip = await selector.selecionar_chip(
        tipo_mensagem=tipo_mensagem,
        conversa_id=conversa_id,
        telefone_destino=telefone,
    )

    if not chip:
        logger.warning(f"[ChipSender] Nenhum chip disponível para {tipo_mensagem}")
        return {
            "success": False,
            "chip_id": None,
            "chip_telefone": None,
            "provider": None,
            "message_id": None,
            "error": f"Nenhum chip disponível para {tipo_mensagem}",
        }

    # 2. Enviar via provider do chip
    result = await enviar_via_chip(chip, telefone, texto)

    return {
        "success": result.success,
        "chip_id": chip["id"],
        "chip_telefone": chip.get("telefone"),
        "provider": result.provider,
        "message_id": result.message_id,
        "error": result.error,
    }


async def enviar_media_via_chip(
    chip: Dict,
    telefone: str,
    media_url: str,
    caption: Optional[str] = None,
    media_type: str = "image",
) -> MessageResult:
    """
    Envia mídia usando o provider do chip.

    Args:
        chip: Dict com dados do chip
        telefone: Número do destinatário
        media_url: URL da mídia
        caption: Legenda (opcional)
        media_type: Tipo de mídia (image, document, audio, video)

    Returns:
        MessageResult com status do envio
    """
    try:
        provider = get_provider(chip)
        result = await provider.send_media(
            telefone,
            media_url,
            caption=caption,
            media_type=media_type,
        )

        if result.success:
            await _atualizar_metricas_envio(chip["id"])

        return result

    except Exception as e:
        logger.error(f"[ChipSender] Erro ao enviar mídia: {e}")
        return MessageResult(success=False, error=str(e))


async def verificar_conexao_chip(chip: Dict) -> Dict:
    """
    Verifica status de conexão do chip.

    Args:
        chip: Dict com dados do chip

    Returns:
        {
            "connected": bool,
            "state": str,
            "provider": str,
            "error": str | None
        }
    """
    try:
        provider = get_provider(chip)
        status = await provider.get_status()

        return {
            "connected": status.connected,
            "state": status.state,
            "provider": provider.provider_type.value,
            "qr_code": status.qr_code,
            "error": None,
        }

    except Exception as e:
        logger.error(f"[ChipSender] Erro ao verificar conexão: {e}")
        return {
            "connected": False,
            "state": "error",
            "provider": chip.get("provider", "unknown"),
            "error": str(e),
        }


async def _atualizar_metricas_envio(chip_id: str) -> None:
    """Atualiza métricas de envio do chip."""
    try:
        supabase.rpc(
            "incrementar_msgs_enviadas",
            {"p_chip_id": chip_id},
        ).execute()
    except Exception as e:
        # Não falhar o envio por erro de métrica
        logger.warning(f"[ChipSender] Erro ao atualizar métricas: {e}")
