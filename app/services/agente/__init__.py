"""
Servico principal do agente Julia.

Sprint 15: Integração com Policy Engine para decisões determinísticas.
Sprint 16: Retorna policy_decision_id para fechamento do ciclo.
Sprint 17: Emissão de eventos offer_made, offer_teaser_sent (E04).
Sprint 29: Conversation Mode + Capabilities Gate (3 camadas de proteção).
Sprint 44: T02.1 - Global timeout para geração de resposta.
Sprint 58: Epic 2 - Decomposição em pacote modular.

GUARDRAIL CRITICO: Julia é INTERMEDIARIA
- Não negocia valores
- Não confirma reservas
- Conecta médico com responsável da vaga

NOTA SOBRE PATCHES: Os sub-módulos (generation, orchestrator) usam _pkg()
para acessar nomes definidos aqui via late-binding. Isso garante que
``patch("app.services.agente.gerar_resposta")`` funciona corretamente nos
testes, pois os sub-módulos consultam este namespace em runtime.
"""

# ---- Imports externos que os testes patcham em app.services.agente.X -------
# Estes DEVEM estar neste módulo para que patch() funcione.

from app.core.tasks import safe_create_task  # noqa: F401
from app.core.prompts import montar_prompt_julia  # noqa: F401

from app.services.llm import (  # noqa: F401
    LLMProvider,
    gerar_resposta,
    gerar_resposta_com_tools,
    continuar_apos_tool,
)
from app.services.interacao import converter_historico_para_messages  # noqa: F401
from app.services.conhecimento import OrquestradorConhecimento  # noqa: F401
from app.services.policy import (  # noqa: F401
    PolicyDecide,
    StateUpdate,
    load_doctor_state,
    save_doctor_state_updates,
    PrimaryAction,
    PolicyDecision,
    log_policy_decision,
    log_policy_effect,
)
from app.services.conversation_mode import (  # noqa: F401
    get_mode_router,
    CapabilitiesGate,
    ModeInfo,
)

# ---- Re-exports dos sub-módulos -------------------------------------------

from app.services.agente.types import (  # noqa: F401
    ProcessamentoResult,
    TIMEOUT_GERACAO_RESPOSTA,
    RESPOSTA_TIMEOUT_FALLBACK,
    PADROES_RESPOSTA_INCOMPLETA,
    MAX_RETRIES_INCOMPLETO,
    _resposta_parece_incompleta,
)

from app.services.agente.generation import (  # noqa: F401
    JULIA_TOOLS,
    processar_tool_call,
    gerar_resposta_julia,
    _gerar_resposta_julia_impl,
)

from app.services.agente.orchestrator import (  # noqa: F401
    processar_mensagem_completo,
    _emitir_offer_events,
)

from app.services.agente.delivery import (  # noqa: F401
    enviar_resposta,
    enviar_mensagens_sequencia,
    _emitir_fallback_event,
)
