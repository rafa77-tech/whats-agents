# Sistema de Business Events

> Implementado na Sprint 17 - Business Events e Funil

## Visão Geral

O sistema de Business Events rastreia todas as ações significativas de negócio para análise de funil, métricas e auditoria.

## Tipos de Eventos

### Eventos de Médico

| Evento | Descrição |
|--------|-----------|
| `doctor_inbound` | Médico enviou mensagem |
| `doctor_outbound` | Mensagem enviada para médico |

### Eventos de Oferta

| Evento | Descrição |
|--------|-----------|
| `offer_teaser_sent` | Teaser de vaga enviado |
| `offer_made` | Oferta completa feita |
| `offer_accepted` | Médico aceitou a vaga |
| `offer_declined` | Médico recusou a vaga |

### Eventos de Handoff

| Evento | Descrição |
|--------|-----------|
| `handoff_created` | Handoff para humano criado |
| `handoff_contacted` | Mensagem enviada ao divulgador |
| `handoff_confirm_clicked` | Link de confirmação clicado |
| `handoff_confirmed` | Plantão confirmado |
| `handoff_not_confirmed` | Plantão não fechou |
| `handoff_expired` | Expirou sem resposta |
| `handoff_followup_sent` | Follow-up enviado |

### Eventos de Confirmação de Plantão

| Evento | Descrição |
|--------|-----------|
| `shift_confirmation_due` | Plantão terminou, aguarda confirmação |
| `shift_completed` | Plantão realizado |
| `shift_not_completed` | Plantão não ocorreu |

### Eventos de Guardrails

| Evento | Descrição |
|--------|-----------|
| `outbound_blocked` | Envio bloqueado por guardrail |
| `outbound_bypass` | Envio permitido por bypass humano |
| `outbound_fallback` | Fallback legado usado |
| `outbound_deduped` | Bloqueado por deduplicação |

### Eventos de Fora do Horário

| Evento | Descrição |
|--------|-----------|
| `out_of_hours_ack_sent` | ACK enviado fora do horário |
| `out_of_hours_ack_skipped` | ACK pulado |

### Eventos de Campanha

| Evento | Descrição |
|--------|-----------|
| `campaign_touch_linked` | Touch de campanha registrado |
| `campaign_reply_attributed` | Reply atribuído a campanha |
| `briefing_sync_triggered` | Sync manual via Slack |

## Origens de Eventos

| Source | Descrição |
|--------|-----------|
| `pipeline` | Pipeline de processamento |
| `backend` | Código de aplicação |
| `db` | Trigger de banco |
| `heuristic` | Detector heurístico |
| `ops` | Manual por operações |
| `system` | Sistema automático |
| `slack` | Comando via Slack |

## Arquitetura

```
app/services/business_events/
├── __init__.py       # Exports
├── types.py          # EventType, EventSource, BusinessEvent
├── repository.py     # emit_event(), query_events()
├── alerts.py         # Alertas baseados em eventos
├── audit.py          # Auditoria e reconciliação
├── context.py        # Contexto de evento atual
├── kpis.py           # KPIs e métricas
├── metrics.py        # Agregação de métricas
├── reconciliation.py # Reconciliação de dados
├── recusa_detector.py# Detecção de recusas
├── rollout.py        # Rollout gradual
└── validators.py     # Validação de eventos
```

## Uso

### Emitindo Eventos

```python
from app.services.business_events.types import BusinessEvent, EventType, EventSource
from app.services.business_events.repository import emit_event

event = BusinessEvent(
    event_type=EventType.OFFER_ACCEPTED,
    source=EventSource.PIPELINE,
    cliente_id=cliente_id,
    vaga_id=vaga_id,
    event_props={"valor": 2500}
)

await emit_event(event)
```

### Consultando Eventos

```python
from app.services.business_events.repository import query_events

eventos = await query_events(
    cliente_id=cliente_id,
    event_type=EventType.OFFER_MADE,
    limit=10
)
```

## Tabela no Banco

```sql
CREATE TABLE business_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    event_props JSONB DEFAULT '{}',
    cliente_id UUID REFERENCES clientes(id),
    vaga_id UUID REFERENCES vagas(id),
    hospital_id UUID REFERENCES hospitais(id),
    conversation_id UUID REFERENCES conversations(id),
    interaction_id BIGINT,
    policy_decision_id UUID,
    dedupe_key TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_dedupe_key UNIQUE (dedupe_key) WHERE dedupe_key IS NOT NULL
);
```

## Referências

- Sprint 17: `planning/sprint-17/`
- Código: `app/services/business_events/`
