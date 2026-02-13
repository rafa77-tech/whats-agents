"""
Multi-chip envio outbound.

Sprint 58 E04 - Extraido de sender.py.
Sprint 26 E02 - Integracao com ChipSelector para multi-chip.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.guardrails import (
    OutboundContext,
    OutboundMethod,
)

logger = logging.getLogger(__name__)


def _is_multi_chip_enabled() -> bool:
    """Verifica se multi-chip esta habilitado."""
    return getattr(settings, "MULTI_CHIP_ENABLED", False)


def _determinar_tipo_mensagem(ctx: "OutboundContext") -> str:
    """
    Determina o tipo de mensagem baseado no contexto.

    Returns:
        'prospeccao', 'followup', ou 'resposta'
    """
    # Resposta: quando eh reply a uma mensagem recebida
    if ctx.method == OutboundMethod.REPLY:
        return "resposta"

    # Prospeccao: campanha proativa para contato frio
    if ctx.method == OutboundMethod.CAMPAIGN and ctx.is_proactive:
        return "prospeccao"

    # Followup: acompanhamento de conversa existente
    if ctx.method in (OutboundMethod.FOLLOWUP, OutboundMethod.REACTIVATION):
        return "followup"

    # Default: resposta (mais permissivo)
    return "resposta"


async def _enviar_via_multi_chip(
    telefone: str,
    texto: str,
    ctx: "OutboundContext",
    simular_digitacao: bool = False,
    tempo_digitacao: float = None,
    chips_excluidos: Optional[list] = None,
) -> dict:
    """
    Envia mensagem usando o sistema multi-chip.

    Sprint 26 E02: Seleciona melhor chip e envia via provider.

    Args:
        telefone: Numero do destinatario
        texto: Texto da mensagem
        ctx: Contexto do envio
        simular_digitacao: Se deve simular digitacao
        tempo_digitacao: Tempo de digitacao
        chips_excluidos: Lista de chip IDs a excluir da selecao (ex: campanha)

    Returns:
        Dict com resultado do envio
    """
    from app.services.chips.selector import chip_selector
    from app.services.chips.sender import enviar_via_chip

    tipo_mensagem = _determinar_tipo_mensagem(ctx)

    # Selecionar chip (excluindo chips da campanha se configurado)
    chip = await chip_selector.selecionar_chip(
        tipo_mensagem=tipo_mensagem,
        conversa_id=ctx.conversation_id,
        telefone_destino=telefone,
        excluir_chips=chips_excluidos,
    )

    if not chip:
        logger.warning(
            f"[MultiChip] Nenhum chip disponivel para {tipo_mensagem}, fallback para Evolution"
        )
        return {"fallback": True}

    # Simular digitacao se necessario
    if simular_digitacao:
        from app.services.whatsapp_providers import get_provider
        import asyncio

        provider = get_provider(chip)
        tempo = tempo_digitacao or 1.5

        # Enviar presence "composing"
        try:
            # Evolution API: /chat/presence/{instance}
            if chip.get("provider") == "evolution":
                from app.services.http_client import get_http_client

                client = await get_http_client()
                await client.post(
                    f"{provider.base_url}/chat/presence/{provider.instance_name}",
                    headers=provider.headers,
                    json={
                        "number": telefone,
                        "delay": int(tempo * 1000),
                        "presence": "composing",
                    },
                    timeout=5,
                )
        except Exception as e:
            logger.debug(f"[MultiChip] Erro ao enviar presence: {e}")

        await asyncio.sleep(tempo)

    # Enviar mensagem
    result = await enviar_via_chip(chip, telefone, texto)

    # Registrar envio para metricas
    if result.success and ctx.conversation_id:
        try:
            await chip_selector.registrar_envio(
                chip_id=chip["id"],
                conversa_id=ctx.conversation_id,
                tipo_mensagem=tipo_mensagem,
                telefone_destino=telefone,
            )
        except Exception as e:
            logger.warning(f"[MultiChip] Erro ao registrar envio: {e}")

    # Converter para formato esperado pelo outbound
    response = None
    if result.success:
        response = {
            "key": {"id": result.message_id},
            "provider": result.provider,
            "chip_id": chip["id"],
            "chip_telefone": chip.get("telefone"),
        }

    return {
        "success": result.success,
        "response": response,
        "error": result.error,
        "fallback": False,
    }
