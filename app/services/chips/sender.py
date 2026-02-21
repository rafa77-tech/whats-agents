"""
Chip Sender - Envio de mensagens via chip com provider abstraction.

Sprint 26 - E08: Multi-Provider Support
Sprint 36 - T05.6: Retry com chip alternativo
Sprint 36 - T05.8: Cooldown após erro WhatsApp
Sprint 36 - T08.1: Métricas de envio para Trust Score
Sprint 36 - T09.2: Integração com circuit breaker per-chip

Integra o Chip Selector com WhatsApp Providers para enviar
mensagens pelo chip correto usando o provider apropriado.
"""

import logging
from typing import Optional, Dict, Literal, List

from app.services.supabase import supabase
from app.services.whatsapp_providers import get_provider, MessageResult
from app.services.chips.selector import ChipSelector
from app.services.chips.circuit_breaker import ChipCircuitBreaker
from app.services.chips.cooldown import registrar_erro_whatsapp

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
    template_info: Optional[Dict] = None,
) -> MessageResult:
    """
    Envia mensagem usando o provider do chip.

    Sprint 66: Para chips Meta, respeita janela 24h.
    - Dentro da janela: send_text (free-form)
    - Fora da janela + template_info: send_template
    - Fora da janela + sem template: erro

    Args:
        chip: Dict com dados do chip (da tabela chips)
        telefone: Número do destinatário
        texto: Texto da mensagem
        template_info: Info do template Meta (name, language, components)

    Returns:
        MessageResult com status do envio
    """
    # Sprint 51 - E03: BLOQUEIO DEFENSIVO para chips listener
    # Chips listener são exclusivos para escuta de grupos (read-only)
    if chip.get("tipo") == "listener":
        logger.error(
            f"[ChipSender] BLOQUEIO: Tentativa de envio via chip listener! "
            f"chip={chip.get('telefone', 'N/A')}, destino={telefone[-4:]}"
        )
        return MessageResult(success=False, error="Chip listener não pode enviar mensagens")

    try:
        provider = get_provider(chip)

        # Sprint 66: Smart routing para chips Meta
        if chip.get("provider") == "meta":
            result = await _enviar_meta_smart(
                provider, chip, telefone, texto, template_info
            )
        else:
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
    max_retries: int = 3,
    template_info: Optional[Dict] = None,
) -> Dict:
    """
    Seleciona melhor chip e envia mensagem com retry automático.

    Sprint 36 - T05.6: Retry com chip alternativo em caso de falha.

    Combina ChipSelector + Provider para envio inteligente.
    Em caso de falha, tenta automaticamente com chips alternativos.

    Args:
        tipo_mensagem: 'prospeccao', 'followup', ou 'resposta'
        telefone: Número do destinatário
        texto: Texto da mensagem
        conversa_id: ID da conversa (para continuidade)
        max_retries: Número máximo de tentativas (default: 3)

    Returns:
        {
            "success": bool,
            "chip_id": str | None,
            "chip_telefone": str | None,
            "provider": str | None,
            "message_id": str | None,
            "error": str | None,
            "tentativas": int,
            "chips_tentados": list[str]
        }
    """
    selector = _get_selector()
    chips_tentados: List[str] = []
    ultimo_erro: Optional[str] = None
    ultimo_chip: Optional[Dict] = None

    for tentativa in range(max_retries):
        # 1. Selecionar chip (excluindo os já tentados)
        chip = await selector.selecionar_chip(
            tipo_mensagem=tipo_mensagem,
            conversa_id=conversa_id,
            telefone_destino=telefone,
            excluir_chips=chips_tentados if chips_tentados else None,
        )

        if not chip:
            # Sem mais chips disponíveis
            if chips_tentados:
                logger.warning(
                    f"[ChipSender] Sem mais chips após {len(chips_tentados)} tentativas "
                    f"para {tipo_mensagem}"
                )
            else:
                logger.warning(f"[ChipSender] Nenhum chip disponível para {tipo_mensagem}")
            break

        ultimo_chip = chip
        chips_tentados.append(chip["id"])

        # 2. Tentar enviar
        result = await enviar_via_chip(chip, telefone, texto, template_info=template_info)

        if result.success:
            # Sucesso!
            if tentativa > 0:
                logger.info(
                    f"[ChipSender] Sucesso na tentativa {tentativa + 1} "
                    f"após fallback de {chips_tentados[:-1]}"
                )
            return {
                "success": True,
                "chip_id": chip["id"],
                "chip_telefone": chip.get("telefone"),
                "provider": result.provider,
                "message_id": result.message_id,
                "error": None,
                "tentativas": tentativa + 1,
                "chips_tentados": chips_tentados,
            }

        # Falhou - registrar erro e tentar próximo
        ultimo_erro = result.error

        logger.warning(
            f"[ChipSender] Falha na tentativa {tentativa + 1}/{max_retries}: "
            f"chip={chip.get('telefone', 'N/A')[-4:]}, erro={result.error}"
        )

        # Verificar se deve fazer retry
        if tentativa < max_retries - 1:
            logger.info(
                f"[ChipSender] Tentando fallback para chip alternativo "
                f"(tentativa {tentativa + 2}/{max_retries})"
            )

    # Todas as tentativas falharam
    return {
        "success": False,
        "chip_id": ultimo_chip["id"] if ultimo_chip else None,
        "chip_telefone": ultimo_chip.get("telefone") if ultimo_chip else None,
        "provider": None,
        "message_id": None,
        "error": ultimo_erro or f"Nenhum chip disponível para {tipo_mensagem}",
        "tentativas": len(chips_tentados),
        "chips_tentados": chips_tentados,
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
    # Sprint 51 - E03: BLOQUEIO DEFENSIVO para chips listener
    if chip.get("tipo") == "listener":
        logger.error(
            f"[ChipSender] BLOQUEIO: Tentativa de envio de mídia via chip listener! "
            f"chip={chip.get('telefone', 'N/A')}, destino={telefone[-4:]}"
        )
        return MessageResult(success=False, error="Chip listener não pode enviar mensagens")

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

    Sprint 36 - T09.2: Também atualiza circuit breaker per-chip.

    Args:
        chip_id: ID do chip
        telefone_destino: Número do destinatário (para rastrear conversas)
        sucesso: Se o envio foi bem-sucedido
        error_code: Código do erro (se falhou)
        error_message: Mensagem de erro (se falhou)
        tipo_midia: Tipo de mídia enviada (se aplicável)
    """
    # Sprint 36 - T09.2: Atualizar circuit breaker per-chip
    if sucesso:
        ChipCircuitBreaker.registrar_sucesso(chip_id)
    else:
        ChipCircuitBreaker.registrar_falha(chip_id, error_code, error_message)

        # Sprint 36 - T05.8: Aplicar cooldown baseado no tipo de erro
        try:
            cooldown_result = await registrar_erro_whatsapp(
                chip_id=chip_id,
                error_code=error_code,
                error_message=error_message,
            )
            if cooldown_result.get("cooldown_aplicado"):
                logger.info(
                    f"[ChipSender] Cooldown aplicado ao chip {chip_id[:8]}: "
                    f"{cooldown_result['cooldown_minutos']}min - {cooldown_result['motivo']}"
                )
        except Exception as cooldown_err:
            logger.warning(f"[ChipSender] Erro ao aplicar cooldown: {cooldown_err}")

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
                supabase.table("chip_interactions").update(
                    {
                        "destinatario": telefone_destino,
                    }
                ).eq("chip_id", chip_id).eq("tipo", "msg_enviada").is_(
                    "destinatario", "null"
                ).order("created_at", desc=True).limit(1).execute()
            except Exception:
                pass  # Best effort

    except Exception as e:
        # Não falhar o envio por erro de métrica
        logger.warning(f"[ChipSender] Erro ao registrar métricas: {e}")


async def _enviar_meta_smart(
    provider,
    chip: Dict,
    telefone: str,
    texto: str,
    template_info: Optional[Dict] = None,
) -> MessageResult:
    """
    Sprint 66: Envio inteligente para chips Meta respeitando janela 24h.

    - Dentro da janela: envia texto livre (free-form)
    - Fora da janela + template: envia via template
    - Fora da janela + sem template: retorna erro

    Args:
        provider: MetaCloudProvider
        chip: Dict do chip
        telefone: Número do destinatário
        texto: Texto da mensagem
        template_info: Dict com name, language, components do template

    Returns:
        MessageResult
    """
    from app.services.meta.window_tracker import window_tracker

    na_janela = await window_tracker.esta_na_janela(chip["id"], telefone)

    if na_janela:
        return await provider.send_text(telefone, texto)
    elif template_info:
        return await provider.send_template(
            telefone,
            template_info["name"],
            template_info.get("language", "pt_BR"),
            template_info.get("components"),
        )
    else:
        logger.warning(
            f"[ChipSender] Chip Meta fora da janela 24h e sem template: "
            f"chip={chip.get('telefone', 'N/A')[-4:]}, destino={telefone[-4:]}"
        )
        return MessageResult(
            success=False,
            error="meta_fora_janela_sem_template",
            provider="meta",
        )


# Alias para retrocompatibilidade
async def _atualizar_metricas_envio(chip_id: str) -> None:
    """Alias para retrocompatibilidade."""
    await _registrar_envio(chip_id=chip_id, telefone_destino="", sucesso=True)
