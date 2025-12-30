"""
Servico de atribuicao de campanhas.

Sprint 23 E02 - Rastreia first/last touch para atribuicao de conversoes.

Este servico implementa:
- First Touch: Qual campanha abriu a conversa (atribuicao analitica)
- Last Touch: Qual campanha tocou por ultimo (atribuicao operacional)
- Reply Attribution: Qual campanha gerou a resposta (dentro da janela)
- Attribution Lock: Protege last_touch quando ha inbound recente

Invariantes:
- C2: Todo outbound SENT com campaign_id DEVE atualizar last_touch
- C3: Todo inbound reply dentro da janela (7d) DEVE herdar campaign_id
- C4: Se ha inbound recente (< LOCK_MINUTES), NAO sobrescreve last_touch
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

# Attribution Lock: Não sobrescrever last_touch se há inbound recente
# Se médico respondeu há menos de X minutos, o touch que gerou a resposta
# "possui" a atribuição - campanhas novas não podem roubar crédito
ATTRIBUTION_LOCK_MINUTES = 60


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
    attribution_locked: bool = False  # True se lock impediu atualização de last_touch
    attributed_campaign_id: Optional[int] = None
    error: Optional[str] = None


async def _check_attribution_lock(cliente_id: str) -> bool:
    """
    Verifica se há inbound recente que impede atualização de last_touch.

    Attribution Lock: Se médico respondeu há menos de ATTRIBUTION_LOCK_MINUTES,
    o touch que gerou a resposta "possui" a atribuição.

    Returns:
        True se deve bloquear atualização de last_touch
    """
    try:
        # Buscar last_inbound_at do doctor_state
        response = (
            supabase.table("doctor_state")
            .select("last_inbound_at")
            .eq("cliente_id", cliente_id)
            .single()
            .execute()
        )

        if not response.data:
            return False  # Sem state = sem lock

        last_inbound_at_str = response.data.get("last_inbound_at")
        if not last_inbound_at_str:
            return False  # Sem inbound = sem lock

        # Parsear e verificar janela
        last_inbound_at = datetime.fromisoformat(
            last_inbound_at_str.replace("Z", "+00:00")
        )

        now = datetime.now(timezone.utc)
        minutos_desde_inbound = (now - last_inbound_at).total_seconds() / 60

        if minutos_desde_inbound < ATTRIBUTION_LOCK_MINUTES:
            logger.debug(
                f"Attribution lock ativo: cliente={cliente_id[:8]}, "
                f"inbound ha {minutos_desde_inbound:.0f} min (lock={ATTRIBUTION_LOCK_MINUTES} min)"
            )
            return True

        return False

    except Exception as e:
        logger.warning(f"Erro ao verificar attribution lock: {e}")
        return False  # Em caso de erro, não bloquear


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
    1. Verifica attribution lock (inbound recente)
    2. Se locked, NAO atualiza last_touch (preserva atribuicao existente)
    3. Se nao locked, atualiza last_touch_*
    4. Se first_touch IS NULL, seta first_touch tambem (independente do lock)

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
        # Verificar attribution lock
        is_locked = await _check_attribution_lock(cliente_id)

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
        last_touch_updated = False

        # Preparar update
        update_data = {}

        # last_touch: só atualiza se NÃO está locked
        if not is_locked:
            update_data["last_touch_campaign_id"] = campaign_id
            update_data["last_touch_type"] = touch_type
            update_data["last_touch_at"] = now.isoformat()
            last_touch_updated = True
        else:
            logger.info(
                f"Attribution locked: campanha {campaign_id} NAO sobrescreveu "
                f"last_touch de conversa {conversation_id[:8]} (inbound recente)"
            )

        # first_touch: sempre seta se ainda não existe (independente do lock)
        if conversa.get("first_touch_campaign_id") is None:
            update_data["first_touch_campaign_id"] = campaign_id
            update_data["first_touch_type"] = touch_type
            update_data["first_touch_at"] = now.isoformat()
            first_touch_set = True

        # Aplicar update (se houver algo para atualizar)
        if update_data:
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
                "last_touch_updated": last_touch_updated,
                "attribution_locked": is_locked,
                "touched_at": now.isoformat(),
            }
        ))

        logger.info(
            f"Touch registrado: conversa={conversation_id}, "
            f"campanha={campaign_id}, tipo={touch_type}, "
            f"first_touch_set={first_touch_set}, "
            f"last_touch_updated={last_touch_updated}, "
            f"locked={is_locked}"
        )

        return AttributionResult(
            success=True,
            first_touch_set=first_touch_set,
            last_touch_updated=last_touch_updated,
            attribution_locked=is_locked,
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
