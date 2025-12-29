"""
Modulo de eventos de negocio.

Sprint 17 - E02, E04, E05, E08
"""
from .repository import (
    emit_event,
    get_events_by_type,
    get_events_for_cliente,
    get_events_for_vaga,
    get_funnel_counts,
)
from .types import BusinessEvent, EventType, EventSource
from .validators import vaga_pode_receber_oferta
from .context import extrair_vagas_do_contexto, tem_mencao_oportunidade
from .rollout import (
    should_emit_event,
    get_rollout_status,
    add_to_allowlist,
    get_canary_config,
)
from .recusa_detector import (
    detectar_recusa,
    processar_possivel_recusa,
    buscar_ultima_oferta,
    RecusaResult,
)

__all__ = [
    # Repository
    "emit_event",
    "get_events_by_type",
    "get_events_for_cliente",
    "get_events_for_vaga",
    "get_funnel_counts",
    # Types
    "BusinessEvent",
    "EventType",
    "EventSource",
    # Validators
    "vaga_pode_receber_oferta",
    # Context helpers
    "extrair_vagas_do_contexto",
    "tem_mencao_oportunidade",
    # Rollout
    "should_emit_event",
    "get_rollout_status",
    "add_to_allowlist",
    "get_canary_config",
    # Recusa detector
    "detectar_recusa",
    "processar_possivel_recusa",
    "buscar_ultima_oferta",
    "RecusaResult",
]
