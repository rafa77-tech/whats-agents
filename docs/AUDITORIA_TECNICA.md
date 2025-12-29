# Auditoria Técnica - Sistema Julia

Data: 2025-12-29
Sprint: 18.1 P0 (Guardrails Canary 10%)

---

## Resumo Executivo

| Categoria | Status | Score |
|-----------|--------|-------|
| Arquitetura | **PASS** | 9/10 |
| Guardrails | **PASS** | 10/10 |
| Agente (Julia) | **PASS** | 8/10 |
| Pipeline | **PASS** | 9/10 |
| Observabilidade | **PASS** | 8/10 |
| Segurança | **PASS** | 9/10 |
| Provider (Evolution) | **RISK** | 6/10 |

**Veredito: GO com restrições para Canary 10%**

---

## 1. Arquitetura do Sistema

### 1.1 Componentes e Responsabilidades

| Componente | Responsabilidade | Status |
|------------|------------------|--------|
| Inbound Pipeline | receber → normalizar → persistir → context → Policy/Agent → effects | **PASS** |
| Policy Engine | decide WAIT/HANDOFF/OFFER/FOLLOWUP - auditável e determinístico | **PASS** |
| Agent (Julia) | gera conteúdo conforme decisão - NÃO decide compliance | **PASS** |
| Outbound | único caminho → guardrails → provider → business_events | **PASS** |
| Observability | policy_events + business_events + auditoria | **PASS** |

**Evidência:**
- `app/pipeline/setup.py:29-62` - Pipeline bem definido com ordem de processadores
- `app/services/policy/` - Policy Engine separado com decisões determinísticas
- `app/services/outbound.py` - `send_outbound_message()` é único export público
- `app/services/guardrails/check.py` - Guardrails soberanos

**Falha Típica Evitada:** Agent não decide e envia direto ✅

### 1.2 Fluxo Crítico Fim-a-Fim

```
1. inbound recebido              → ParseMessageProcessor
2. interação salva               → SaveInteractionProcessor (interaction_id)
3. policy_decision               → LLMCoreProcessor chama PolicyDecide
4. escolha de action             → PolicyDecision.primary_action
5. agent gera texto              → gerar_resposta_julia()
6. send_outbound_message(ctx)    → SendMessageProcessor usa ctx REPLY
7. provider send (Evolution)     → evolution.enviar_mensagem()
8. DOCTOR_OUTBOUND + BLOCKED     → _emitir_outbound_event(), _emit_guardrail_event()
9. update status                 → update_effect_interaction_id()
```

**Rastreabilidade:** Pode reconstruir conversa com:
- `cliente_id` ✅
- `conversation_id` ✅
- `policy_decision_id` ✅ (Sprint 16)
- `interaction_id` ✅

**Status: PASS**

---

## 2. Qualidade do Código e Guardrails

### 2.1 "One Way Out" - Outbound Soberano

| Regra | Status | Evidência |
|-------|--------|-----------|
| Todo envio exige OutboundContext | **PASS** | `post_processors.py:155` cria ctx |
| `send_outbound_message()` é único export | **PASS** | CI guard em `test_architecture_guardrails.py` |
| Nenhum `EvolutionAPI.send()` fora do provider | **PASS** | Grep confirma |

**CI Guard:** `tests/test_architecture_guardrails.py` falha build se detectar import direto.

**Teste Adicional Recomendado:**
```python
# Varrer por strings do client Evolution fora do módulo
def test_no_direct_evolution_calls():
    forbidden_patterns = [
        "evolution.enviar_mensagem",
        "EvolutionClient().enviar",
        "enviar_whatsapp("
    ]
    # ... varrer arquivos exceto whatsapp.py e outbound.py
```

**Status: PASS**

### 2.2 Erros e Retries

| Feature | Status | Risco |
|---------|--------|-------|
| Circuit breaker | **OK** | 5 falhas → abre, 60s reset |
| Rate limiter | **OK** | 20/hora, 100/dia |
| Retry com backoff | **MISSING** | Falha = circuit direto |
| Idempotência | **MISSING** | Timeout = duplicata |
| Send receipt | **MISSING** | Não marca "realmente enviado" |

**Código atual (sem retry):**
```python
# app/services/whatsapp.py:40-63
async def _fazer_request(self, method, url, payload, timeout):
    async def _request():
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, ...)
            response.raise_for_status()
            return response.json()
    return await circuit_evolution.executar(_request)  # Direto pro circuit
```

**Status: RISK - Não bloqueia canary 10%, mas exigido para 25%+**

---

## 3. Configuração do Agente (Julia)

### 3.1 Separação de Responsabilidades

| Pergunta | Resposta | Status |
|----------|----------|--------|
| Policy decide se pode e o que pode fazer? | Sim - `PolicyDecide()` retorna action + constraints | **PASS** |
| Agent decide como falar dentro de constraints? | Sim - `constraints_text` vai pro prompt | **PASS** |
| Agent pode ignorar forbid_all/constraints? | Não - constraints são PRIORIDADE MÁXIMA no prompt | **PASS** |
| Agent pode enviar proativo sem guardrail? | Não - `send_outbound_message()` obrigatório | **PASS** |
| Agent pode inventar vaga_id/status? | Não - tools buscam do banco | **PASS** |

**Evidência:**
```python
# app/prompts/builder.py:130-141
def build(self) -> str:
    partes = []
    # 0. Policy constraints (PRIORIDADE MÁXIMA - Sprint 15)
    if self._policy_constraints:
        partes.append(f"## DIRETRIZES DE POLÍTICA (PRIORIDADE MÁXIMA)\n\n{self._policy_constraints}")
```

**Status: PASS**

### 3.2 Prompting e Controle

| Item | Status | Localização |
|------|--------|-------------|
| System prompt estável e versionado | **PASS** | `prompts` + `prompts_historico` no DB |
| Tool policy explícita | **PASS** | `julia_tools` com regras de uso |
| Safe mode refletido | **PASS** | `is_safe_mode_active()` bloqueia proativo |
| Kill switch | **PASS** | `pausar_julia` via Slack |
| Limites claros (PII, opt-out) | **PASS** | Regra R6 + OptOutProcessor |

**Prompt Base (fallback):**
```python
# app/prompts/loader.py:17-38
FALLBACK_PROMPTS = {
    "julia_base": """...
## REGRAS ABSOLUTAS
1. NUNCA revele que e uma IA, bot, assistente virtual ou programa
2. Se perguntarem se e bot, voce E a Julia, escalista humana
3. NUNCA envie listas com marcadores ou numeros
4. NUNCA use linguagem muito formal
5. SEMPRE respeite quando alguem pedir para parar de receber mensagens"""
}
```

**Status: PASS**

### 3.3 Tools do Agente

| Tool | Função | Idempotente? | Loga IDs? |
|------|--------|--------------|-----------|
| `buscar_vagas` | Lista vagas disponíveis | ✅ Sim (read-only) | ✅ medico_id |
| `reservar_plantao` | Reserva vaga | ⚠️ Parcial | ✅ vaga_id, medico_id |
| `buscar_info_hospital` | Busca endereço | ✅ Sim (read-only) | ✅ hospital_nome |
| `agendar_lembrete` | Cria lembrete | ⚠️ Parcial | ✅ medico_id |
| `salvar_memoria` | Salva preferência | ⚠️ Parcial | ✅ medico_id |

**Gaps identificados:**
- `reservar_plantao`: Não tem dedupe - chamar 2x = 2 reservas?
- `agendar_lembrete`: Não tem dedupe - pode criar duplicados

**Mitigação atual:** Agente não costuma chamar tool 2x na mesma mensagem.

**Status: PASS com observação**

---

## 4. Pipelines, Jobs, Workers

### 4.1 Inbound Pipeline

**Ordem dos Processadores:**

| Prioridade | Processador | Função |
|------------|-------------|--------|
| 5 | IngestaoGrupoProcessor | Ingestão de grupos (não responde) |
| 10 | ParseMessageProcessor | Parse do webhook |
| 15 | PresenceProcessor | Mostra "online" |
| 20 | LoadEntitiesProcessor | Carrega médico/conversa |
| 22 | BusinessEventInboundProcessor | Emite `doctor_inbound` |
| 25 | ChatwootSyncProcessor | Sincroniza com Chatwoot |
| 30 | OptOutProcessor | Detecta opt-out |
| 35 | BotDetectionProcessor | Detecta bot |
| 40 | MediaProcessor | Processa mídia |
| 45 | LongMessageProcessor | Mensagens longas |
| 50 | HandoffTriggerProcessor | Detecta trigger handoff |
| 60 | HumanControlProcessor | Verifica controle humano |

| Item | Status |
|------|--------|
| Dedupe inbound | ⚠️ Não explícito (depende do Evolution não duplicar) |
| Ordering | ✅ Processadores ordenados por prioridade |
| Persistência antes de executar | ✅ `SaveInteractionProcessor` salva entrada |

**Status: PASS**

### 4.2 Post-Processors

| Prioridade | Processador | Função |
|------------|-------------|--------|
| 5 | ValidateOutputProcessor | Bloqueia revelação de IA |
| 10 | TimingProcessor | Delay humanizado |
| 20 | SendMessageProcessor | Envia via guardrails wrapper |
| 30 | SaveInteractionProcessor | Salva interações + update policy_event |
| 40 | MetricsProcessor | Registra métricas |

**Sprint 18.1 P0 - SendMessageProcessor:**
```python
# post_processors.py:153-167
ctx = None
if context.medico and context.conversa:
    ctx = criar_contexto_reply(
        cliente_id=context.medico["id"],
        conversation_id=context.conversa["id"],
        inbound_interaction_id=inbound_interaction_id,
        last_inbound_at=datetime.now(timezone.utc).isoformat(),
        policy_decision_id=context.metadata.get("policy_decision_id"),
    )

resultado = await enviar_resposta(
    telefone=context.telefone,
    resposta=response,
    ctx=ctx,  # Contexto obrigatório
)
```

**Status: PASS**

### 4.3 Jobs/Workers

| Item | Status | Observação |
|------|--------|------------|
| Lock para evitar corrida | ⚠️ Verificar Redis lock | Jobs devem ter lock |
| Job idempotente | ⚠️ Parcial | Alguns jobs podem duplicar |
| Retries não geram duplicata | ✅ `dedupe_key` em events | Business events ok |
| Métricas de execução | ✅ | `data_anomalies`, `business_alerts` |

**Status: PASS com observação**

---

## 5. Observabilidade e SLOs

### 5.1 Métricas Implementadas

| Métrica | Tabela/Query | Status |
|---------|--------------|--------|
| Volume por event_type | `business_events` | ✅ |
| Blocked/bypass por razão | `business_events` | ✅ |
| Replies inválidos | `business_events` WHERE method=reply | ✅ |
| Provider errors | `business_events` WHERE block_reason IN (...) | ⚠️ Parcial |
| Fallback legado | `business_events` WHERE event_type=outbound_fallback | ✅ |

### 5.2 SLOs Definidos

| SLO | Threshold | Query |
|-----|-----------|-------|
| Safety | outbound_to_opted_out = 0 | Q1 |
| Guardrail | outbound_fallback = 0 | Q5 |
| Integrity | invalid_reply = 0 | Q3 |
| Delivery | provider_error < 1% | Q4 |

**Status: PASS**

---

## 6. Segurança

### 6.1 Itens Implementados

| Item | Status | Evidência |
|------|--------|-----------|
| RLS everywhere | ✅ | Migrations habilitam RLS |
| Revoke grants anon/authenticated | ✅ | `disable_default_permissions` |
| search_path fixo | ✅ | Migrations definem |
| default privileges seguros | ✅ | `on_new_object_...` triggers |

### 6.2 Check Final de Produção

| Item | Status | Ação |
|------|--------|------|
| Secrets sem log | ✅ | Telefone truncado, sem PII |
| Rotação de secrets | ⚠️ | Verificar processo |
| Auditoria service_role | ⚠️ | Documentar quem tem acesso |
| Backups/PITR | ⚠️ | Verificar se habilitado no Supabase |

**Status: PASS**

---

## 7. Diagnóstico do Provider (Evolution)

### 7.1 Análise do Client

**Arquivo:** `app/services/whatsapp.py`

| Feature | Implementado | Código |
|---------|--------------|--------|
| Circuit breaker | ✅ | `circuit_evolution.executar(_request)` |
| Rate limiter | ✅ | `pode_enviar()`, `registrar_envio()` |
| Timeout | ✅ | 30s default |
| Retry com backoff | ❌ | Não implementado |
| Idempotency key | ❌ | Não enviado |
| Send receipt/acknowledgment | ❌ | Não implementado |

### 7.2 Fluxo de Erro Atual

```
Falha HTTP → raise_for_status() → CircuitBreaker conta falha → 5 falhas = OPEN
```

**Problema:** Uma falha transitória (timeout, 503) já conta como falha.

### 7.3 Riscos Identificados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Timeout gera duplicata | Média | Alto | Implementar dedupe/outbox |
| Circuit abre cedo demais | Baixa | Médio | Implementar retry antes |
| Mensagem perdida sem saber | Baixa | Alto | Implementar acknowledgment |

**Status: RISK - Bloqueador para 25%+**

---

## 8. Resumo de Gaps e Ações

### Bloqueadores para 25%

| Gap | Esforço | Prioridade | Risco se não fizer |
|-----|---------|------------|-------------------|
| B1: Toggle campanhas via Slack | 1h | P0 | Incidente sem botão de emergência |
| B2: Retry/backoff Evolution | 2h | P0 | Circuit abre cedo, falsos alarmes |
| B3: Dedupe simples (nível 1) | 2h | P0 | Duplicatas em timeout/retry |

**Justificativa B3 em 25%:** Mesmo com guardrails, duplicata ocorre por:
- Timeout httpx (não sabe se chegou)
- Retry manual do operador/job
- Reprocessamento de fila após restart
- Flakiness Evolution (503/429/latência)

### Bloqueadores para 50%

| Gap | Esforço | Prioridade |
|-----|---------|------------|
| C1: Outbox robusto (nível 2) | 4h | P0 |

### Bloqueadores para 100%

| Gap | Esforço | Prioridade |
|-----|---------|------------|
| Playbook de incidentes testado | 2h | P0 |
| 7 dias estáveis em 50% | - | Gate |

### Dívida Técnica (não bloqueadora)

| Item | Esforço | Prioridade |
|------|---------|------------|
| Dedupe em tools (reservar_plantao) | 2h | P1 |
| Lock explícito em jobs | 2h | P1 |
| Send acknowledgment (nível 3) | 3h | P2 |
| Rotação de secrets documentada | 1h | P2 |

---

## 9. Veredito Final

### Canary 10%: **GO**

| Critério | Status |
|----------|--------|
| Guardrails soberanos | ✅ |
| CI guard | ✅ |
| Kill switch funciona | ✅ |
| Observabilidade mínima | ✅ |
| Sem PII em eventos/logs | ✅ |

### Restrições Operacionais

1. Volume de campanhas pequeno (janelas 1-2h)
2. Monitoramento diário obrigatório
3. Não escalar sem fechar gaps B1 e B2

### Próximos Gates

| Gate | Critério |
|------|----------|
| 25% | Gaps B1 + B2 fechados + 24h estáveis |
| 50% | Gap C1 fechado + 48h estáveis |
| 100% | Playbook testado + 7 dias estáveis |

---

## Anexo: Inventário de Componentes

### Tools do Agente (5)

```python
JULIA_TOOLS = [
    TOOL_BUSCAR_VAGAS,        # Read-only, lista vagas
    TOOL_RESERVAR_PLANTAO,    # Write, reserva vaga
    TOOL_BUSCAR_INFO_HOSPITAL,# Read-only, busca endereço
    TOOL_AGENDAR_LEMBRETE,    # Write, cria lembrete
    TOOL_SALVAR_MEMORIA,      # Write, salva preferência
]
```

### Pre-Processors (12)

```python
IngestaoGrupoProcessor()     # 5
ParseMessageProcessor()      # 10
PresenceProcessor()          # 15
LoadEntitiesProcessor()      # 20
BusinessEventInboundProcessor() # 22
ChatwootSyncProcessor()      # 25
OptOutProcessor()            # 30
BotDetectionProcessor()      # 35
MediaProcessor()             # 40
LongMessageProcessor()       # 45
HandoffTriggerProcessor()    # 50
HumanControlProcessor()      # 60
```

### Post-Processors (5)

```python
ValidateOutputProcessor()    # 5
TimingProcessor()            # 10
SendMessageProcessor()       # 20
SaveInteractionProcessor()   # 30
MetricsProcessor()           # 40
```

### Business Event Types (13)

```python
DOCTOR_INBOUND
DOCTOR_OUTBOUND
OFFER_TEASER_SENT
OFFER_MADE
OFFER_ACCEPTED
OFFER_DECLINED
HANDOFF_CREATED
SHIFT_CONFIRMATION_DUE
SHIFT_COMPLETED
SHIFT_NOT_COMPLETED
OUTBOUND_BLOCKED
OUTBOUND_BYPASS
OUTBOUND_FALLBACK
```

### Tabelas Críticas

| Tabela | Função |
|--------|--------|
| `business_events` | Eventos de negócio auditáveis |
| `policy_events` | Decisões da Policy Engine |
| `doctor_state` | Estado do médico (opted_out, cooling_off) |
| `feature_flags` | Flags de rollout (canary) |
| `interacoes` | Histórico de mensagens |
| `conversations` | Conversas ativas |

---

## 11. Operação (Runbook)

### 11.1 Monitoramento Diário

| Horário | Responsável | Ação |
|---------|-------------|------|
| 09:00 | Ops | Executar queries Q1-Q5, verificar thresholds |
| 17:00 | Ops | Verificar métricas do dia, preparar resumo |
| Ad-hoc | Qualquer | Se alerta disparar, seguir protocolo |

### 11.2 Queries de Monitoramento

| Query | Onde | Threshold |
|-------|------|-----------|
| Q1: Volume por evento | Supabase SQL | Sanity check |
| Q3: Replies inválidos | Supabase SQL | **= 0** |
| Q4: Provider errors | Supabase SQL | **< 1%** |
| Q5: Fallback legado | Supabase SQL | **= 0** |

**Endpoint interno:** `GET /integridade/daily-health` (se implementado)

### 11.3 Alarmes Vermelhos (Ação Imediata)

| Condição | Severidade | Ação |
|----------|------------|------|
| `outbound_fallback > 0` | 🔴 P0 | Investigar call-site não migrado |
| `reply_invalido > 0` | 🔴 P0 | Investigar race condition |
| `outbound_to_opted_out > 0` | 🔴 P0 | **ROLLBACK IMEDIATO** + pausar_julia |
| `provider_error_rate > 5%` | 🟠 P1 | Verificar Evolution, considerar safe_mode |
| `duplicatas_detectadas > 0` | 🟠 P1 | Pausar campanhas, investigar |

### 11.4 Ações de Emergência

```
# 1. Pausar tudo (kill switch total)
Slack: "pausa a Julia"
→ julia_status = pausado

# 2. Pausar só campanhas (kill switch parcial)
Slack: "desativa campanhas"  # Após implementar B1
→ feature_flags.campaigns.enabled = false

# 3. Safe mode (respostas conservadoras)
Supabase: UPDATE feature_flags SET value = '{"enabled": true}' WHERE key = 'safe_mode'

# 4. Rollback canary
Supabase: UPDATE feature_flags SET value = '{"percentage": 0}' WHERE key = 'business_events_canary'
```

### 11.5 Contatos de Escalação

| Situação | Quem acionar |
|----------|--------------|
| Vazamento opted_out | Product + Tech Lead |
| Provider fora | Tech Lead |
| Duplicatas em massa | Tech Lead |
| Dúvida operacional | Consultar este documento |

### 11.6 Checklist Pós-Incidente

- [ ] Incidente documentado em issue
- [ ] Root cause identificado
- [ ] Fix implementado ou mitigação aplicada
- [ ] Queries de validação executadas
- [ ] Comunicação para stakeholders
- [ ] Atualizar este runbook se necessário
