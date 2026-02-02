"""
Repository para eventos de negocio.

Sprint 17 - E02
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.services.supabase import supabase
from .types import BusinessEvent, EventType

logger = logging.getLogger(__name__)


async def emit_event(event: BusinessEvent) -> str:
    """
    Emite um evento de negocio.

    Idempotência:
    - Se event.dedupe_key for definido, usa upsert para evitar duplicatas
    - Duplicata detectada retorna ID existente (não erro)

    Args:
        event: Evento a emitir

    Returns:
        id do evento criado/existente (UUID) ou string vazia se falhou
    """
    try:
        data = event.to_dict()

        # Se tem dedupe_key, usar upsert para idempotência
        if event.dedupe_key:
            # Primeiro tenta buscar existente
            existing = (
                supabase.table("business_events")
                .select("id")
                .eq("dedupe_key", event.dedupe_key)
                .limit(1)
                .execute()
            )

            if existing.data:
                event_id = existing.data[0]["id"]
                logger.info(
                    f"BusinessEvent duplicado ignorado: {event.event_type.value} "
                    f"[{event_id[:8]}] dedupe_key={event.dedupe_key}"
                )
                return event_id

        # Inserir novo evento
        response = (
            supabase.table("business_events")
            .insert(data)
            .execute()
        )

        if response.data:
            event_id = response.data[0]["id"]
            logger.info(
                f"BusinessEvent emitido: {event.event_type.value} "
                f"[{event_id[:8]}] source={event.source.value} cliente={event.cliente_id}"
            )
            return event_id

        logger.error("Falha ao emitir evento: sem data retornado")
        return ""

    except Exception as e:
        # Se for erro de unique constraint, é duplicata (race condition)
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            logger.info(f"BusinessEvent duplicado (race): {event.event_type.value}")
            # Tentar buscar o existente
            try:
                existing = (
                    supabase.table("business_events")
                    .select("id")
                    .eq("dedupe_key", event.dedupe_key)
                    .limit(1)
                    .execute()
                )
                if existing.data:
                    return existing.data[0]["id"]
            except Exception:
                pass
            return ""

        logger.error(f"Erro ao emitir business_event: {e}")
        return ""


async def get_events_by_type(
    event_type: EventType,
    hours: int = 24,
    limit: int = 100,
) -> list[dict]:
    """
    Busca eventos por tipo nas ultimas N horas.

    Args:
        event_type: Tipo do evento
        hours: Janela de tempo
        limit: Maximo de resultados

    Returns:
        Lista de eventos
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("event_type", event_type.value)
            .gte("ts", since)
            .order("ts", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos por tipo: {e}")
        return []


async def get_events_for_cliente(
    cliente_id: str,
    hours: int = 168,  # 7 dias
) -> list[dict]:
    """
    Busca eventos de um cliente.

    Args:
        cliente_id: UUID do cliente
        hours: Janela de tempo

    Returns:
        Lista de eventos ordenados por tempo
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("cliente_id", cliente_id)
            .gte("ts", since)
            .order("ts", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos do cliente: {e}")
        return []


async def get_events_for_vaga(vaga_id: str) -> list[dict]:
    """
    Busca todos os eventos de uma vaga.

    Args:
        vaga_id: UUID da vaga

    Returns:
        Lista de eventos ordenados por tempo
    """
    try:
        response = (
            supabase.table("business_events")
            .select("*")
            .eq("vaga_id", vaga_id)
            .order("ts", desc=True)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar eventos da vaga: {e}")
        return []


async def get_funnel_counts(
    hours: int = 24,
    hospital_id: Optional[str] = None,
) -> dict:
    """
    Conta eventos para o funil.

    Args:
        hours: Janela de tempo
        hospital_id: Filtrar por hospital (opcional)

    Returns:
        Dict com contagens por tipo de evento
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    try:
        # Sprint 44 T04.5/T04.7: Usar RPC para contagens se disponível
        # Fallback para query com limite
        try:
            response = supabase.rpc(
                "get_event_counts",
                {"p_hours": hours}
            ).execute()

            if response.data:
                return {row["event_type"]: row["count"] for row in response.data}
        except Exception:
            pass  # Fallback para query tradicional

        # Fallback com limite
        query = (
            supabase.table("business_events")
            .select("event_type")
            .gte("ts", since)
            .limit(10000)  # Sprint 44 T04.5: Limite de segurança
        )

        if hospital_id:
            query = query.eq("hospital_id", hospital_id)

        response = query.execute()

        # Contar por tipo
        counts = {}
        for row in response.data or []:
            event_type = row["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1

        return counts

    except Exception as e:
        logger.error(f"Erro ao contar eventos do funil: {e}")
        return {}
