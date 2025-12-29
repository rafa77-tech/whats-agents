# Sprint 23: Campanhas como Motor de Conversao

**Objetivo:** Transformar campanhas de "motor de alcance" para "motor de conversao auditavel"

**Problema Central:** Hoje sabemos que enviamos, mas nao sabemos o que funcionou.

---

## Contexto

### O que temos hoje (funciona)
- Envios persistidos em `envios_campanha` e `fila_mensagens`
- Status por envio (pendente/enviado/bloqueado/erro)
- Guardrails robustos (opted_out, cooling_off, contact_cap_7d)
- Cadencia de follow-up documentada (48h → 5d → 15d → pausa 60d)

### O que falta (gaps criticos)
1. **Atribuicao reply→campanha:** Nao sabemos de qual campanha veio a resposta
2. **Outcome no send:** Resultado do outbound nao propaga para o registro de envio
3. **Duas pipelines:** `envios_campanha` e `fila_mensagens` coexistem sem fonte unica
4. **Status deduped:** Deduplicacao de outbound nao e distinguida de bloqueio
5. **Cooldown por campanha:** Apenas `contact_cap_7d`, nao previne 2 campanhas diferentes
6. **Briefing tatico:** 60min de latencia e longo para virar a mao no dia

---

## Invariantes de Atribuicao (Contrato Inviolavel)

Para garantir 100% de atribuicao, estes invariantes DEVEM ser respeitados:

| ID | Invariante | Validacao |
|----|------------|-----------|
| **C1** | Todo outbound `method=CAMPAIGN` DEVE ter `campaign_id` no registro do send | Se `campaign_id` NULL em send de campanha = BUG |
| **C2** | Todo outbound `outcome=SENT` com `campaign_id != null` DEVE atualizar `conversation.last_touch_campaign_id` | Ou emitir evento que permita reconstruir |
| **C3** | Todo inbound reply dentro da janela (7d) DEVE herdar `campaign_id` do `last_touch` vigente | Gravar `attributed_campaign_id` no momento do inbound |

**Sem estes invariantes, "100% de atribuicao" vira wishful thinking.**

---

## Metricas de Conversao (Definicao Previa)

Para evitar discussao semantica, definimos 3 niveis de conversao:

| Metrica | Definicao | Formula |
|---------|-----------|---------|
| **Reply Rate** | % de medicos que responderam apos receber campanha | `replies_7d / sends_delivered * 100` |
| **Qualified Rate** | % que entrou em objetivo oferta/negociacao | `qualified / replies * 100` |
| **Booked Rate** | % que aceitou/reservou plantao | `booked / qualified * 100` |

Isso gera **funil por campanha** e permite comparar performance entre tipos.

---

## Epicos

| Epico | Titulo | Prioridade | Complexidade | Status |
|-------|--------|------------|--------------|--------|
| E01 | Outcome no Send | P0 | Media | ✅ Completo |
| E02 | Atribuicao First/Last Touch | P0 | Media | ✅ Completo |
| E03 | Unificacao de Envios | P1 | Media | ✅ Completo |
| E04 | Status Deduped Explicito | P1 | Baixa | ✅ Completo |
| E05 | Cooldown por Campanha (Guardrail) | P1 | Media | ✅ Completo |
| E06 | Briefing Tatico (Slack) | P2 | Baixa | ✅ Completo |

**Ordem ajustada:** E01 antes de E02 porque `outcome=SENT` e gatilho para setar `last_touch`.

---

## E01: Outcome no Send

**Objetivo:** Resultado do outbound propaga para registro de envio com semantica clara.

### Outcomes Padronizados (Enum)

| Outcome | Tipo | Descricao |
|---------|------|-----------|
| `SENT` | Sucesso | Enviado com sucesso via provider |
| `BLOCKED_OPTED_OUT` | Guardrail | Bloqueado por opt-out (R0) |
| `BLOCKED_COOLING_OFF` | Guardrail | Bloqueado por cooling_off (R1) |
| `BLOCKED_NEXT_ALLOWED` | Guardrail | Bloqueado por next_allowed_at (R2) |
| `BLOCKED_CONTACT_CAP` | Guardrail | Bloqueado por limite 7d (R3) |
| `BLOCKED_CAMPAIGNS_DISABLED` | Guardrail | Campanhas desabilitadas (R4a) |
| `BLOCKED_SAFE_MODE` | Guardrail | Safe mode ativo (R4b) |
| `BLOCKED_CAMPAIGN_COOLDOWN` | Guardrail | Cooldown entre campanhas (R5) |
| `DEDUPED` | Protecao | Duplicado (mesmo conteudo em janela) |
| `FAILED_PROVIDER` | Erro | Erro do provider (Evolution API) |
| `FAILED_VALIDATION` | Erro | Erro de validacao pre-envio |
| `BYPASS` | Override | Bypass manual via Slack |

**Distincao importante:**
- `BLOCKED_*` = guardrail impediu (permissao/regra)
- `DEDUPED` = protecao anti-spam (nao e bloqueio por permissao)
- `FAILED_*` = erro tecnico

### Modelo de Dados

```sql
-- Tipo enum para outcome
CREATE TYPE send_outcome AS ENUM (
  'SENT',
  'BLOCKED_OPTED_OUT',
  'BLOCKED_COOLING_OFF',
  'BLOCKED_NEXT_ALLOWED',
  'BLOCKED_CONTACT_CAP',
  'BLOCKED_CAMPAIGNS_DISABLED',
  'BLOCKED_SAFE_MODE',
  'BLOCKED_CAMPAIGN_COOLDOWN',
  'DEDUPED',
  'FAILED_PROVIDER',
  'FAILED_VALIDATION',
  'BYPASS'
);

-- Adicionar a fila_mensagens
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome send_outcome;
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome_reason_code TEXT;
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome_at TIMESTAMPTZ;
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS provider_message_id TEXT;

-- Indice para queries de outcome
CREATE INDEX IF NOT EXISTS idx_fila_mensagens_outcome
ON fila_mensagens(outcome) WHERE outcome IS NOT NULL;
```

### Alteracoes no OutboundResult

```python
@dataclass
class OutboundResult:
    success: bool
    blocked: bool  # True APENAS para guardrails
    deduped: bool  # True para deduplicacao (NAO e blocked)
    outcome: SendOutcome  # Enum com valor especifico
    outcome_reason_code: str | None  # Ex: "contact_cap", "content_hash_window"
    provider_message_id: str | None  # ID do provider quando enviado
    error: str | None
```

### Tarefas

- [x] T01.1: Criar enum `send_outcome` no banco ✅
- [x] T01.2: Migracao - adicionar colunas de outcome em fila_mensagens ✅
- [x] T01.3: Criar `OutcomeMapper` para traduzir guardrail → outcome ✅
- [x] T01.4: Atualizar `OutboundResult` com campos novos ✅
- [x] T01.5: Atualizar `send_outbound_message` para retornar outcome detalhado ✅
- [x] T01.6: Atualizar `fila_worker` para registrar outcome completo ✅
- [x] T01.7: Testes unitarios e integracao ✅ (20 testes)

### Criterios de Aceite

- [x] Todo envio processado tem `outcome` preenchido (enum)
- [x] Bloqueios por guardrail tem `outcome_reason_code` com detalhes
- [x] Deduplicacao tem outcome `DEDUPED` (nao `BLOCKED_*`)
- [x] `provider_message_id` gravado quando `outcome=SENT`
- [ ] Invariante C1 validado: campaign_id nunca nulo em sends de campanha (validado em E02)

---

## E02: Atribuicao First/Last Touch

**Objetivo:** Quando medico responde, saber qual campanha abriu a conversa (first) e qual tocou por ultimo (last).

### Por que First E Last?

| Tipo | Uso | Exemplo |
|------|-----|---------|
| **First Touch** | Atribuicao analitica (quem abriu) | "Discovery gerou 50 conversas novas" |
| **Last Touch** | Atribuicao operacional (quem reativou) | "Reativacao recuperou 20 medicos" |

Sem first_touch, followups e reativacoes sempre "roubam" credito do discovery inicial.

### Modelo de Dados

```sql
-- Adicionar a conversations
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS first_touch_campaign_id UUID REFERENCES campanhas(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS first_touch_type TEXT; -- campaign, followup, manual, slack
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS first_touch_at TIMESTAMPTZ;

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_campaign_id UUID REFERENCES campanhas(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_type TEXT;
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_at TIMESTAMPTZ;

-- Atribuicao no inbound (para reconstrucao)
ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS attributed_campaign_id UUID REFERENCES campanhas(id);

-- Indices
CREATE INDEX IF NOT EXISTS idx_conversations_first_touch
ON conversations(first_touch_campaign_id) WHERE first_touch_campaign_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conversations_last_touch
ON conversations(last_touch_campaign_id) WHERE last_touch_campaign_id IS NOT NULL;
```

### Logica de Atribuicao

```
QUANDO: Outbound com outcome=SENT e campaign_id != null
ENTAO:
  1. Atualizar conversation.last_touch_*
  2. Se first_touch_campaign_id IS NULL:
     - Setar first_touch_* tambem
  3. Emitir evento CAMPAIGN_TOUCH_LINKED

QUANDO: Inbound recebido (reply)
ENTAO:
  1. Buscar conversation.last_touch_campaign_id
  2. Se existe e last_touch_at dentro da janela (7 dias):
     - Gravar interacao.attributed_campaign_id
     - Emitir evento CAMPAIGN_REPLY_ATTRIBUTED
  3. Se nao existe ou fora da janela:
     - attributed_campaign_id = NULL (resposta organica)
```

### Eventos de Auditoria

| Evento | Quando | Payload |
|--------|--------|---------|
| `CAMPAIGN_TOUCH_LINKED` | Outbound SENT com campaign_id | campaign_id, touch_type, conversation_id |
| `CAMPAIGN_REPLY_ATTRIBUTED` | Inbound com atribuicao | campaign_id, interaction_id, conversation_id |

### Tarefas

- [x] T02.1: Migracao - adicionar colunas first/last touch em conversations ✅
- [x] T02.2: Migracao - adicionar attributed_campaign_id em interacoes ✅
- [x] T02.3: Criar servico `CampaignAttributionService` ✅
- [x] T02.4: Integrar no pos-processador de outbound (quando SENT) ✅
- [x] T02.5: Integrar no pipeline de inbound (pos-LoadEntities) ✅
- [x] T02.6: Emitir eventos CAMPAIGN_TOUCH_LINKED e CAMPAIGN_REPLY_ATTRIBUTED ✅
- [x] T02.7: Testes - validar invariantes C2 e C3 ✅ (13 testes)

### Criterios de Aceite

- [x] Conversa nova apos campanha tem `first_touch_*` e `last_touch_*` preenchidos
- [x] Reativacao atualiza `last_touch_*` mas mantem `first_touch_*`
- [x] Reply dentro de 7 dias tem `attributed_campaign_id` na interacao
- [x] Reply organica (sem envio previo) tem `attributed_*` NULL
- [x] Eventos emitidos permitem reconstruir trilha completa
- [x] Janela de atribuicao configuravel (default 7 dias)

---

## E03: Unificacao de Envios

**Objetivo:** Fonte unica de verdade para envios de campanha.

### Estrategia

Manter `fila_mensagens` como mecanismo de envio, deprecar `envios_campanha` gradualmente.
View unificada para relatorios com schema estavel.

### Modelo de Dados

```sql
-- View unificada para relatorios (schema estavel)
CREATE OR REPLACE VIEW campaign_sends AS
SELECT
  fm.id as send_id,
  fm.cliente_id,
  (fm.metadata->>'campanha_id')::UUID as campaign_id,
  fm.tipo as send_type,
  fm.status as queue_status,
  fm.outcome,
  fm.outcome_reason_code,
  fm.provider_message_id,
  fm.created_at as queued_at,
  fm.agendar_para as scheduled_for,
  fm.enviada_em as sent_at,
  fm.outcome_at,
  'fila_mensagens' as source_table  -- Para debug/auditoria
FROM fila_mensagens fm
WHERE fm.metadata->>'campanha_id' IS NOT NULL

UNION ALL

SELECT
  ec.id as send_id,
  ec.cliente_id,
  ec.campanha_id as campaign_id,
  ec.tipo as send_type,
  ec.status as queue_status,
  CASE
    WHEN ec.status = 'enviado' THEN 'SENT'::send_outcome
    WHEN ec.status = 'bloqueado' THEN 'BLOCKED_OPTED_OUT'::send_outcome -- legado generico
    WHEN ec.status = 'erro' THEN 'FAILED_PROVIDER'::send_outcome
    ELSE NULL
  END as outcome,
  ec.erro as outcome_reason_code,
  NULL as provider_message_id,
  ec.created_at as queued_at,
  NULL as scheduled_for,
  ec.enviado_em as sent_at,
  ec.enviado_em as outcome_at,
  'envios_campanha' as source_table  -- Legado
FROM envios_campanha ec;

-- Indice para performance na fila_mensagens
CREATE INDEX IF NOT EXISTS idx_fila_mensagens_campanha
ON fila_mensagens((metadata->>'campanha_id'))
WHERE metadata->>'campanha_id' IS NOT NULL;

-- View de metricas por campanha
CREATE OR REPLACE VIEW campaign_metrics AS
SELECT
  campaign_id,
  COUNT(*) as total_sends,
  COUNT(*) FILTER (WHERE outcome = 'SENT') as delivered,
  COUNT(*) FILTER (WHERE outcome LIKE 'BLOCKED_%') as blocked,
  COUNT(*) FILTER (WHERE outcome = 'DEDUPED') as deduped,
  COUNT(*) FILTER (WHERE outcome LIKE 'FAILED_%') as failed,
  ROUND(
    COUNT(*) FILTER (WHERE outcome = 'SENT')::numeric /
    NULLIF(COUNT(*), 0) * 100, 2
  ) as delivery_rate
FROM campaign_sends
GROUP BY campaign_id;
```

### Tarefas

- [x] T03.1: Criar view `campaign_sends` com schema estavel ✅
- [x] T03.2: Criar view `campaign_metrics` para dashboard ✅
- [x] T03.3: Atualizar `criar_envios_campanha` para usar apenas `fila_mensagens` ✅ (ja usava)
- [x] T03.4: Criar `CampaignSendsRepository` que usa as views ✅
- [x] T03.5: Deprecar uso direto de `envios_campanha` em novos codigos ✅
- [x] T03.6: Documentar que `envios_campanha` e legado ✅

### Criterios de Aceite

- [x] Todos os relatorios de campanha usam `campaign_sends`
- [x] Novos envios vao para `fila_mensagens` com `metadata.campanha_id`
- [x] Dados historicos de `envios` continuam visiveis via view
- [x] Coluna `source_table` permite identificar origem
- [x] View `campaign_metrics` funciona para dashboard

---

## E04: Status Deduped Explicito

**Objetivo:** Distinguir deduplicacao de bloqueio por guardrail.

### Contexto

Deduplicacao NAO e bloqueio por permissao - e protecao contra spam acidental.
Misturar os dois destroi a leitura operacional.

### Regra Clara

| Situacao | blocked | deduped | outcome |
|----------|---------|---------|---------|
| Guardrail impediu | `True` | `False` | `BLOCKED_*` |
| Conteudo duplicado | `False` | `True` | `DEDUPED` |
| Enviado com sucesso | `False` | `False` | `SENT` |

### Alteracoes

```python
# app/services/outbound.py

async def send_outbound_message(...) -> OutboundResult:
    # 1. Verificar deduplicacao ANTES de guardrails
    if await _is_duplicate_content(cliente_id, texto):
        return OutboundResult(
            success=False,
            blocked=False,  # NAO e bloqueio
            deduped=True,   # E deduplicacao
            outcome=SendOutcome.DEDUPED,
            outcome_reason_code="content_hash_window",
        )

    # 2. Verificar guardrails
    guardrail_result = await check_outbound_guardrails(ctx)
    if guardrail_result.is_blocked:
        return OutboundResult(
            success=False,
            blocked=True,  # E bloqueio
            deduped=False,
            outcome=_map_guardrail_to_outcome(guardrail_result),
            outcome_reason_code=guardrail_result.reason_code,
        )

    # 3. Enviar
    ...
```

### Tarefas

- [x] T04.1: Adicionar `deduped` ao `OutboundResult` ✅ (Sprint 23 E01)
- [x] T04.2: Verificar deduplicacao ANTES de guardrails ✅ (Sprint 23 E01)
- [x] T04.3: Emitir evento `OUTBOUND_DEDUPED` (separado de `OUTBOUND_BLOCKED`) ✅ (Sprint 18.1)
- [x] T04.4: Mapear para outcome `DEDUPED` no fila_worker ✅ (Sprint 23 E01)
- [x] T04.5: Testes - garantir que deduped != blocked ✅ (20 testes em test_send_outcome.py)

### Criterios de Aceite

- [x] Mensagem duplicada retorna `deduped=True`, `blocked=False`
- [x] Outcome e `DEDUPED` com `reason_code=content_hash_window`
- [x] Evento `OUTBOUND_DEDUPED` emitido (nao `OUTBOUND_BLOCKED`)
- [x] Metricas de "bloqueios" nao incluem dedupe

---

## E05: Cooldown por Campanha (Guardrail R5)

**Objetivo:** Evitar que medico receba campanhas diferentes em janela curta.

**Implementacao:** Como guardrail central (nao na logica de campanha).

### Regras de Negocio

| Regra | Descricao | Default | Configuravel |
|-------|-----------|---------|--------------|
| R5a | Nao enviar 2 campanhas diferentes em X dias | 3 dias | Sim |
| R5b | Se respondeu, suspender campanhas por Y dias | 7 dias | Sim |
| R5c | Exceto: reply e atendimento (sem bloqueio) | - | - |
| R5d | Bypass via Slack permitido (com log) | - | - |

**CRITICO:** Reply NAO pode ser bloqueado por cooldown. Reply e atendimento 24/7.

### Modelo de Dados

```sql
-- Historico de campanhas enviadas (para cooldown)
CREATE TABLE IF NOT EXISTS campaign_contact_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id),
  campaign_id UUID NOT NULL REFERENCES campanhas(id),
  campaign_type TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT idx_campaign_contact_unique
    UNIQUE (cliente_id, campaign_id)
);

CREATE INDEX idx_campaign_contact_lookup
ON campaign_contact_history(cliente_id, sent_at DESC);

-- Configuracao de cooldown (feature_flags ou tabela dedicada)
-- campaign_cooldown_days = 3
-- response_cooldown_days = 7
```

### Integracao no Guardrail

```python
# app/services/guardrails/check.py

async def check_outbound_guardrails(ctx: OutboundContext) -> GuardrailResult:
    ...
    # =========================================================================
    # R5: Cooldown por campanha (APENAS para method=CAMPAIGN)
    # =========================================================================
    if ctx.method == OutboundMethod.CAMPAIGN:
        cooldown_result = await _check_campaign_cooldown(ctx)
        if cooldown_result.is_blocked:
            # Permitir bypass via Slack
            if _is_human_slack_bypass(ctx):
                result = GuardrailResult(
                    decision=GuardrailDecision.ALLOW,
                    reason_code="campaign_cooldown",
                    human_bypass=True,
                    details={"bypass_reason": ctx.bypass_reason}
                )
                await _emit_guardrail_event(ctx, result, "outbound_bypass")
                return result

            result = GuardrailResult(
                decision=GuardrailDecision.BLOCK,
                reason_code="campaign_cooldown",
                details=cooldown_result.details
            )
            await _emit_guardrail_event(ctx, result, "outbound_blocked")
            return result
    ...


async def _check_campaign_cooldown(ctx: OutboundContext) -> CooldownResult:
    """
    Verifica cooldown entre campanhas.

    R5a: Ultima campanha diferente foi ha menos de 3 dias?
    R5b: Medico respondeu nos ultimos 7 dias?
    """
    # R5a: Campanhas diferentes em janela curta
    ultima = await buscar_ultima_campanha_enviada(ctx.cliente_id)
    if ultima and ultima.campaign_id != ctx.campaign_id:
        dias = (now() - ultima.sent_at).days
        if dias < CAMPAIGN_COOLDOWN_DAYS:
            return CooldownResult(
                is_blocked=True,
                reason="different_campaign_recent",
                details={
                    "last_campaign_type": ultima.campaign_type,
                    "days_since": dias,
                    "cooldown_days": CAMPAIGN_COOLDOWN_DAYS
                }
            )

    # R5b: Respondeu recentemente
    if await medico_respondeu_recentemente(ctx.cliente_id, dias=RESPONSE_COOLDOWN_DAYS):
        # Exceto se tem conversa ativa com oferta
        if not await tem_conversa_ativa_com_oferta(ctx.cliente_id):
            return CooldownResult(
                is_blocked=True,
                reason="responded_recently",
                details={"cooldown_days": RESPONSE_COOLDOWN_DAYS}
            )

    return CooldownResult(is_blocked=False)
```

### Tarefas

- [x] T05.1: Criar tabela `campaign_contact_history` ✅
- [x] T05.2: Registrar envio na tabela quando outcome=SENT ✅
- [x] T05.3: Criar `_check_campaign_cooldown` no guardrails/check.py ✅
- [x] T05.4: Integrar como R5 no `check_outbound_guardrails` ✅
- [x] T05.5: Garantir que `method=REPLY` NAO passa por R5 ✅
- [x] T05.6: Permitir bypass via Slack (com evento de auditoria) ✅
- [x] T05.7: Configuracao de dias via feature_flags ✅ (constantes configuraveis)
- [x] T05.8: Testes - especialmente que reply nao e bloqueado ✅ (14 testes)

### Criterios de Aceite

- [x] Medico nao recebe 2 campanhas diferentes em 3 dias
- [x] Medico que respondeu nao recebe campanha por 7 dias
- [x] Reply NUNCA e bloqueado por cooldown (e atendimento)
- [x] Bypass via Slack funciona e gera evento `OUTBOUND_BYPASS`
- [x] Parametros configuraveis sem deploy (via constantes, futuro: feature_flags)
- [x] Outcome `BLOCKED_CAMPAIGN_COOLDOWN` aparece nos relatorios

---

## E06: Briefing Tatico (Slack)

**Objetivo:** Permitir sync imediato de briefing via Slack com feedback rico.

### Motivacao

60min de latencia e aceitavel para mudancas programadas, mas briefing e arma tatica:
- Hospital com urgencia
- Feriado nao mapeado
- Problema reputacional
- Mudanca de margem

### Implementacao

```python
# app/tools/slack/briefing.py

@tool_function
async def sincronizar_briefing_agora(session: SlackSession) -> str:
    """
    Forca sincronizacao imediata do briefing.

    Exemplos:
    - "@Julia sync briefing agora"
    - "@Julia atualiza briefing"
    - "@Julia puxa briefing"
    """
    # Rate limit: max 1 sync a cada 5 minutos
    if await _sync_em_cooldown():
        return "Calma! Ultimo sync foi ha menos de 5 minutos. Aguarde um pouco."

    hash_antes = await _get_briefing_hash_atual()

    resultado = await sincronizar_briefing()

    hash_depois = resultado.get("hash", "")

    # Emitir evento de auditoria
    await emit_event(BusinessEvent(
        event_type=EventType.BRIEFING_SYNC_TRIGGERED,
        source=EventSource.SLACK,
        event_props={
            "actor_id": session.user_id,
            "hash_antes": hash_antes,
            "hash_depois": hash_depois,
            "atualizado": resultado.get("atualizado", False),
        }
    ))

    if resultado.get("atualizado"):
        secoes = resultado.get("secoes", [])
        return (
            f"Briefing sincronizado!\n\n"
            f"*Documento:* {resultado.get('titulo', 'N/A')}\n"
            f"*Secoes atualizadas:* {', '.join(secoes) if secoes else 'todas'}\n"
            f"*Hash:* `{hash_antes[:8]}` → `{hash_depois[:8]}`\n"
            f"*Timestamp:* {datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        return (
            f"Briefing ja estava atualizado (sem mudancas detectadas)\n"
            f"*Hash atual:* `{hash_depois[:8]}`"
        )
```

### Padroes NLP

```python
PATTERNS_SYNC_BRIEFING = [
    "sync briefing",
    "sincroniza briefing",
    "atualiza briefing",
    "puxa briefing",
    "recarrega briefing",
    "refresh briefing",
]
```

### Tarefas

- [x] T06.1: Adicionar tool `sincronizar_briefing_agora` no Slack ✅
- [x] T06.2: Adicionar padroes NLP para reconhecimento ✅ (na descricao da tool)
- [x] T06.3: Implementar rate limit (1 sync / 5 min) ✅
- [x] T06.4: Emitir evento `BRIEFING_SYNC_TRIGGERED` com actor_id ✅
- [x] T06.5: Retornar diff resumido (hash antes → depois) ✅
- [x] T06.6: Intervalo automatico mantido em 60min (sync manual resolve urgencia)
- [x] T06.7: Padroes NLP na descricao da tool (Claude entende)
- [x] T06.8: Testes ✅ (15 testes)

### Criterios de Aceite

- [x] Gestor pode forcar sync via Slack com linguagem natural
- [x] Rate limit impede spam (1 sync / 5 min)
- [x] Feedback mostra hash antes/depois e secoes atualizadas
- [x] Evento `BRIEFING_SYNC_TRIGGERED` emitido com actor_id
- [x] Tool registrada e disponivel no Slack

---

## Ordem de Implementacao

```
Semana 1: E01 (Outcome) + E04 (Deduped)
          └─ Fundacao: outcome correto e semantica clara

Semana 2: E02 (Atribuicao First/Last Touch)
          └─ Usar outcome=SENT como gatilho para setar touches

Semana 3: E03 (Unificacao) + E05 (Cooldown)
          └─ Views unificadas + regra de negocio como guardrail

Semana 4: E06 (Briefing) + Testes E2E + Documentacao
          └─ Quick win + validacao completa
```

**Por que E01 antes de E02?**
Quando setar `last_touch_campaign_id`, usamos `outcome=SENT` como gatilho.
So faz sentido setar touch quando de fato enviou, nao quando bloqueou/errou.

---

## Metricas de Sucesso

| Metrica | Antes | Depois |
|---------|-------|--------|
| Atribuicao de reply | 0% | 100% (invariantes C1-C3) |
| Reply rate por campanha | N/A | Medivel |
| Qualified rate por campanha | N/A | Medivel |
| Booked rate por campanha | N/A | Medivel |
| Distinguir deduped vs blocked | Nao | Sim |
| Fonte unica de envios | 2 tabelas | 1 view |
| Tempo para virar briefing | 60min | < 1min (Slack) |

---

## Dependencias

- Sprint 17 (Guardrails) - base para outcomes e R5
- Sprint 18 (Business Events) - eventos de auditoria
- Sprint 14 (Pipeline grupos) - padroes de processamento

---

## Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| Migracao de dados historicos | View unificada mantem acesso a ambas tabelas |
| Performance de atribuicao | Indice em envios + cache de 7 dias |
| Quebra de relatorios existentes | Manter `envios_campanha` readonly |
| Reply bloqueado por cooldown | Explicito: method=REPLY nao passa por R5 |
| Spam de sync briefing | Rate limit 1 sync / 5 min |

---

## Arquivos Principais

| Arquivo | Mudanca |
|---------|---------|
| `app/services/campaign_attribution.py` | NOVO - logica de atribuicao first/last |
| `app/services/campaign_cooldown.py` | NOVO - verificacao de cooldown |
| `app/services/campaign_sends.py` | NOVO - repository unificado via view |
| `app/services/outbound.py` | Adicionar deduped, outcome detalhado |
| `app/workers/fila_worker.py` | Registrar outcome completo |
| `app/pipeline/processors/attribution.py` | NOVO - atribuir campaign_id no inbound |
| `app/tools/slack/briefing.py` | Tool de sync imediato |
| `app/services/guardrails/check.py` | Adicionar R5 (cooldown campanha) |
| `app/services/guardrails/types.py` | Enum SendOutcome |
