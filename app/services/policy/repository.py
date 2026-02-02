"""
Repositório para doctor_state.

Sprint 15 - Policy Engine
"""
import logging
from datetime import datetime
from typing import Optional

from app.core.timezone import agora_utc
from app.services.supabase import supabase
from app.services.redis import cache_get_json, cache_set_json, cache_delete
from .types import (
    DoctorState, PermissionState, TemperatureTrend,
    TemperatureBand, ObjectionSeverity, RiskTolerance, LifecycleStage
)

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # 5 minutos
CACHE_PREFIX = "doctor_state"


def _parse_datetime(value) -> Optional[datetime]:
    """Converte valor do banco para datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Remove timezone suffix se presente
        value = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _row_to_state(row: dict) -> DoctorState:
    """Converte row do banco para DoctorState."""
    # Parse enums com fallback seguro
    try:
        permission = PermissionState(row.get("permission_state", "none"))
    except ValueError:
        permission = PermissionState.NONE

    try:
        trend = TemperatureTrend(row.get("temperature_trend", "stable"))
    except ValueError:
        trend = TemperatureTrend.STABLE

    try:
        band = TemperatureBand(row.get("temperature_band", "warm"))
    except ValueError:
        band = TemperatureBand.WARM

    try:
        risk = RiskTolerance(row.get("risk_tolerance", "unknown"))
    except ValueError:
        risk = RiskTolerance.UNKNOWN

    try:
        lifecycle = LifecycleStage(row.get("lifecycle_stage", "novo"))
    except ValueError:
        lifecycle = LifecycleStage.NOVO

    severity = None
    if row.get("objection_severity"):
        try:
            severity = ObjectionSeverity(row["objection_severity"])
        except ValueError:
            pass

    return DoctorState(
        cliente_id=str(row["cliente_id"]),
        permission_state=permission,
        cooling_off_until=_parse_datetime(row.get("cooling_off_until")),
        temperature=float(row.get("temperature", 0.5)),
        temperature_trend=trend,
        temperature_band=band,
        risk_tolerance=risk,
        last_inbound_at=_parse_datetime(row.get("last_inbound_at")),
        last_outbound_at=_parse_datetime(row.get("last_outbound_at")),
        last_outbound_actor=row.get("last_outbound_actor"),
        next_allowed_at=_parse_datetime(row.get("next_allowed_at")),
        contact_count_7d=row.get("contact_count_7d", 0),
        active_objection=row.get("active_objection"),
        objection_severity=severity,
        objection_detected_at=_parse_datetime(row.get("objection_detected_at")),
        objection_resolved_at=_parse_datetime(row.get("objection_resolved_at")),
        pending_action=row.get("pending_action"),
        current_intent=row.get("current_intent"),
        lifecycle_stage=lifecycle,
        flags=row.get("flags", {}),
        last_decay_at=_parse_datetime(row.get("last_decay_at")),
    )


async def load_doctor_state(cliente_id: str) -> Optional[DoctorState]:
    """
    Carrega estado do médico.

    Tenta cache primeiro, depois banco.
    Se não existir, cria registro default.
    """
    cache_key = f"{CACHE_PREFIX}:{cliente_id}"

    # Tentar cache
    try:
        cached = await cache_get_json(cache_key)
        if cached:
            return _row_to_state(cached)
    except Exception as e:
        logger.warning(f"Erro ao ler cache doctor_state: {e}")

    # Buscar no banco
    try:
        response = (
            supabase.table("doctor_state")
            .select("*")
            .eq("cliente_id", cliente_id)
            .execute()
        )

        if response.data and len(response.data) > 0:
            row = response.data[0]
            # Salvar no cache
            try:
                await cache_set_json(cache_key, row, CACHE_TTL)
            except Exception as e:
                logger.warning(f"Erro ao salvar cache doctor_state: {e}")
            return _row_to_state(row)

        # Não existe: criar registro default
        return await create_default_state(cliente_id)

    except Exception as e:
        logger.error(f"Erro ao carregar doctor_state: {e}")
        # Retornar estado default em memória para não quebrar fluxo
        return DoctorState(
            cliente_id=cliente_id,
            permission_state=PermissionState.NONE,
        )


async def create_default_state(cliente_id: str) -> DoctorState:
    """Cria registro default para médico novo."""
    try:
        response = (
            supabase.table("doctor_state")
            .insert({"cliente_id": cliente_id})
            .execute()
        )

        if response.data and len(response.data) > 0:
            return _row_to_state(response.data[0])

    except Exception as e:
        logger.error(f"Erro ao criar doctor_state: {e}")

    return DoctorState(
        cliente_id=cliente_id,
        permission_state=PermissionState.NONE,
    )


async def save_doctor_state_updates(cliente_id: str, updates: dict) -> bool:
    """
    Salva atualizações no estado do médico.

    Args:
        cliente_id: ID do médico
        updates: Dict com campos a atualizar

    Returns:
        True se sucesso
    """
    if not updates:
        return True

    try:
        # Invalidar cache
        cache_key = f"{CACHE_PREFIX}:{cliente_id}"
        try:
            await cache_delete(cache_key)
        except Exception as e:
            logger.warning(f"Erro ao invalidar cache: {e}")

        # Atualizar banco
        response = (
            supabase.table("doctor_state")
            .update(updates)
            .eq("cliente_id", cliente_id)
            .execute()
        )

        logger.debug(f"doctor_state atualizado: {cliente_id} -> {list(updates.keys())}")
        return True

    except Exception as e:
        logger.error(f"Erro ao salvar doctor_state: {e}")
        return False


async def resolve_objection(cliente_id: str) -> bool:
    """
    Marca objeção como resolvida.

    Chamado quando:
    - Humano marca como resolvido via Slack/Chatwoot
    - Médico confirma resolução explicitamente
    - Ação pendente foi concluída
    """
    return await save_doctor_state_updates(cliente_id, {
        "objection_resolved_at": agora_utc().isoformat(),
    })


async def buscar_states_para_decay(dias_minimo: int = 1) -> list[dict]:
    """
    Busca estados que precisam de decay de temperatura.

    Args:
        dias_minimo: Mínimo de dias desde último decay

    Returns:
        Lista de rows do banco
    """
    try:
        # Buscar estados com temperatura > 0 que não tiveram decay recente
        response = (
            supabase.table("doctor_state")
            .select("cliente_id, temperature, last_inbound_at, last_decay_at")
            .neq("permission_state", "opted_out")
            .gt("temperature", 0)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Erro ao buscar states para decay: {e}")
        return []
