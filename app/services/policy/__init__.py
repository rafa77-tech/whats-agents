"""
Policy Engine - Sprint 15 + Sprint 16

Separação de DECISÃO (determinística) de EXECUÇÃO (LLM).

Componentes:
- DoctorState: Estado do relacionamento com médico
- StateUpdate: Atualiza estado baseado em eventos
- PolicyDecide: Aplica regras e decide ação
- PolicyDecision: Resultado da decisão (ação + constraints)

Sprint 16 - Observability:
- Feature Flags: Kill switch sem deploy
- Events Repository: Persistência para métricas
- Metrics: 5 queries de monitoramento
- Replay: Reprodução offline de decisões
- Orphan Detector: Detecção de decisões sem efeitos
"""

from .types import (
    # Enums
    PermissionState,
    TemperatureBand,
    TemperatureTrend,
    ObjectionSeverity,
    RiskTolerance,
    LifecycleStage,
    PrimaryAction,
    Tone,
    # Dataclasses
    DoctorState,
    PolicyDecision,
)

from .repository import (
    load_doctor_state,
    save_doctor_state_updates,
    create_default_state,
    resolve_objection,
    buscar_states_para_decay,
)

from .state_update import StateUpdate, state_updater
from .decide import PolicyDecide, policy_decide, get_policy_decision
from .version import POLICY_VERSION, get_policy_version
from .logger import log_policy_decision, log_policy_effect

# Sprint 16 - Observability
from .flags import (
    is_policy_engine_enabled,
    is_safe_mode_active,
    get_safe_mode_action,
    are_campaigns_enabled,
    is_rule_disabled,
    enable_safe_mode,
    disable_safe_mode,
    disable_policy_engine,
    enable_policy_engine,
    disable_rule,
    enable_rule,
)

from .events_repository import (
    persist_decision,
    persist_effect,
    check_effect_exists,
    get_decision_by_id,
    get_effects_for_decision,
    get_events_for_cliente,
    update_effect_interaction_id,
)

from .metrics import (
    get_decisions_count,
    get_decisions_by_rule,
    get_decisions_by_action,
    get_effects_by_type,
    get_handoff_count,
    get_decisions_per_hour,
    get_orphan_decisions,
    get_policy_summary,
)

from .replay import (
    replay_decision,
    replay_batch,
    validate_rules_change,
    ReplayResult,
)

from .orphan_detector import (
    detect_orphans,
    get_orphan_rate_trend,
    investigate_orphan,
    check_health,
    OrphanAnalysis,
)

__all__ = [
    # Enums
    "PermissionState",
    "TemperatureBand",
    "TemperatureTrend",
    "ObjectionSeverity",
    "RiskTolerance",
    "LifecycleStage",
    "PrimaryAction",
    "Tone",
    # Dataclasses
    "DoctorState",
    "PolicyDecision",
    # Repository
    "load_doctor_state",
    "save_doctor_state_updates",
    "create_default_state",
    "resolve_objection",
    "buscar_states_para_decay",
    # StateUpdate
    "StateUpdate",
    "state_updater",
    # PolicyDecide
    "PolicyDecide",
    "policy_decide",
    "get_policy_decision",
    # Version
    "POLICY_VERSION",
    "get_policy_version",
    # Logger
    "log_policy_decision",
    "log_policy_effect",
    # Sprint 16 - Flags
    "is_policy_engine_enabled",
    "is_safe_mode_active",
    "get_safe_mode_action",
    "are_campaigns_enabled",
    "is_rule_disabled",
    "enable_safe_mode",
    "disable_safe_mode",
    "disable_policy_engine",
    "enable_policy_engine",
    "disable_rule",
    "enable_rule",
    # Sprint 16 - Events Repository
    "persist_decision",
    "persist_effect",
    "check_effect_exists",
    "get_decision_by_id",
    "get_effects_for_decision",
    "get_events_for_cliente",
    "update_effect_interaction_id",
    # Sprint 16 - Metrics
    "get_decisions_count",
    "get_decisions_by_rule",
    "get_decisions_by_action",
    "get_effects_by_type",
    "get_handoff_count",
    "get_decisions_per_hour",
    "get_orphan_decisions",
    "get_policy_summary",
    # Sprint 16 - Replay
    "replay_decision",
    "replay_batch",
    "validate_rules_change",
    "ReplayResult",
    # Sprint 16 - Orphan Detector
    "detect_orphans",
    "get_orphan_rate_trend",
    "investigate_orphan",
    "check_health",
    "OrphanAnalysis",
]
