"""
Policy Engine - Sprint 15

Separação de DECISÃO (determinística) de EXECUÇÃO (LLM).

Componentes:
- DoctorState: Estado do relacionamento com médico
- StateUpdate: Atualiza estado baseado em eventos
- PolicyDecide: Aplica regras e decide ação
- PolicyDecision: Resultado da decisão (ação + constraints)
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
]
