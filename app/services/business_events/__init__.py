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
from .metrics import (
    get_funnel_metrics,
    get_funnel_by_hospital,
    get_funnel_trend,
    get_top_doctors,
    get_conversion_time,
    FunnelMetrics,
)
from .alerts import (
    Alert,
    AlertType,
    AlertSeverity,
    detect_handoff_spike,
    detect_decline_spike,
    detect_conversion_drop,
    detect_all_anomalies,
    send_alert_to_slack,
    is_in_cooldown,
    set_cooldown,
    process_and_notify_alerts,
    persist_alert,
    get_recent_alerts,
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
    # Metrics
    "get_funnel_metrics",
    "get_funnel_by_hospital",
    "get_funnel_trend",
    "get_top_doctors",
    "get_conversion_time",
    "FunnelMetrics",
    # Alerts
    "Alert",
    "AlertType",
    "AlertSeverity",
    "detect_handoff_spike",
    "detect_decline_spike",
    "detect_conversion_drop",
    "detect_all_anomalies",
    "send_alert_to_slack",
    "is_in_cooldown",
    "set_cooldown",
    "process_and_notify_alerts",
    "persist_alert",
    "get_recent_alerts",
]
