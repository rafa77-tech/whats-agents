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

## Epicos

| Epico | Titulo | Prioridade | Complexidade |
|-------|--------|------------|--------------|
| E01 | Atribuicao Last-Touch | P0 | Media |
| E02 | Outcome no Send | P0 | Baixa |
| E03 | Unificacao de Envios | P1 | Media |
| E04 | Status Deduped Explicito | P1 | Baixa |
| E05 | Cooldown por Campanha | P1 | Media |
| E06 | Briefing Tatico (Slack) | P2 | Baixa |

---

## E01: Atribuicao Last-Touch

**Objetivo:** Quando medico responde, saber de qual campanha veio.

### Modelo de Dados

```sql
-- Adicionar a conversations
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_campaign_id UUID REFERENCES campanhas(id);
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_type TEXT; -- discovery, oferta, reativacao, followup
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_touch_sent_at TIMESTAMPTZ;

-- Indice para busca rapida
CREATE INDEX IF NOT EXISTS idx_conversations_last_touch
ON conversations(last_touch_campaign_id) WHERE last_touch_campaign_id IS NOT NULL;
```

### Logica de Atribuicao

```
QUANDO: Inbound recebido
ENTAO:
  1. Buscar ultimo envio para cliente_id nos ultimos 7 dias
  2. Se encontrado:
     - Atualizar conversations.last_touch_*
     - Emitir evento CAMPAIGN_REPLY_ATTRIBUTED
  3. Se nao encontrado:
     - Manter last_touch_* como NULL (resposta organica)
```

### Tarefas

- [ ] T01.1: Migracao - adicionar colunas em conversations
- [ ] T01.2: Servico `atribuir_last_touch(cliente_id, conversa_id)`
- [ ] T01.3: Integrar no pipeline de inbound (pos-LoadEntities)
- [ ] T01.4: Evento CAMPAIGN_REPLY_ATTRIBUTED no business_events
- [ ] T01.5: Testes unitarios e integracao

### Criterios de Aceite

- [ ] Conversa criada apos envio de campanha tem `last_touch_campaign_id` preenchido
- [ ] Conversa organica (sem envio previo) tem `last_touch_*` NULL
- [ ] Evento emitido permite auditoria completa
- [ ] Janela de atribuicao configuravel (default 7 dias)

---

## E02: Outcome no Send

**Objetivo:** Resultado do outbound propaga para registro de envio.

### Outcomes Padronizados

| Outcome | Descricao | Fonte |
|---------|-----------|-------|
| `sent` | Enviado com sucesso | Evolution API |
| `blocked_opted_out` | Bloqueado por opt-out | Guardrail R0 |
| `blocked_cooling_off` | Bloqueado por cooling_off | Guardrail R1 |
| `blocked_next_allowed` | Bloqueado por next_allowed_at | Guardrail R2 |
| `blocked_contact_cap` | Bloqueado por limite 7d | Guardrail R3 |
| `blocked_campaigns_disabled` | Campanhas desabilitadas | Guardrail R4a |
| `blocked_safe_mode` | Safe mode ativo | Guardrail R4b |
| `deduped` | Duplicado (mesmo conteudo recente) | Outbound dedupe |
| `failed` | Erro de envio | Evolution API |

### Modelo de Dados

```sql
-- Adicionar a fila_mensagens
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome TEXT;
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome_reason TEXT;
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS outcome_at TIMESTAMPTZ;

-- Enum check
ALTER TABLE fila_mensagens ADD CONSTRAINT check_outcome
CHECK (outcome IS NULL OR outcome IN (
  'sent', 'blocked_opted_out', 'blocked_cooling_off',
  'blocked_next_allowed', 'blocked_contact_cap',
  'blocked_campaigns_disabled', 'blocked_safe_mode',
  'deduped', 'failed'
));
```

### Tarefas

- [ ] T02.1: Migracao - adicionar colunas de outcome
- [ ] T02.2: Criar `OutcomeMapper` para traduzir guardrail → outcome
- [ ] T02.3: Atualizar `fila_worker` para registrar outcome
- [ ] T02.4: Atualizar `send_outbound_message` para retornar outcome detalhado
- [ ] T02.5: Testes

### Criterios de Aceite

- [ ] Todo envio processado tem `outcome` preenchido
- [ ] Bloqueios por guardrail tem `outcome_reason` com detalhes
- [ ] Deduplicacao tem outcome `deduped` (nao `blocked`)
- [ ] Relatorio de campanha pode filtrar por outcome

---

## E03: Unificacao de Envios

**Objetivo:** Fonte unica de verdade para envios de campanha.

### Estrategia

Manter `fila_mensagens` como mecanismo de envio, deprecar `envios_campanha` gradualmente.

### Modelo de Dados

```sql
-- View unificada para relatorios
CREATE OR REPLACE VIEW campaign_sends AS
SELECT
  fm.id as send_id,
  fm.cliente_id,
  (fm.metadata->>'campanha_id')::UUID as campaign_id,
  fm.tipo as send_type,
  fm.status,
  fm.outcome,
  fm.outcome_reason,
  fm.created_at as queued_at,
  fm.enviada_em as sent_at,
  fm.outcome_at,
  'fila_mensagens' as source
FROM fila_mensagens fm
WHERE fm.metadata->>'campanha_id' IS NOT NULL

UNION ALL

SELECT
  ec.id as send_id,
  ec.cliente_id,
  ec.campanha_id as campaign_id,
  ec.tipo as send_type,
  ec.status,
  CASE
    WHEN ec.status = 'enviado' THEN 'sent'
    WHEN ec.status = 'bloqueado' THEN 'blocked_guardrail'
    WHEN ec.status = 'erro' THEN 'failed'
    ELSE NULL
  END as outcome,
  ec.erro as outcome_reason,
  ec.created_at as queued_at,
  ec.enviado_em as sent_at,
  ec.enviado_em as outcome_at,
  'envios_campanha' as source
FROM envios_campanha ec;

-- Indice para performance
CREATE INDEX IF NOT EXISTS idx_fila_mensagens_campanha
ON fila_mensagens((metadata->>'campanha_id'))
WHERE metadata->>'campanha_id' IS NOT NULL;
```

### Tarefas

- [ ] T03.1: Criar view `campaign_sends`
- [ ] T03.2: Atualizar `criar_envios_campanha` para usar apenas `fila_mensagens`
- [ ] T03.3: Criar servico `CampaignSendsRepository` que usa a view
- [ ] T03.4: Deprecar uso direto de `envios_campanha` em novos codigos
- [ ] T03.5: Documentar que `envios_campanha` e legado

### Criterios de Aceite

- [ ] Todos os relatorios de campanha usam `campaign_sends`
- [ ] Novos envios vao para `fila_mensagens` com `metadata.campanha_id`
- [ ] Dados historicos de `envios_campanha` continuam visiveis
- [ ] Nenhum codigo novo escreve em `envios_campanha`

---

## E04: Status Deduped Explicito

**Objetivo:** Distinguir deduplicacao de bloqueio por guardrail.

### Contexto

Hoje, se outbound detecta duplicidade (mesmo conteudo em janela), isso cai como "blocked". Mas nao e bloqueio por permissao - e proteção contra spam acidental.

### Alteracoes

```python
# app/services/outbound.py - retornar reason especifico
class OutboundResult:
    success: bool
    blocked: bool
    deduped: bool  # NOVO
    block_reason: str | None
    dedupe_reason: str | None  # NOVO
```

### Tarefas

- [ ] T04.1: Adicionar `deduped` e `dedupe_reason` ao `OutboundResult`
- [ ] T04.2: Detectar deduplicacao antes de guardrails no `send_outbound_message`
- [ ] T04.3: Emitir evento `OUTBOUND_DEDUPED` (separado de `OUTBOUND_BLOCKED`)
- [ ] T04.4: Mapear para outcome `deduped` no fila_worker
- [ ] T04.5: Testes

### Criterios de Aceite

- [ ] Mensagem duplicada retorna `deduped=True`, `blocked=False`
- [ ] Evento `OUTBOUND_DEDUPED` emitido para auditoria
- [ ] Outcome `deduped` aparece nos relatorios de campanha
- [ ] Metricas de "tentativas" vs "rejeicoes" ficam precisas

---

## E05: Cooldown por Campanha

**Objetivo:** Evitar que medico receba campanhas diferentes em janela curta.

### Regras de Negocio

| Regra | Descricao | Default |
|-------|-----------|---------|
| R1 | Nao enviar 2 campanhas diferentes em X dias | 3 dias |
| R2 | Se respondeu, suspender campanhas por Y dias | 7 dias |
| R3 | Exceto: oferta ativa em conversa aberta | - |

### Modelo de Dados

```sql
-- Rastrear ultimo envio por tipo de campanha
CREATE TABLE IF NOT EXISTS campaign_contact_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id UUID NOT NULL REFERENCES clientes(id),
  campaign_id UUID NOT NULL REFERENCES campanhas(id),
  campaign_type TEXT NOT NULL,
  sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Indice para busca rapida
  CONSTRAINT idx_campaign_contact_unique
    UNIQUE (cliente_id, campaign_id)
);

CREATE INDEX idx_campaign_contact_lookup
ON campaign_contact_history(cliente_id, sent_at DESC);
```

### Logica

```python
async def pode_enviar_campanha(cliente_id: str, campaign_type: str) -> tuple[bool, str]:
    """
    Verifica se pode enviar campanha para o medico.

    Returns:
        (pode_enviar, motivo)
    """
    # R1: Ultima campanha diferente foi ha menos de 3 dias?
    ultima = await buscar_ultima_campanha(cliente_id)
    if ultima and ultima.campaign_type != campaign_type:
        dias = (now() - ultima.sent_at).days
        if dias < COOLDOWN_CAMPANHAS_DIFERENTES_DIAS:
            return False, f"campanha_recente:{ultima.campaign_type}"

    # R2: Medico respondeu nos ultimos 7 dias?
    if await medico_respondeu_recentemente(cliente_id, dias=7):
        # R3: Exceto se tem conversa ativa com oferta
        if not await tem_conversa_ativa_com_oferta(cliente_id):
            return False, "respondeu_recentemente"

    return True, "ok"
```

### Tarefas

- [ ] T05.1: Criar tabela `campaign_contact_history`
- [ ] T05.2: Registrar envio na tabela apos sucesso
- [ ] T05.3: Criar `CampaignCooldownService` com regras R1, R2, R3
- [ ] T05.4: Integrar como guardrail adicional (R5) no check_outbound_guardrails
- [ ] T05.5: Configuracao de dias via settings/feature_flags
- [ ] T05.6: Testes

### Criterios de Aceite

- [ ] Medico nao recebe 2 campanhas diferentes em 3 dias
- [ ] Medico que respondeu nao recebe campanha por 7 dias (exceto conversa ativa)
- [ ] Bloqueio emite evento `CAMPAIGN_COOLDOWN_BLOCKED`
- [ ] Parametros configuraveis sem deploy

---

## E06: Briefing Tatico (Slack)

**Objetivo:** Permitir sync imediato de briefing via Slack.

### Motivacao

60min de latencia e aceitavel para mudancas programadas, mas briefing e arma tatica:
- Hospital com urgencia
- Feriado nao mapeado
- Problema reputacional
- Mudanca de margem

### Implementacao

```python
# app/tools/slack/briefing.py - adicionar tool

@tool_function
async def sincronizar_briefing_agora(session: SlackSession) -> str:
    """
    Forca sincronizacao imediata do briefing.

    Exemplo: "@Julia sync briefing agora"
    """
    resultado = await sincronizar_briefing()

    if resultado.get("atualizado"):
        return (
            f"Briefing sincronizado!\n"
            f"Documento: {resultado.get('titulo', 'N/A')}\n"
            f"Secoes atualizadas: {len(resultado.get('secoes', []))}"
        )
    else:
        return "Briefing ja estava atualizado (sem mudancas detectadas)"
```

### Tarefas

- [ ] T06.1: Adicionar tool `sincronizar_briefing_agora` no Slack
- [ ] T06.2: Adicionar padroes NLP: "sync briefing", "atualiza briefing", "puxa briefing"
- [ ] T06.3: Considerar reducao do intervalo para 15min (config)
- [ ] T06.4: Feedback visual no Slack com detalhes do sync
- [ ] T06.5: Testes

### Criterios de Aceite

- [ ] Gestor pode forcar sync via Slack com linguagem natural
- [ ] Feedback mostra se houve mudanca ou nao
- [ ] Opcao de intervalo menor (15min) disponivel via config
- [ ] Documentado no docs/BRIEFINGS.md

---

## Ordem de Implementacao

```
Semana 1: E01 (Atribuicao) + E02 (Outcome)
          └─ Fundacao: saber de onde veio e o que aconteceu

Semana 2: E04 (Deduped) + E03 (Unificacao)
          └─ Limpeza: distinguir deduplicacao, unificar fonte

Semana 3: E05 (Cooldown) + E06 (Briefing)
          └─ Operacao: regras de negocio + agilidade tatica
```

---

## Metricas de Sucesso

| Metrica | Antes | Depois |
|---------|-------|--------|
| Conversao por campanha | N/A (nao medido) | Medivel |
| Atribuicao de reply | 0% | 100% |
| Distinguir deduped vs blocked | Nao | Sim |
| Fonte unica de envios | 2 tabelas | 1 view |
| Tempo para virar briefing | 60min | < 1min (Slack) |

---

## Dependencias

- Sprint 17 (Guardrails) - base para outcomes
- Sprint 18 (Business Events) - eventos de auditoria
- Sprint 14 (Pipeline grupos) - padroes de processamento

---

## Riscos

| Risco | Mitigacao |
|-------|-----------|
| Migracao de dados historicos | View unificada mantem acesso a ambas tabelas |
| Performance de atribuicao | Indice em envios + cache de 7 dias |
| Quebra de relatorios existentes | Manter `envios_campanha` readonly |

---

## Arquivos Principais

| Arquivo | Mudanca |
|---------|---------|
| `app/services/campaign_attribution.py` | NOVO - logica de atribuicao |
| `app/services/campaign_cooldown.py` | NOVO - regras de cooldown |
| `app/services/campaign_sends.py` | NOVO - repository unificado |
| `app/services/outbound.py` | Adicionar deduped ao result |
| `app/workers/fila_worker.py` | Registrar outcome |
| `app/pipeline/processors/` | Adicionar AttributionProcessor |
| `app/tools/slack/briefing.py` | Tool de sync imediato |
| `app/services/guardrails/check.py` | Adicionar R5 (cooldown campanha) |
