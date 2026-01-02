# E04: Integração no Agente

**Status:** Pendente
**Estimativa:** 6h
**Dependencia:** E01, E02, E03
**Responsavel:** Dev

---

## Objetivo

Integrar o Conversation Mode no fluxo existente do agente Julia, plugando entre o Policy Engine (Sprint 15) e a geração de resposta.

Inclui:
- Mode Router com micro-confirmação
- Capabilities Gate com 3 camadas
- Injeção de constraints no prompt

---

## Fluxo Atualizado

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEBHOOK (mensagem recebida)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. VERIFICAR CONTROLE (IA vs humano) [existente]              │
│        │                                                         │
│        ▼                                                         │
│   2. CARREGAR CONTEXTO + doctor_state [existente]               │
│        │                                                         │
│        ▼                                                         │
│   3. POLICY ENGINE (Sprint 15) [existente]                      │
│      - Verificar opt-out, cooling_off, objeção grave            │
│      - SE bloqueado → parar aqui                                │
│        │                                                         │
│        ▼ (passou)                                                │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 4. MODE ROUTER [NOVO - Sprint 29]                       │   │
│   │                                                          │   │
│   │    4a. Detectar intent (não decide modo)                │   │
│   │    4b. Propor transição (validar contra matriz)         │   │
│   │    4c. Validar transição:                               │   │
│   │        - Se automática → aplicar                        │   │
│   │        - Se requer confirmação → salvar pending         │   │
│   │        - Se há pending → verificar confirmação          │   │
│   │    4d. Atualizar conversation_mode se aceito            │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ 5. CAPABILITIES GATE [NOVO - Sprint 29]                 │   │
│   │                                                          │   │
│   │    5a. Filtrar tools por modo atual (camada 1)          │   │
│   │    5b. Gerar forbidden_claims (camada 2)                │   │
│   │    5c. Gerar required_behavior (camada 3)               │   │
│   │    5d. Verificar se há pending_transition               │   │
│   │        → Se sim, adicionar prompt de micro-confirmação  │   │
│   │                                                          │   │
│   └─────────────────────────────────────────────────────────┘   │
│        │                                                         │
│        ▼                                                         │
│   6. GERAR RESPOSTA (LLM) [existente - modificado]              │
│      - Usar tools filtradas                                     │
│      - Injetar constraints do modo (3 camadas)                  │
│      - Se pending: incluir prompt de micro-confirmação          │
│        │                                                         │
│        ▼                                                         │
│   7. ENVIAR WHATSAPP [existente]                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prompt de Micro-Confirmação (INTERMEDIAÇÃO)

**REGRA CRÍTICA:** A micro-confirmação é sobre **CONECTAR COM RESPONSÁVEL**, não sobre reservar.

Quando há `pending_transition`, o prompt inclui instruções para fazer micro-confirmação:

```python
MICRO_CONFIRMATION_PROMPTS = {
    # discovery → oferta (intermediação)
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA): (
        "O médico mostrou interesse em vagas. LEMBRE-SE: você é INTERMEDIÁRIA.\n"
        "- Você NÃO é dona das vagas\n"
        "- Você NÃO negocia valores\n"
        "- Você NÃO confirma reservas\n\n"
        "Seu objetivo é CONECTAR o médico com o responsável pela vaga.\n\n"
        "Antes de mostrar vagas, faça UMA pergunta de qualificação:\n"
        "- \"Que legal! Só pra eu ver melhor pra vc - vc já tem CRM ativo em SP?\"\n"
        "- \"Show! Vc tá procurando mais fixo ou avulso?\"\n"
        "- \"Boa! Qual região vc prefere pra plantão?\"\n"
        "NÃO mostre vagas ainda. Aguarde a resposta."
    ),

    # followup → oferta (verificar desfecho ou nova oportunidade)
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA): (
        "O médico pode estar interessado em nova oportunidade.\n"
        "LEMBRE-SE: você é INTERMEDIÁRIA - não negocie nem confirme.\n\n"
        "Confirme o interesse antes de conectar:\n"
        "- \"Surgiu uma vaga interessante - quer que eu te coloque em contato com o responsável?\"\n"
        "- \"Lembrei de vc pq abriu uma boa, quer ver os detalhes?\"\n"
        "NÃO apresente a vaga ainda. Aguarde confirmação."
    ),
}
```

---

## Modificações Necessárias

### 1. `app/services/agente.py`

```python
# Adicionar imports
from app.services.conversation_mode import (
    get_mode_router,
    CapabilitiesGate,
    ConversationMode,
)
from app.services.conversation_mode.repository import get_conversation_mode
from app.services.conversation_mode.validator import TransitionDecision


async def processar_mensagem_completo(
    mensagem_texto: str,
    medico: dict,
    conversa: dict,
    vagas: list[dict] = None
) -> Optional[str]:
    """
    Processa mensagem completa com Policy Engine + Conversation Mode.
    """
    # 1-3. Verificações existentes (controle, contexto, policy)
    # [código existente sem modificação]

    # Após PolicyDecide, se não bloqueou:

    # 4. MODE ROUTER [NOVO]
    mode_router = get_mode_router()
    mode_info = await mode_router.process(
        conversa_id=conversa["id"],
        mensagem=mensagem_texto,
        last_message_at=conversa.get("last_message_at"),
        reserva_confirmada=contexto.get("reserva_confirmada", False),
        objecao_resolvida=objecao_dict.get("resolvida", False) if objecao_dict else False,
    )

    # 5. CAPABILITIES GATE [NOVO]
    capabilities_gate = CapabilitiesGate(mode_info.mode)

    # 6. Gerar resposta com tools filtradas
    resposta = await gerar_resposta_julia(
        mensagem_texto,
        contexto,
        medico=medico,
        conversa=conversa,
        policy_decision=decision,
        capabilities_gate=capabilities_gate,  # NOVO
        mode_info=mode_info,  # NOVO: para micro-confirmação
    )

    return resposta
```

### 2. `app/services/agente.py` - Função `gerar_resposta_julia`

```python
from app.services.conversation_mode.types import ModeInfo

# Prompts de micro-confirmação
MICRO_CONFIRMATION_PROMPTS = {
    (ConversationMode.DISCOVERY, ConversationMode.OFERTA): (
        "\n\n## ATENÇÃO: MICRO-CONFIRMAÇÃO NECESSÁRIA\n"
        "O médico mostrou interesse em vagas, mas ANTES de oferecer:\n"
        "1. Faça UMA pergunta de qualificação\n"
        "2. NÃO mencione vagas específicas ainda\n"
        "3. Aguarde a resposta antes de transicionar\n\n"
        "Exemplos de micro-confirmação:\n"
        "- \"Que legal! Só pra eu entender melhor - vc já tem CRM ativo em SP?\"\n"
        "- \"Show! Vc tá procurando mais fixo ou avulso?\"\n"
        "- \"Boa! Qual região vc prefere?\""
    ),
    (ConversationMode.FOLLOWUP, ConversationMode.OFERTA): (
        "\n\n## ATENÇÃO: MICRO-CONFIRMAÇÃO NECESSÁRIA\n"
        "O médico pode estar interessado em nova oportunidade. ANTES de oferecer:\n"
        "1. Pergunte se quer ver os detalhes\n"
        "2. NÃO apresente a vaga ainda\n\n"
        "Exemplos:\n"
        "- \"Surgiu uma vaga interessante - quer que eu mande os detalhes?\"\n"
        "- \"Lembrei de vc pq abriu uma boa, quer ver?\""
    ),
}


async def gerar_resposta_julia(
    mensagem: str,
    contexto: dict,
    medico: dict,
    conversa: dict,
    incluir_historico: bool = True,
    usar_tools: bool = True,
    policy_decision: PolicyDecision = None,
    capabilities_gate: CapabilitiesGate = None,  # NOVO
    mode_info: ModeInfo = None,  # NOVO
) -> str:
    """Gera resposta da Julia com capabilities filtradas."""

    # Obter todas as tools
    all_tools = get_all_julia_tools()

    # NOVO: Filtrar tools pelo modo (CAMADA 1)
    if capabilities_gate:
        filtered_tools = capabilities_gate.filter_tools(all_tools)
    else:
        filtered_tools = all_tools

    # Montar constraints combinados
    constraints_parts = []

    # Constraints da Policy Engine (Sprint 15)
    if policy_decision and policy_decision.constraints_text:
        constraints_parts.append(policy_decision.constraints_text)

    # NOVO: Constraints do Conversation Mode (3 CAMADAS)
    if capabilities_gate:
        mode_constraints = capabilities_gate.get_constraints_text()
        if mode_constraints:
            constraints_parts.append(mode_constraints)

    # NOVO: Prompt de micro-confirmação se há pending_transition
    if mode_info and mode_info.pending_transition:
        transition_key = (mode_info.mode, mode_info.pending_transition)
        if transition_key in MICRO_CONFIRMATION_PROMPTS:
            constraints_parts.append(MICRO_CONFIRMATION_PROMPTS[transition_key])

    combined_constraints = "\n\n---\n\n".join(constraints_parts)

    # Montar prompt
    system_prompt = await montar_prompt_julia(
        # ... parâmetros existentes ...
        policy_constraints=combined_constraints,  # Usa combined
    )

    # Chamar LLM com tools filtradas
    resposta = await chamar_claude(
        system_prompt=system_prompt,
        mensagem=mensagem,
        historico=historico,
        tools=filtered_tools,  # NOVO: tools filtradas
    )

    return resposta
```

### 3. Atualizar `types.py` do módulo

```python
# app/services/conversation_mode/types.py

"""
Tipos do Conversation Mode.
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class ConversationMode(Enum):
    """Modos de conversa."""
    DISCOVERY = "discovery"      # Conhecer o médico
    OFERTA = "oferta"            # Oferecer vaga
    FOLLOWUP = "followup"        # Dar continuidade
    REATIVACAO = "reativacao"    # Reativar inativo


@dataclass
class ModeInfo:
    """Informações do modo atual de uma conversa."""
    conversa_id: str
    mode: ConversationMode
    updated_at: Optional[datetime] = None
    updated_reason: Optional[str] = None
    mode_source: Optional[str] = None  # NOVO: inbound, campaign:<id>, manual
    pending_transition: Optional[ConversationMode] = None  # NOVO
    pending_transition_at: Optional[datetime] = None  # NOVO

    @classmethod
    def from_row(cls, row: dict) -> "ModeInfo":
        """Cria ModeInfo a partir de row do banco."""
        pending = row.get("pending_transition")
        return cls(
            conversa_id=row["id"],
            mode=ConversationMode(row.get("conversation_mode", "discovery")),
            updated_at=row.get("mode_updated_at"),
            updated_reason=row.get("mode_updated_reason"),
            mode_source=row.get("mode_source"),
            pending_transition=ConversationMode(pending) if pending else None,
            pending_transition_at=row.get("pending_transition_at"),
        )


@dataclass
class ModeTransition:
    """Representa uma transição de modo."""
    from_mode: ConversationMode
    to_mode: ConversationMode
    reason: str
    confidence: float  # 0.0 a 1.0
    evidence: str  # Texto/sinal que motivou
```

### 4. Atualizar `__init__.py` do módulo

```python
# app/services/conversation_mode/__init__.py

from .types import ConversationMode, ModeInfo, ModeTransition
from .capabilities import CapabilitiesGate, get_capabilities_gate, CAPABILITIES_BY_MODE
from .intents import IntentDetector, DetectedIntent, IntentResult
from .proposer import TransitionProposer, TransitionProposal, ALLOWED_TRANSITIONS
from .validator import TransitionValidator, TransitionDecision, ValidationResult
from .router import ModeRouter, get_mode_router
from .repository import (
    get_conversation_mode,
    set_conversation_mode,
    set_pending_transition,
    clear_pending_transition,
)

__all__ = [
    # Types
    "ConversationMode",
    "ModeInfo",
    "ModeTransition",
    # Capabilities (Camada 1, 2, 3)
    "CapabilitiesGate",
    "get_capabilities_gate",
    "CAPABILITIES_BY_MODE",
    # Intent Detection
    "IntentDetector",
    "DetectedIntent",
    "IntentResult",
    # Transition Proposal
    "TransitionProposer",
    "TransitionProposal",
    "ALLOWED_TRANSITIONS",
    # Validation
    "TransitionValidator",
    "TransitionDecision",
    "ValidationResult",
    # Router
    "ModeRouter",
    "get_mode_router",
    # Repository
    "get_conversation_mode",
    "set_conversation_mode",
    "set_pending_transition",
    "clear_pending_transition",
]
```

---

## Fluxo de Micro-Confirmação (Exemplo Prático - INTERMEDIAÇÃO)

```
┌────────────────────────────────────────────────────────────────────┐
│ EXEMPLO: Médico em DISCOVERY pergunta sobre vagas                   │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 1. Médico: "Oi, vocês tem plantão de cardio?"                      │
│                                                                     │
│    Mode Router:                                                     │
│    - Intent detectado: INTERESSE_VAGA                               │
│    - Proposta: discovery → oferta                                   │
│    - Requer confirmação? SIM (connect_to_owner_confirm)             │
│    - Decisão: PENDING                                               │
│    - Salva: pending_transition = 'oferta'                          │
│                                                                     │
│    Capabilities Gate:                                               │
│    - Modo atual: DISCOVERY (não mudou ainda)                        │
│    - Tools: bloqueia buscar_vagas, criar_handoff_externo           │
│    - Adiciona prompt de micro-confirmação                          │
│                                                                     │
│    Julia responde:                                                  │
│    "Temos sim! Só pra eu ver melhor pra vc - vc prefere            │
│     plantão noturno ou diurno?"                                    │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 2. Médico: "Noturno, por favor"                                    │
│                                                                     │
│    Mode Router:                                                     │
│    - Intent detectado: NEUTRO                                       │
│    - Pending existe? SIM (oferta)                                   │
│    - Mensagem confirma? SIM ("noturno" = resposta à pergunta)      │
│    - Decisão: CONFIRM                                               │
│    - Aplica: conversation_mode = 'oferta'                          │
│    - Limpa: pending_transition = NULL                              │
│                                                                     │
│    Capabilities Gate:                                               │
│    - Modo atual: OFERTA (transicionou!)                             │
│    - Tools: permite buscar_vagas, criar_handoff_externo            │
│    - Constraints de OFERTA (intermediação)                          │
│                                                                     │
│    Julia responde:                                                  │
│    "Boa! Deixa eu ver aqui... Tem um plantão noturno no            │
│     São Luiz dia 15. Quer que eu te coloque em contato com         │
│     o responsável da vaga pra vocês acertarem os detalhes?"        │
│                                                                     │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│ 3. Médico: "Sim, pode passar"                                      │
│                                                                     │
│    Julia chama: criar_handoff_externo(vaga_id, medico_id)           │
│    Julia chama: registrar_status_intermediacao("contatado")         │
│                                                                     │
│    Julia responde:                                                  │
│    "Show! Passei seu contato pro Dr. Paulo que tá com a vaga.      │
│     Ele vai te chamar pra acertar os detalhes. Qualquer coisa      │
│     me avisa aqui como foi!"                                        │
│                                                                     │
│    Mode Router:                                                     │
│    - Transição: oferta → followup (ponte feita)                    │
│    - Status: aguardando_desfecho                                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Funil de Intermediação (Não é "Reserva")

**Mudança de paradigma:** O funil NÃO é "reserva confirmada". É "intermediação até desfecho".

### Estados do Funil

```
┌─────────────────────────────────────────────────────────────────┐
│                    FUNIL DE INTERMEDIAÇÃO                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. interesse_confirmado                                        │
│      └── Médico disse que quer ver vagas                        │
│      └── Status: qualificando                                    │
│                                                                  │
│   2. ponte_feita                                                 │
│      └── Julia conectou médico com responsável                  │
│      └── criar_handoff_externo() chamado                        │
│      └── Status: contatado                                       │
│                                                                  │
│   3. aguardando_desfecho                                         │
│      └── Médico e responsável estão conversando                 │
│      └── Julia faz follow-up após 24-48h                        │
│      └── Status: aguardando                                      │
│                                                                  │
│   4. desfecho                                                    │
│      ├── fechado_com_responsavel                                │
│      │   └── Médico confirmou que fechou                        │
│      │   └── Status: convertido                                  │
│      ├── nao_fechou                                              │
│      │   └── Médico disse que não rolou                         │
│      │   └── Julia oferece alternativas                         │
│      │   └── Status: nao_convertido                              │
│      └── sem_resposta                                            │
│          └── Médico não respondeu follow-up                     │
│          └── Status: sem_resposta                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Logging do Funil

```python
# Exemplo de log estruturado
{
    "event": "intermediacao_status",
    "conversa_id": "xxx",
    "vaga_id": "yyy",
    "medico_id": "zzz",
    "status": "ponte_feita",  # ou outro estado
    "responsavel_id": "www",
    "timestamp": "2025-01-02T10:30:00Z",
    "metadata": {
        "tempo_ate_ponte": "15min",
        "origem_vaga": "grupo_whatsapp",
    }
}
```

### Métricas de Sucesso (Intermediação)

| Métrica | Descrição | Meta |
|---------|-----------|------|
| Taxa de ponte | % de interessados que viraram ponte | > 60% |
| Taxa de conversão | % de pontes que fecharam | > 30% |
| Tempo até ponte | Tempo médio do interesse até ponte | < 10min |
| Taxa de follow-up | % de follow-ups feitos | 100% |

---

## Log de Auditoria

Cada processamento gera logs estruturados:

```python
# Exemplo de logs
logger.info(f"Mode Router - conversa={conversa_id}")
logger.debug(f"  Intent: {intent_result.intent.value} (conf={intent_result.confidence:.2f})")
logger.debug(f"  Proposta: {proposal.from_mode.value} → {proposal.to_mode.value if proposal.to_mode else 'none'}")
logger.debug(f"  Decisão: {validation.decision.value}")
logger.info(f"  Modo final: {mode_info.mode.value}")

# Se houve transição
if validation.decision in (TransitionDecision.APPLY, TransitionDecision.CONFIRM):
    logger.info(f"  TRANSIÇÃO: {proposal.from_mode.value} → {validation.final_mode.value}")
    logger.info(f"  Razão: {validation.reason}")

# Se ficou pending
if validation.decision == TransitionDecision.PENDING:
    logger.info(f"  PENDING: aguardando confirmação para {validation.pending_mode.value}")

# Capabilities aplicadas
logger.debug(f"Capabilities Gate - modo={mode_info.mode.value}")
logger.debug(f"  Tools removidas: {len(all_tools) - len(filtered_tools)}")
logger.debug(f"  Claims proibidos: {capabilities_gate.get_forbidden_claims()}")
```

---

## DoD (Definition of Done)

### Integração

- [ ] `processar_mensagem_completo` chama `mode_router.process()`
- [ ] `processar_mensagem_completo` cria `CapabilitiesGate`
- [ ] `gerar_resposta_julia` recebe `capabilities_gate` e `mode_info`
- [ ] Tools são filtradas antes de enviar ao LLM (camada 1)
- [ ] Constraints do modo são injetados no prompt (camadas 2 e 3)
- [ ] Constraints combinam Policy Engine + Conversation Mode
- [ ] Prompt de micro-confirmação injetado quando há pending

### Micro-Confirmação

- [ ] Quando transição requer confirmação, pending é salvo
- [ ] Prompt inclui instruções de micro-confirmação
- [ ] Na resposta positiva, pending é confirmado e modo transiciona
- [ ] Na resposta negativa/objeção, pending é cancelado
- [ ] Pending expira após 30 minutos

### Logs e Auditoria

- [ ] Log de intent detectado
- [ ] Log de proposta de transição
- [ ] Log de decisão (APPLY, PENDING, CONFIRM, CANCEL, REJECT)
- [ ] Log de tools removidas pelo gate
- [ ] Log do modo atual em cada mensagem

### Testes de Integração

- [ ] Teste: conversa em discovery não usa `buscar_vagas`
  ```python
  async def test_discovery_mode_blocks_vagas():
      # Setup conversa em modo discovery
      await set_conversation_mode(conversa_id, ConversationMode.DISCOVERY, "test")

      # Processar mensagem que pediria vagas
      resposta = await processar_mensagem_completo(
          "Tem alguma vaga pra mim?",
          medico, conversa, []
      )

      # Verificar que buscar_vagas não foi chamada
      # (verificar via mock ou log)
  ```

- [ ] Teste: transição discovery → oferta requer micro-confirmação
  ```python
  async def test_discovery_to_oferta_needs_confirmation():
      # Setup conversa em discovery
      await set_conversation_mode(conversa_id, ConversationMode.DISCOVERY, "test")

      # Processar mensagem com interesse
      await processar_mensagem_completo(
          "Quero saber de vagas!",
          medico, conversa, []
      )

      # Verificar que pending foi salvo, não transitou ainda
      mode_info = await get_conversation_mode(conversa_id)
      assert mode_info.mode == ConversationMode.DISCOVERY
      assert mode_info.pending_transition == ConversationMode.OFERTA
  ```

- [ ] Teste: confirmação de pending transiciona modo
  ```python
  async def test_confirmation_transitions_mode():
      # Setup com pending
      await set_conversation_mode(conversa_id, ConversationMode.DISCOVERY, "test")
      await set_pending_transition(conversa_id, ConversationMode.OFERTA)

      # Processar mensagem que confirma
      await processar_mensagem_completo(
          "Sim, tenho CRM ativo",
          medico, conversa, []
      )

      # Verificar transição
      mode_info = await get_conversation_mode(conversa_id)
      assert mode_info.mode == ConversationMode.OFERTA
      assert mode_info.pending_transition is None
  ```

### Validação Manual

- [ ] Enviar mensagem de teste em cada modo
- [ ] Verificar que constraints aparecem no prompt
- [ ] Verificar que tools bloqueadas não são oferecidas ao LLM
- [ ] Testar fluxo completo de micro-confirmação
- [ ] Verificar logs de auditoria

### Não fazer neste epic

- [ ] NÃO modificar endpoints de API
- [ ] NÃO adicionar UI/dashboard
- [ ] NÃO fazer rollout gradual (feature flag) - isso é opcional

---

## Feature Flag (Opcional)

Para rollout gradual, pode-se adicionar feature flag:

```python
from app.services.policy.flags import get_flag

# No processar_mensagem_completo
if get_flag("conversation_mode_enabled"):
    # Usar Conversation Mode
    mode_router = get_mode_router()
    mode_info = await mode_router.process(...)
    capabilities_gate = CapabilitiesGate(mode_info.mode)
else:
    # Fallback: sem filtro de capabilities
    capabilities_gate = None
    mode_info = None
```

---

## Rollback

Se precisar reverter:

1. Remover chamadas a `mode_router` e `capabilities_gate`
2. Remover parâmetro `capabilities_gate` e `mode_info` de `gerar_resposta_julia`
3. Usar `all_tools` direto sem filtro
4. Deploy

O banco permanece com os campos, mas código não os usa.

---

## Próximo

Após E04 concluído: [E05: Testes](./epic-05-testes.md)
