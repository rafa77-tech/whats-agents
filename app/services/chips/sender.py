"""
Chip Sender - Envio de mensagens via chip com provider abstraction.

Sprint 26 - E08: Multi-Provider Support
Sprint 36 - T08.1: Métricas de envio para Trust Score

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

        # Atualizar métricas do chip (Sprint 36 - T08.1)
        await _registrar_envio(
            chip_id=chip["id"],
            telefone_destino=telefone,
            sucesso=result.success,
            error_code=result.error_code if hasattr(result, "error_code") else None,
            error_message=result.error if not result.success else None,
        )

        logger.info(
            f"[ChipSender] Enviado via {result.provider}: "
            f"chip={chip.get('telefone', 'N/A')[-4:]}, "
            f"destino={telefone[-4:]}, success={result.success}"
        )

        return result

    except Exception as e:
        logger.error(f"[ChipSender] Erro ao enviar: {e}")
        # Registrar erro mesmo em exceção
        await _registrar_envio(
            chip_id=chip["id"],
            telefone_destino=telefone,
            sucesso=False,
            error_message=str(e),
        )
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

        # Atualizar métricas do chip (Sprint 36 - T08.1)
        await _registrar_envio(
            chip_id=chip["id"],
            telefone_destino=telefone,
            sucesso=result.success,
            error_code=result.error_code if hasattr(result, "error_code") else None,
            error_message=result.error if not result.success else None,
            tipo_midia=media_type,
        )

        return result

    except Exception as e:
        logger.error(f"[ChipSender] Erro ao enviar mídia: {e}")
        await _registrar_envio(
            chip_id=chip["id"],
            telefone_destino=telefone,
            sucesso=False,
            error_message=str(e),
        )
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


async def _registrar_envio(
    chip_id: str,
    telefone_destino: str,
    sucesso: bool,
    error_code: Optional[int] = None,
    error_message: Optional[str] = None,
    tipo_midia: Optional[str] = None,
) -> None:
    """
    Registra envio para métricas do chip (Sprint 36 - T08.1).

    Atualiza contadores no banco para alimentar o Trust Score:
    - msgs_enviadas_total
    - msgs_enviadas_hoje
    - erros_ultimas_24h (se falhou)
    - ultimo_envio_em

    Args:
        chip_id: ID do chip
        telefone_destino: Número do destinatário (para rastrear conversas)
        sucesso: Se o envio foi bem-sucedido
        error_code: Código do erro (se falhou)
        error_message: Mensagem de erro (se falhou)
        tipo_midia: Tipo de mídia enviada (se aplicável)
    """
    try:
        if sucesso:
            result = supabase.rpc(
                "chip_registrar_envio_sucesso",
                {"p_chip_id": chip_id},
            ).execute()
            logger.debug(f"[ChipSender] Métricas atualizadas (sucesso): {result.data}")
        else:
            result = supabase.rpc(
                "chip_registrar_envio_erro",
                {
                    "p_chip_id": chip_id,
                    "p_error_code": error_code,
                    "p_error_message": error_message,
                },
            ).execute()
            logger.debug(f"[ChipSender] Métricas atualizadas (erro): {result.data}")

        # Registrar destinatário para rastreio de conversas bidirecionais
        if telefone_destino:
            try:
                supabase.table("chip_interactions").update({
                    "destinatario": telefone_destino,
                }).eq(
                    "chip_id", chip_id
                ).eq(
                    "tipo", "msg_enviada"
                ).is_(
                    "destinatario", "null"
                ).order(
                    "created_at", desc=True
                ).limit(1).execute()
            except Exception:
                pass  # Best effort

    except Exception as e:
        # Não falhar o envio por erro de métrica
        logger.warning(f"[ChipSender] Erro ao registrar métricas: {e}")


# Alias para retrocompatibilidade
async def _atualizar_metricas_envio(chip_id: str) -> None:
    """Alias para retrocompatibilidade."""
    await _registrar_envio(chip_id=chip_id, telefone_destino="", sucesso=True)
