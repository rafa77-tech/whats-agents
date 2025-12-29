# Epic 04: Emissores Backend

## Objetivo

Instrumentar o código Python para emitir eventos de negócio que não podem ser capturados via triggers DB.

## Contexto

### Eventos via Backend

| Evento | Onde Emitir | Condição |
|--------|-------------|----------|
| `doctor_inbound` | Webhook recebimento | Mensagem do médico |
| `doctor_outbound` | Envio de mensagem | Mensagem enviada |
| `offer_teaser_sent` | Agente Julia | Menciona oportunidade sem vaga_id |
| `offer_made` | Policy effect | `primary_action=OFFER` + `vaga_id` |
| `handoff_created` | `criar_handoff()` | Sempre que cria handoff |

### Princípio: Mínima Invasão

- Emitir em pontos naturais do fluxo
- Não criar novos fluxos só para eventos
- Usar `asyncio.create_task` para não bloquear

---

## Story 4.1: Eventos de Mensagem (inbound/outbound)

### Objetivo
Emitir `doctor_inbound` e `doctor_outbound` no fluxo de mensagens.

### Tarefas

1. **Emitir doctor_inbound** no webhook de mensagens:

```python
# app/api/routes/webhook.py

from app.services.business_events import emit_event, BusinessEvent, EventType

async def process_incoming_message(message_data: dict):
    """Processa mensagem recebida do WhatsApp."""
    cliente_id = message_data.get("cliente_id")
    conversation_id = message_data.get("conversation_id")

    # Emitir evento de negócio (não bloqueia)
    asyncio.create_task(
        emit_event(BusinessEvent(
            event_type=EventType.DOCTOR_INBOUND,
            cliente_id=cliente_id,
            conversation_id=conversation_id,
            event_props={
                "message_type": message_data.get("type", "text"),
                "has_media": message_data.get("has_media", False),
            },
        ))
    )

    # ... resto do processamento
```

2. **Emitir doctor_outbound** no envio de mensagens:

```python
# app/services/whatsapp/sender.py

from app.services.business_events import emit_event, BusinessEvent, EventType

async def enviar_mensagem(
    telefone: str,
    mensagem: str,
    cliente_id: str = None,
    conversation_id: str = None,
) -> bool:
    """Envia mensagem via WhatsApp."""
    # Enviar
    result = await _send_via_evolution(telefone, mensagem)

    if result and cliente_id:
        # Emitir evento de negócio
        asyncio.create_task(
            emit_event(BusinessEvent(
                event_type=EventType.DOCTOR_OUTBOUND,
                cliente_id=cliente_id,
                conversation_id=conversation_id,
                event_props={
                    "message_length": len(mensagem),
                },
            ))
        )

    return result
```

### DoD

- [ ] `doctor_inbound` emitido para toda mensagem recebida
- [ ] `doctor_outbound` emitido para toda mensagem enviada
- [ ] Eventos não bloqueiam o fluxo principal
- [ ] `event_props` contém metadata relevante

---

## Story 4.2: Eventos de Oferta (offer_teaser, offer_made)

### Objetivo
Emitir eventos de oferta baseado na ação do policy engine.

### Contexto

| Cenário | Evento |
|---------|--------|
| Julia menciona "temos vagas" (genérico) | `offer_teaser_sent` |
| Julia oferece vaga específica (com vaga_id) | `offer_made` |

### Trava de Segurança (Recomendação do Professor)

**`offer_made` só emite se:**
- Tiver `vaga_id`
- Vaga estiver com status `anunciada` ou `aberta`

Isso evita "offer_made duplicado" em vaga já reservada/cancelada.

### Tarefas

1. **Criar helper de validação de vaga**:

```python
# app/services/business_events/validators.py

from app.services.supabase import supabase
import logging

logger = logging.getLogger(__name__)

VALID_STATUS_FOR_OFFER = ("aberta", "anunciada")


async def vaga_pode_receber_oferta(vaga_id: str) -> bool:
    """
    Verifica se vaga pode receber offer_made.

    Args:
        vaga_id: UUID da vaga

    Returns:
        True se vaga está aberta ou anunciada
    """
    try:
        response = (
            supabase.table("vagas")
            .select("status")
            .eq("id", vaga_id)
            .single()
            .execute()
        )

        if not response.data:
            logger.warning(f"Vaga não encontrada para offer_made: {vaga_id}")
            return False

        status = response.data.get("status")
        if status not in VALID_STATUS_FOR_OFFER:
            logger.info(
                f"offer_made ignorado: vaga {vaga_id[:8]} "
                f"está {status} (esperado: {VALID_STATUS_FOR_OFFER})"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Erro ao validar vaga para offer_made: {e}")
        return False  # Fail closed: na dúvida, não emite
```

2. **Detectar e emitir no policy effect (com validação)**:

```python
# app/services/policy/executor.py

from app.services.business_events import emit_event, BusinessEvent, EventType, EventSource
from app.services.business_events.validators import vaga_pode_receber_oferta

async def execute_policy_decision(
    decision: PolicyDecision,
    context: dict,
) -> ExecutionResult:
    """Executa a decisão do policy engine."""

    # Se ação é OFFER, emitir evento apropriado
    if decision.primary_action == PrimaryAction.OFFER:
        vaga_id = context.get("vaga_id")

        if vaga_id:
            # TRAVA: só emite se vaga estiver aberta/anunciada
            if await vaga_pode_receber_oferta(vaga_id):
                asyncio.create_task(
                    emit_event(BusinessEvent(
                        event_type=EventType.OFFER_MADE,
                        source=EventSource.BACKEND,
                        cliente_id=context.get("cliente_id"),
                        vaga_id=vaga_id,
                        hospital_id=context.get("hospital_id"),
                        conversation_id=context.get("conversation_id"),
                        policy_decision_id=context.get("policy_decision_id"),
                        event_props={
                            "valor": context.get("valor"),
                            "data_plantao": context.get("data_plantao"),
                            "especialidade": context.get("especialidade"),
                        },
                    ))
                )
        else:
            # Menção genérica de oportunidade (sem vaga específica)
            asyncio.create_task(
                emit_event(BusinessEvent(
                    event_type=EventType.OFFER_TEASER_SENT,
                    source=EventSource.BACKEND,
                    cliente_id=context.get("cliente_id"),
                    conversation_id=context.get("conversation_id"),
                    policy_decision_id=context.get("policy_decision_id"),
                    event_props={
                        "tipo_abordagem": context.get("tipo_abordagem", "discovery"),
                    },
                ))
            )

    # ... resto da execução
```

2. **Alternativa: Emitir no agente.py após usar tool buscar_vagas**:

```python
# app/services/agente.py

# Após tool_call de buscar_vagas retornar com vaga_id
if tool_name == "buscar_vagas" and tool_result.get("vagas"):
    for vaga in tool_result["vagas"]:
        # Marcar que esta vaga foi oferecida
        # O evento será emitido quando a mensagem for enviada
        context["vagas_oferecidas"].append(vaga["id"])

# No final, ao enviar mensagem com oferta:
if context.get("vagas_oferecidas"):
    for vaga_id in context["vagas_oferecidas"]:
        asyncio.create_task(
            emit_event(BusinessEvent(
                event_type=EventType.OFFER_MADE,
                cliente_id=cliente_id,
                vaga_id=vaga_id,
                conversation_id=conversation_id,
            ))
        )
```

### DoD

- [ ] `offer_made` emitido quando Julia oferece vaga específica
- [ ] `offer_teaser_sent` emitido quando menciona oportunidades sem vaga_id
- [ ] `policy_decision_id` linkado quando disponível
- [ ] `vaga_id` e `hospital_id` preenchidos corretamente

---

## Story 4.3: Evento handoff_created

### Objetivo
Emitir `handoff_created` quando um handoff é criado.

### Tarefas

1. **Emitir no criar_handoff**:

```python
# app/services/handoff.py

from app.services.business_events import emit_event, BusinessEvent, EventType

async def criar_handoff(
    cliente_id: str,
    conversation_id: str,
    motivo: str,
    policy_decision_id: str = None,
    **kwargs,
) -> dict:
    """Cria um handoff para atendimento humano."""

    # Criar handoff no banco
    handoff = await _insert_handoff(
        cliente_id=cliente_id,
        conversation_id=conversation_id,
        motivo=motivo,
        **kwargs,
    )

    # Emitir evento de negócio
    asyncio.create_task(
        emit_event(BusinessEvent(
            event_type=EventType.HANDOFF_CREATED,
            cliente_id=cliente_id,
            conversation_id=conversation_id,
            policy_decision_id=policy_decision_id,
            event_props={
                "motivo": motivo,
                "handoff_id": handoff.get("id"),
                "prioridade": kwargs.get("prioridade", "normal"),
            },
        ))
    )

    # ... notificar Slack, etc
    return handoff
```

### DoD

- [ ] `handoff_created` emitido em todo criar_handoff
- [ ] `motivo` incluído em event_props
- [ ] `policy_decision_id` linkado quando disponível
- [ ] Não bloqueia o fluxo principal

---

## Story 4.4: Helper para Contexto de Vaga

### Objetivo
Criar helper para extrair vaga_id do contexto da conversa.

### Contexto

O agente Julia pode mencionar vagas de várias formas:
1. Após tool call `buscar_vagas`
2. Após tool call `reservar_plantao`
3. Mencionando vaga do contexto anterior

### Tarefas

1. **Criar helper de extração**:

```python
# app/services/business_events/context.py

from typing import Optional, List

def extrair_vagas_do_contexto(
    tool_calls: List[dict],
    resposta_agente: str,
) -> List[str]:
    """
    Extrai vaga_ids do contexto da interação.

    Args:
        tool_calls: Lista de tool calls feitos pelo agente
        resposta_agente: Resposta final do agente

    Returns:
        Lista de vaga_ids mencionados/oferecidos
    """
    vaga_ids = []

    # 1. Extrair de tool calls
    for call in tool_calls:
        if call.get("name") == "buscar_vagas":
            result = call.get("result", {})
            for vaga in result.get("vagas", []):
                if vaga.get("id"):
                    vaga_ids.append(vaga["id"])

        elif call.get("name") == "reservar_plantao":
            result = call.get("result", {})
            if result.get("vaga_id"):
                vaga_ids.append(result["vaga_id"])

    return list(set(vaga_ids))  # Dedupe


def tem_mencao_oportunidade(resposta: str) -> bool:
    """
    Verifica se a resposta menciona oportunidades genéricas.

    Usado para decidir entre offer_made vs offer_teaser_sent.
    """
    termos = [
        "temos vagas",
        "temos oportunidades",
        "surgiu uma vaga",
        "apareceu plantão",
        "tem interesse",
        "posso te passar",
    ]

    resposta_lower = resposta.lower()
    return any(termo in resposta_lower for termo in termos)
```

### DoD

- [ ] Helper `extrair_vagas_do_contexto` implementado
- [ ] Helper `tem_mencao_oportunidade` implementado
- [ ] Testes unitários para ambos
- [ ] Usado nos emissores de offer_*

---

## Checklist do Épico

- [ ] **S17.E04.1** - Eventos inbound/outbound
- [ ] **S17.E04.2** - Eventos offer_teaser/offer_made
- [ ] **S17.E04.3** - Evento handoff_created
- [ ] **S17.E04.4** - Helpers de contexto
- [ ] Todos eventos emitidos com asyncio.create_task
- [ ] Eventos não bloqueiam fluxo principal
- [ ] policy_decision_id linkado quando aplicável
- [ ] Testes de integração passando
