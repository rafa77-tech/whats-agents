"""
Servico de atribuicao de campanhas.

Sprint 23 E02 - Rastreia first/last touch para atribuicao de conversoes.

Este servico implementa:
- First Touch: Qual campanha abriu a conversa (atribuicao analitica)
- Last Touch: Qual campanha tocou por ultimo (atribuicao operacional)
- Reply Attribution: Qual campanha gerou a resposta (dentro da janela)

Invariantes:
- C2: Todo outbound SENT com campaign_id DEVE atualizar last_touch
- C3: Todo inbound reply dentro da janela (7d) DEVE herdar campaign_id
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase
from app.services.business_events import emit_event, BusinessEvent, EventType, EventSource

logger = logging.getLogger(__name__)

# Janela de atribuicao em dias (configuravel)
ATTRIBUTION_WINDOW_DAYS = 7


@dataclass
class TouchInfo:
    """Informacoes de um touch de campanha."""
    campaign_id: int
    touch_type: str  # campaign, followup, reactivation, manual
    touched_at: datetime


@dataclass
class AttributionResult:
    """Resultado de uma operacao de atribuicao."""
    success: bool
    first_touch_set: bool = False
    last_touch_updated: bool = False
    attributed_campaign_id: Optional[int] = None
    error: Optional[str] = None


async def registrar_campaign_touch(
    conversation_id: str,
    campaign_id: int,
    touch_type: str,
    cliente_id: str,
) -> AttributionResult:
    """
    Registra um touch de campanha na conversa.

    Chamado quando outbound com outcome=SENT e campaign_id != null.

    Logica:
    1. Atualiza last_touch_* (sempre)
    2. Se first_touch IS NULL, seta first_touch tambem

    Args:
        conversation_id: ID da conversa
        campaign_id: ID da campanha
        touch_type: Tipo do touch (campaign, followup, reactivation)
        cliente_id: ID do cliente (para evento)

    Returns:
        AttributionResult com detalhes da operacao
    """
    now = datetime.now(timezone.utc)

    try:
        # Buscar estado atual da conversa
        response = (
            supabase.table("conversations")
            .select("first_touch_campaign_id, first_touch_at")
            .eq("id", conversation_id)
            .single()
            .execute()
        )

        if not response.data:
            logger.warning(f"Conversa {conversation_id} nao encontrada para touch")
            return AttributionResult(
                success=False,
                error=f"Conversa {conversation_id} nao encontrada"
            )

        conversa = response.data
        first_touch_set = False

        # Preparar update
        update_data = {
            "last_touch_campaign_id": campaign_id,
            "last_touch_type": touch_type,
            "last_touch_at": now.isoformat(),
        }

        # Se nao tem first_touch, setar tambem
        if conversa.get("first_touch_campaign_id") is None:
            update_data["first_touch_campaign_id"] = campaign_id
            update_data["first_touch_type"] = touch_type
            update_data["first_touch_at"] = now.isoformat()
            first_touch_set = True

        # Aplicar update
        supabase.table("conversations").update(update_data).eq(
            "id", conversation_id
        ).execute()

        # Emitir evento de auditoria
        await emit_event(BusinessEvent(
            event_type=EventType.CAMPAIGN_TOUCH_LINKED,
            source=EventSource.SYSTEM,
            cliente_id=cliente_id,
            conversation_id=conversation_id,
            event_props={
                "campaign_id": campaign_id,
                "touch_type": touch_type,
                "first_touch_set": first_touch_set,
                "touched_at": now.isoformat(),
            }
        ))

        logger.info(
            f"Touch registrado: conversa={conversation_id}, "
            f"campanha={campaign_id}, tipo={touch_type}, "
            f"first_touch_set={first_touch_set}"
        )

        return AttributionResult(
            success=True,
            first_touch_set=first_touch_set,
            last_touch_updated=True,
        )

    except Exception as e:
        logger.error(f"Erro ao registrar touch: {e}", exc_info=True)
        return AttributionResult(success=False, error=str(e))


async def atribuir_reply_a_campanha(
    interaction_id: int,
    conversation_id: str,
    cliente_id: str,
) -> AttributionResult:
    """
    Atribui uma resposta (inbound) a campanha que a gerou.

    Chamado quando recebe mensagem inbound.

    Logica:
    1. Buscar last_touch_campaign_id da conversa
    2. Se existe e last_touch_at dentro da janela (7 dias):
       - Gravar attributed_campaign_id na interacao
       - Emitir evento CAMPAIGN_REPLY_ATTRIBUTED
    3. Se nao existe ou fora da janela:
       - attributed_campaign_id = NULL (resposta organica)

    Args:
        interaction_id: ID da interacao (inbound)
        conversation_id: ID da conversa
        cliente_id: ID do cliente

    Returns:
        AttributionResult com campaign_id atribuido (ou None)
    """
    try:
        # Buscar last_touch da conversa
        response = (
            supabase.table("conversations")
            .select("last_touch_campaign_id, last_touch_at")
            .eq("id", conversation_id)
            .single()
            .execute()
        )

        if not response.data:
            logger.debug(f"Conversa {conversation_id} nao encontrada para atribuicao")
            return AttributionResult(success=True, attributed_campaign_id=None)

        conversa = response.data
        last_touch_campaign_id = conversa.get("last_touch_campaign_id")
        last_touch_at_str = conversa.get("last_touch_at")

        if not last_touch_campaign_id or not last_touch_at_str:
            # Sem touch anterior - resposta organica
            logger.debug(
                f"Interacao {interaction_id} sem touch anterior (organica)"
            )
            return AttributionResult(success=True, attributed_campaign_id=None)

        # Verificar se esta dentro da janela de atribuicao
        last_touch_at = datetime.fromisoformat(
            last_touch_at_str.replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)
        dias_desde_touch = (now - last_touch_at).days

        if dias_desde_touch > ATTRIBUTION_WINDOW_DAYS:
            # Fora da janela - resposta organica
            logger.debug(
                f"Interacao {interaction_id} fora da janela "
                f"({dias_desde_touch} dias desde touch)"
            )
            return AttributionResult(success=True, attributed_campaign_id=None)

        # Dentro da janela - atribuir
        supabase.table("interacoes").update({
            "attributed_campaign_id": last_touch_campaign_id
        }).eq("id", interaction_id).execute()

        # Emitir evento de auditoria
        await emit_event(BusinessEvent(
            event_type=EventType.CAMPAIGN_REPLY_ATTRIBUTED,
            source=EventSource.SYSTEM,
            cliente_id=cliente_id,
            conversation_id=conversation_id,
            event_props={
                "campaign_id": last_touch_campaign_id,
                "interaction_id": interaction_id,
                "days_since_touch": dias_desde_touch,
            }
        ))

        logger.info(
            f"Reply atribuido: interacao={interaction_id}, "
            f"campanha={last_touch_campaign_id}, "
            f"dias_desde_touch={dias_desde_touch}"
        )

        return AttributionResult(
            success=True,
            attributed_campaign_id=last_touch_campaign_id,
        )

    except Exception as e:
        logger.error(f"Erro ao atribuir reply: {e}", exc_info=True)
        return AttributionResult(success=False, error=str(e))


async def buscar_atribuicao_conversa(
    conversation_id: str,
) -> dict:
    """
    Busca informacoes de atribuicao de uma conversa.

    Util para debug e relatorios.

    Returns:
        Dict com first_touch e last_touch info
    """
    response = (
        supabase.table("conversations")
        .select(
            "first_touch_campaign_id, first_touch_type, first_touch_at, "
            "last_touch_campaign_id, last_touch_type, last_touch_at"
        )
        .eq("id", conversation_id)
        .single()
        .execute()
    )

    if not response.data:
        return {}

    return response.data


async def contar_replies_por_campanha(
    campaign_id: int,
    dias: int = 30,
) -> dict:
    """
    Conta replies atribuidos a uma campanha.

    Args:
        campaign_id: ID da campanha
        dias: Periodo de analise em dias

    Returns:
        Dict com contagem de replies e conversoes
    """
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    response = (
        supabase.table("interacoes")
        .select("id", count="exact")
        .eq("attributed_campaign_id", campaign_id)
        .eq("origem", "medico")  # Apenas inbound
        .gte("created_at", desde)
        .execute()
    )

    return {
        "campaign_id": campaign_id,
        "total_replies": response.count or 0,
        "periodo_dias": dias,
    }
