"""
Conversation Mode - Sprint 29

Controla o modo de conversa e capabilities do agente Julia.

GUARDRAIL CRÍTICO: Julia é INTERMEDIÁRIA
- Não pode negociar valores
- Não pode confirmar reservas
- Conecta médico com responsável da vaga

3 CAMADAS DE PROTEÇÃO:
1. Tools - Backend bloqueia chamadas (filter_tools)
2. Claims - Prompt proíbe promessas (get_forbidden_claims)
3. Behavior - Prompt exige comportamento (get_required_behavior)

MODE ROUTER (3 camadas):
1. IntentDetector - Detecta intenção do médico (não decide modo)
2. TransitionProposer - Propõe transição baseado em intent + matriz
3. TransitionValidator - Valida com micro-confirmação
"""

from .types import ConversationMode, ModeInfo, ModeTransition
from .repository import (
    get_conversation_mode,
    set_conversation_mode,
    set_pending_transition,
    clear_pending_transition,
)
from .capabilities import (
    CapabilitiesGate,
    get_capabilities_gate,
    CAPABILITIES_BY_MODE,
    GLOBAL_FORBIDDEN_TOOLS,
    GLOBAL_FORBIDDEN_CLAIMS,
)
from .intents import (
    DetectedIntent,
    IntentResult,
    IntentDetector,
)
from .proposer import (
    TransitionProposal,
    TransitionProposer,
    ALLOWED_TRANSITIONS,
    CONFIRMATION_REQUIRED,
    AUTOMATIC_TRANSITIONS,
)
from .validator import (
    TransitionDecision,
    ValidationResult,
    TransitionValidator,
)
from .router import (
    ModeRouter,
    get_mode_router,
)
from .bootstrap import (
    bootstrap_mode,
    get_mode_source,
)
from .mode_logging import (
    ModeDecisionLog,
    log_mode_decision,
    log_violation_attempt,
    log_transition_applied,
    log_pending_created,
    log_pending_resolved,
    get_capabilities_version,
)
from .prompts import (
    get_micro_confirmation_prompt,
    MICRO_CONFIRMATION_PROMPTS,
)
from .response_validator import (
    validar_resposta_julia,
    sanitizar_resposta_julia,
    get_fallback_response,
    PADROES_PROIBIDOS,
)

__all__ = [
    # Types
    "ConversationMode",
    "ModeInfo",
    "ModeTransition",
    # Repository
    "get_conversation_mode",
    "set_conversation_mode",
    "set_pending_transition",
    "clear_pending_transition",
    # Capabilities (3 camadas)
    "CapabilitiesGate",
    "get_capabilities_gate",
    "CAPABILITIES_BY_MODE",
    "GLOBAL_FORBIDDEN_TOOLS",
    "GLOBAL_FORBIDDEN_CLAIMS",
    # Intent Detection
    "DetectedIntent",
    "IntentResult",
    "IntentDetector",
    # Transition Proposer
    "TransitionProposal",
    "TransitionProposer",
    "ALLOWED_TRANSITIONS",
    "CONFIRMATION_REQUIRED",
    "AUTOMATIC_TRANSITIONS",
    # Transition Validator
    "TransitionDecision",
    "ValidationResult",
    "TransitionValidator",
    # Mode Router
    "ModeRouter",
    "get_mode_router",
    # Bootstrap
    "bootstrap_mode",
    "get_mode_source",
    # Logging
    "ModeDecisionLog",
    "log_mode_decision",
    "log_violation_attempt",
    "log_transition_applied",
    "log_pending_created",
    "log_pending_resolved",
    "get_capabilities_version",
    # Prompts
    "get_micro_confirmation_prompt",
    "MICRO_CONFIRMATION_PROMPTS",
    # Response Validator
    "validar_resposta_julia",
    "sanitizar_resposta_julia",
    "get_fallback_response",
    "PADROES_PROIBIDOS",
]
