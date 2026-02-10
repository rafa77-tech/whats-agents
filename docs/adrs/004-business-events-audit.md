# ADR-004: Event Sourcing para Auditoria e Automacao

- Status: Aceita
- Data: Janeiro 2026
- Sprint: Sprint 17 (Business Events e Funil)
- Decisores: Equipe de Engenharia

## Contexto

Durante as primeiras 16 sprints, o sistema acumulou problemas de rastreabilidade e auditoria:

**Problemas identificados:**

1. **Falta de auditoria completa**
   - Mudancas de status de vaga nao registradas
   - Handoffs acontecendo sem log de motivacao
   - Dificil responder "por que esta conversa foi escalada?"

2. **Attribution de campanhas impossivel**
   - Campanha enviada, medico respondeu, mas qual campanha gerou a conversao?
   - Nao da pra calcular ROI de campanhas

3. **Metricas de funil incompletas**
   - Quantos medicos na etapa "interessado"?
   - Qual a taxa de conversao de "primeiro contato" -> "vaga reservada"?
   - Informacao espalhada em multiplas tabelas sem link

4. **Automacao limitada**
   - "Se medico nao responder em 48h, enviar follow-up" = codigo custom
   - Dificil adicionar novas regras de automacao
   - Policy engine (Sprint 15) nao tem eventos para reagir

**Requisito:** Sistema de eventos que registre tudo e permita automacao.

## Decisao

Implementar **Event Sourcing pattern** com business events:

### Arquitetura

1. **Business Events Table**
```sql
CREATE TABLE business_events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,  -- ex: "conversa_iniciada", "vaga_reservada"
    entity_type TEXT,           -- ex: "conversa", "vaga", "campanha"
    entity_id UUID,
    user_id UUID,               -- medico_id ou gestor_id
    metadata JSONB,             -- dados especificos do evento
    created_at TIMESTAMPTZ DEFAULT now()
);
```

2. **17+ Tipos de Eventos**
   - `conversa_iniciada`
   - `resposta_recebida`
   - `mensagem_enviada`
   - `vaga_reservada`
   - `vaga_cancelada`
   - `handoff_escalado`
   - `handoff_resolvido`
   - `opt_out_solicitado`
   - `campanha_enviada`
   - `campanha_respondida`
   - `politica_violada`
   - `medico_interessado`
   - `documentos_enviados`
   - `plantao_confirmado`
   - etc.

3. **Event Emitter**
```python
class BusinessEventEmitter:
    async def emit(
        self,
        event_type: str,
        entity_type: str,
        entity_id: UUID,
        metadata: dict
    ):
        await supabase.table("business_events").insert({
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "metadata": metadata,
            "created_at": agora_utc().isoformat()
        })

        # Trigger policy engine
        await policy_engine.process_event(event)
```

4. **Integracao com Pipeline**
   - Post-processor emite eventos automaticamente
   - Codigo de negocio emite eventos manualmente quando necessario

5. **Policy Engine reage a eventos**
```python
# Exemplo: Auto follow-up
@policy("auto_followup")
async def auto_followup_policy(event: BusinessEvent):
    if event.event_type == "resposta_recebida":
        # Agendar follow-up em 48h se nao houver nova interacao
        await schedule_followup(event.entity_id, delay_hours=48)
```

**Beneficios:**
- Auditoria completa (todo evento registrado)
- Attribution de campanhas (rastrear origem de conversao)
- Funil de conversao (aggregar eventos por etapa)
- Automacao reativa (policy engine)

## Alternativas Consideradas

### 1. Logs estruturados apenas
- **Pros**: Simples, ja temos logging
- **Cons**: Logs nao sao queryable, sem estrutura, dificil analytics
- **Rejeicao**: Logs sao para debug, nao para business logic

### 2. Audit table com triggers SQL
- **Pros**: Automatico, nao esquece de registrar
- **Cons**: Triggers sao dificeis de testar, nao suportam automacao
- **Rejeicao**: Menos flexivel que eventos no application layer

### 3. Change Data Capture (CDC) com Debezium
- **Pros**: Captura todas as mudancas no banco automaticamente
- **Cons**: Complexidade alta, overhead de infraestrutura, nao captura intencao
- **Rejeicao**: Overkill, nao expressa semantica de negocio

### 4. CQRS completo (event store separado)
- **Pros**: Event sourcing puro, replay de eventos
- **Cons**: Complexidade muito alta, dual write problem
- **Rejeicao**: Nao precisamos de replay, apenas auditoria e automacao

## Consequencias

### Positivas

1. **Auditoria completa**
   - Todo evento importante registrado
   - Responder "por que X aconteceu?" = query eventos
   - Compliance (se necessario no futuro)

2. **Attribution de campanhas**
   - `campanha_enviada` -> `resposta_recebida` -> `vaga_reservada`
   - Calcular ROI: custo campanha / conversoes
   - Dashboard de performance de campanhas

3. **Funil de conversao**
   - Aggregar eventos por tipo
   - "100 conversas iniciadas -> 30 interessados -> 10 vagas reservadas"
   - Taxa de conversao por etapa

4. **Automacao reativa**
   - Policy engine reage a eventos
   - Adicionar nova regra = novo policy handler
   - "Se X acontecer, fazer Y" sem codigo custom

5. **Analytics facilitado**
   - Query eventos para relatorios
   - Time-series de eventos (Grafana)
   - Cohort analysis (conversoes por mes)

6. **Debugging melhorado**
   - Timeline de eventos de uma conversa
   - "O que aconteceu com esta vaga?"
   - Event viewer no dashboard

### Negativas

1. **Overhead de armazenamento**
   - 100+ eventos/dia = 36k eventos/ano
   - Estimativa: 1kb/evento = 36MB/ano (negligivel)
   - Mitigacao: TTL de 1 ano, archive para S3

2. **Complexidade adicional**
   - Desenvolvedores precisam emitir eventos
   - Risco de esquecer de emitir evento
   - Mitigacao: Code review checklist, post-processor automatico

3. **Consistencia dual write**
   - Emitir evento + update database = 2 writes
   - Risco de evento emitido mas DB falhou (ou vice-versa)
   - Mitigacao: Transactional outbox pattern (futuro se necessario)

4. **Performance de queries**
   - Aggregar eventos pode ser lento
   - Indexes necessarios (entity_id, event_type, created_at)
   - Mitigacao: Materialized views para funil

### Mitigacoes

1. **Emissao automatica via post-processor**
   - Pipeline emite eventos core automaticamente
   - Reduz risco de esquecimento

2. **Schema de eventos versionado**
   - Metadata JSONB suporta evolucao de schema
   - Backwards compatibility

3. **Indexes estrategicos**
```sql
CREATE INDEX idx_events_entity ON business_events(entity_id, created_at);
CREATE INDEX idx_events_type ON business_events(event_type, created_at);
CREATE INDEX idx_events_user ON business_events(user_id, created_at);
```

4. **Materialized view para funil**
```sql
CREATE MATERIALIZED VIEW funil_conversao AS
SELECT
    DATE(created_at) as dia,
    COUNT(*) FILTER (WHERE event_type = 'conversa_iniciada') as conversas,
    COUNT(*) FILTER (WHERE event_type = 'medico_interessado') as interessados,
    COUNT(*) FILTER (WHERE event_type = 'vaga_reservada') as reservas
FROM business_events
GROUP BY dia;
```

## Implementacao

### Emitir evento

```python
# Em qualquer parte do codigo
from app.services.business_events import emit_event

await emit_event(
    event_type="vaga_reservada",
    entity_type="vaga",
    entity_id=vaga_id,
    metadata={
        "medico_id": medico_id,
        "hospital": "Hospital São Luiz",
        "valor": 2500,
        "data_plantao": "2026-03-15"
    }
)
```

### Query de auditoria

```python
# Buscar timeline de uma conversa
events = supabase.table("business_events") \
    .select("*") \
    .eq("entity_id", conversa_id) \
    .order("created_at") \
    .execute()

# Attribution de campanha
conversoes = supabase.table("business_events") \
    .select("*") \
    .eq("event_type", "vaga_reservada") \
    .contains("metadata", {"campanha_id": campaign_id}) \
    .execute()
```

### Policy Engine

```python
# Policy reage a evento
@on_event("resposta_recebida")
async def auto_followup(event: BusinessEvent):
    if not event.metadata.get("tem_interesse"):
        await schedule_task(
            "send_followup",
            entity_id=event.entity_id,
            delay_hours=48
        )
```

## Metricas de Sucesso

1. **100% de eventos core registrados** (conversa, vaga, handoff)
2. **Attribution de 80%+ conversoes** (saber origem)
3. **Funil de conversao atualizado em < 5min** (materialized view refresh)
4. **5+ automacoes via policy engine** (Sprint 17+)

## Referencias

- Codigo: `app/services/business_events.py`
- Table: `business_events` no Supabase
- Policy Engine: `app/services/policy_engine.py`
- Post-processor: `app/pipeline/processors/event_emitter.py`
- Docs: `docs/arquitetura/business-events.md` (se existir)
- Dashboard: Funil de conversao view

## Historico de Mudancas

- **2026-01**: Sprint 17 - Implementacao inicial (17 tipos de eventos)
- **2026-01**: Sprint 18 - Auditoria e integridade (validacao de eventos)
- **2026-02**: Atual - 100+ eventos/hora em operacao
