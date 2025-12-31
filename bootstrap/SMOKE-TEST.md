# SMOKE TEST PRODUÇÃO (PÓS-DEPLOY) — Padrão de Auditoria

**Versão:** 3.0
**Última atualização:** 31/12/2025

Este documento define um **procedimento verificável**, com **critérios objetivos de PASSA/FALHA** e **evidências coletáveis**, para liberar tráfego (ex.: webhooks do Evolution) após deploy em produção.

> Regra de ouro: **qualquer falha em teste BLOQUEADOR = rollback imediato** (ver seção "Rollback").

---

## Escopo e Premissas

- Stack: Railway (api/worker/scheduler) + Redis + Supabase (service_role).
- Horário operacional (para envio PROATIVO): **08:00–20:00 BRT** (customize se diferente).
- Mensagens **REPLY (inbound do médico)** devem funcionar **24/7**.
- O endpoint **/health/deep** é a fonte primária de verificação de ambiente e schema.

---

## Evidências a Coletar (obrigatório)

Ao final, anexe/registre:

1. Saída JSON do **/health/deep** (inteiro)
2. Screenshot/trecho dos **logs do Railway** comprovando RUN_MODE e APP_ENV
3. Prints das queries SQL dos testes 4–7 (ou export do SQL editor)
4. Registro de execução (tabela "Histórico de Execuções" no fim)

---

## Pré-requisitos

- Você tem **SUPABASE_URL** e **SUPABASE_SERVICE_ROLE_KEY** do ambiente alvo.
- Você sabe a URL pública do Railway: **RAILWAY_APP_URL**.
- Você tem acesso ao Supabase SQL Editor (ou psql).

---

## Matriz de Testes

| # | Teste | Tipo | Objetivo |
|---|-------|------|----------|
| 1 | Deep Health + Hard Guards | BLOQUEADOR | Garantir ambiente correto, Redis ok, Supabase ok, schema ok |
| 2 | RUN_MODE segregado | BLOQUEADOR | Garantir api/worker/scheduler isolados (sem scheduler duplicado) |
| 3 | Redis operacional | BLOQUEADOR | Garantir read/write e TTL (não só "conectado") |
| 4 | Schema crítico + Markers + Flags | BLOQUEADOR | Garantir tabelas/views críticas e markers de ambiente |
| 5 | Prompt Contract (core prompts + sentinelas) | BLOQUEADOR | Garantir prompts essenciais existem/ativos e contrato de sentinelas |
| 6 | Guardrails Backend (quiet-hours + opt-out) | BLOQUEADOR | Garantir que backend bloqueia proativo fora do horário e opt-out |
| 7 | Views funcionais (campaign_*) | RECOMENDADO | Garantir campaign_sends/campaign_metrics respondem e agregam |
| 8 | Touch Reconciliation job | RECOMENDADO | Garantir job executa, é idempotente e monotônico |

---

## 1) Deep Health + Hard Guards (BLOQUEADOR)

### Procedimento

```bash
curl -sS "$RAILWAY_APP_URL/health/deep" | jq .
```

### Critérios de PASSA

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| `status` | `"healthy"` | [ ] |
| `deploy_safe` | `true` | [ ] |
| `checks.environment.status` | `"ok"` | [ ] |
| `checks.environment.app_env` | `"production"` | [ ] |
| `checks.project_ref.status` | `"ok"` | [ ] |
| `checks.redis.status` | `"ok"` | [ ] |
| `checks.supabase.status` | `"ok"` | [ ] |
| `checks.tables.status` | `"ok"` | [ ] |
| `checks.views.status` | `"ok"` | [ ] |
| `checks.prompts.status` | `"ok"` ou `"warning"` | [ ] |

### Falha = Ação imediata

Se qualquer item falhar:
1. **Interromper tráfego** (não liberar webhook)
2. **Rollback** (ver seção Rollback)
3. Abrir incidente (registrar evidências)

---

## 2) RUN_MODE Segregado (BLOQUEADOR)

### Objetivo

Comprovar que:
- Serviço **api** roda com `RUN_MODE=api`
- Serviço **worker** roda com `RUN_MODE=worker`
- Serviço **scheduler** roda com `RUN_MODE=scheduler`
- **APP_ENV** e **SUPABASE_PROJECT_REF** coerentes com o marker do banco

### Procedimento

No Railway (Logs), coletar 1 linha por serviço contendo:
- `RUN_MODE=...`
- `APP_ENV=...`
- `SUPABASE_PROJECT_REF=...`

### Critério de PASSA

- 3 serviços exibem seu `RUN_MODE` correto **e apenas 1 scheduler** está ativo (1 réplica).

### Evidência

| Serviço | RUN_MODE | APP_ENV | Réplicas |
|---------|----------|---------|----------|
| API | | | |
| WORKER | | | |
| SCHEDULER | | | 1 |

---

## 3) Redis Operacional (BLOQUEADOR)

> O health/deep já valida Redis, mas este teste confirma **read/write/TTL**.

### Procedimento

```bash
curl -sS "$RAILWAY_APP_URL/health/ready" | jq .
```

### Critério de PASSA

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| `status` | `"ready"` | [ ] |
| `checks.redis` | `"ok"` | [ ] |

---

## 4) Schema Crítico + Markers + Flags (BLOQUEADOR)

### Procedimento (SQL)

No Supabase SQL Editor, rode:

```sql
-- 4.1 Markers de ambiente (hard guard)
SELECT
  MAX(CASE WHEN key='environment' THEN value END) AS environment,
  MAX(CASE WHEN key='supabase_project_ref' THEN value END) AS supabase_project_ref
FROM public.app_settings
WHERE key IN ('environment','supabase_project_ref');

-- 4.2 Tabelas críticas
SELECT
  to_regclass('public.clientes') AS clientes,
  to_regclass('public.vagas') AS vagas,
  to_regclass('public.doctor_state') AS doctor_state,
  to_regclass('public.fila_mensagens') AS fila_mensagens,
  to_regclass('public.conversations') AS conversations,
  to_regclass('public.intent_log') AS intent_log,
  to_regclass('public.touch_reconciliation_log') AS touch_reconciliation_log;

-- 4.3 Views críticas
SELECT
  to_regclass('public.campaign_sends') AS campaign_sends,
  to_regclass('public.campaign_metrics') AS campaign_metrics;

-- 4.4 Feature flags mínimas
SELECT key, value->>'enabled' AS enabled
FROM public.feature_flags
WHERE ativo = true;
```

### Critério de PASSA

- Markers retornam `production` e `jyqgbzhqavgpxqacduoi`
- Todas `to_regclass(...)` retornam **nome da relação**, não `NULL`

---

## 5) Prompt Contract (BLOQUEADOR)

### Objetivo

Garantir que os 3 prompts core existem, estão ativos e que o **julia_base** contém sentinelas obrigatórias (contrato auditável).

### Procedimento via /health/deep

O campo `checks.prompts` deve mostrar:

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| `status` | `"ok"` | [ ] |
| `missing` | `[]` (vazio) | [ ] |
| `inactive` | `[]` (vazio) | [ ] |
| `too_short` | `[]` (vazio) | [ ] |
| `missing_sentinels` | `[]` (vazio) | [ ] |
| `versions.julia_base` | `"v2"` | [ ] |

### Procedimento (SQL de validação)

```sql
-- 5.1 Core prompts ativos
SELECT nome, versao, tipo, ativo, LENGTH(conteudo) AS chars
FROM public.prompts
WHERE nome IN ('julia_base','julia_tools','julia_primeira_msg')
ORDER BY nome;

-- 5.2 Contrato de sentinelas BLOQUEADORAS no julia_base
SELECT
  nome,
  (conteudo LIKE '%[INVARIANT:INBOUND_ALWAYS_REPLY]%') AS has_inbound_always_reply,
  (conteudo LIKE '%[INVARIANT:OPTOUT_ABSOLUTE]%') AS has_optout_absolute,
  (conteudo LIKE '%[INVARIANT:KILL_SWITCHES_PRIORITY]%') AS has_kill_switches,
  (conteudo LIKE '%[INVARIANT:NO_CONFIRM_WITHOUT_RESERVATION]%') AS has_no_confirm,
  (conteudo LIKE '%[INVARIANT:NO_IDENTITY_DEBATE]%') AS has_no_identity,
  (conteudo LIKE '%[CAPABILITY:HANDOFF]%') AS has_handoff,
  (conteudo LIKE '%[FALLBACK:DIRETRIZES_EMPTY_OK]%') AS has_fallback
FROM public.prompts
WHERE nome='julia_base' AND ativo=true;
```

### Critério de PASSA

- Existem 3 prompts core com `ativo=true`
- `LENGTH(julia_base.conteudo) >= 2000`
- **Todas** as sentinelas BLOQUEADOR retornam `true`

---

## 6) Guardrails Backend (BLOQUEADOR)

### Objetivo

Validar que as linhas de defesa do backend funcionam independente do LLM.

### 6.1 Quiet Hours Bloqueia Proativo

Se existir endpoint de dry-run ou view de auditoria:

```sql
-- Verificar se existem envios BLOCKED_QUIET_HOURS recentes
-- (isso comprova que o guardrail funciona)
SELECT outcome, COUNT(*)
FROM fila_mensagens
WHERE method = 'CAMPAIGN'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY outcome;
```

**Critério:** Se houver `BLOCKED_QUIET_HOURS` no histórico, guardrail está funcionando.

**Teste manual alternativo:**
1. Criar campanha de teste para envio fora do horário (ex: 03:00)
2. Verificar que outcome = `BLOCKED_QUIET_HOURS`

### 6.2 Opt-out Absoluto

```sql
-- Verificar médicos com opt-out ativo
SELECT c.id, c.nome, c.telefone, c.opted_out, c.opted_out_at
FROM clientes c
WHERE c.opted_out = true
LIMIT 5;

-- Verificar se há tentativas bloqueadas por opt-out
SELECT outcome, COUNT(*)
FROM fila_mensagens
WHERE outcome = 'BLOCKED_OPTED_OUT'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY outcome;
```

**Critério:** Se `BLOCKED_OPTED_OUT` existe no histórico, guardrail está funcionando.

**Teste manual alternativo:**
1. Marcar médico de teste com `opted_out = true`
2. Tentar enviar mensagem proativa
3. Verificar que outcome = `BLOCKED_OPTED_OUT`

### Critério de PASSA

| Guardrail | Evidência | Resultado |
|-----------|-----------|-----------|
| Quiet Hours | Existe `BLOCKED_QUIET_HOURS` ou teste passou | [ ] |
| Opt-out | Existe `BLOCKED_OPTED_OUT` ou teste passou | [ ] |

---

## 7) Views Funcionais (campaign_*) (RECOMENDADO)

### Procedimento (SQL)

```sql
-- 7.1 campaign_sends responde
SELECT * FROM public.campaign_sends
ORDER BY sent_at DESC NULLS LAST
LIMIT 5;

-- 7.2 campaign_metrics responde
SELECT * FROM public.campaign_metrics
ORDER BY campaign_id DESC
LIMIT 5;
```

### Critério de PASSA

- Queries executam sem erro
- Resultados coerentes com o estado do ambiente

---

## 8) Touch Reconciliation Job (RECOMENDADO)

### Procedimento (HTTP)

```bash
curl -sS -X POST "$RAILWAY_APP_URL/jobs/reconcile-touches?limite=50&horas=72" | jq .
curl -sS "$RAILWAY_APP_URL/jobs/reconciliacao-status?minutos_timeout=15" | jq .
```

### Critérios de PASSA

- Execução retorna `status=ok` e `updated_count >= 0`
- Segunda execução imediata resulta em `0 updates` (idempotência)

---

## Checklist Final (assinar)

| # | Item | Resultado | Evidência |
|---|------|-----------|-----------|
| 1 | Deep health ok + deploy_safe true | ☐ PASS ☐ FAIL | anexar JSON |
| 2 | RUN_MODE correto (3 serviços) | ☐ PASS ☐ FAIL | anexar logs |
| 3 | Redis read/write ok | ☐ PASS ☐ FAIL | anexar output |
| 4 | Markers + schema crítico | ☐ PASS ☐ FAIL | anexar SQL |
| 5 | Prompt contract (7 sentinelas) | ☐ PASS ☐ FAIL | anexar SQL |
| 6 | Guardrails backend | ☐ PASS ☐ FAIL | anexar SQL |
| 7 | Views campaign_* | ☐ PASS ☐ FAIL | anexar SQL |
| 8 | Reconciliation job | ☐ PASS ☐ FAIL | anexar outputs |

---

## Rollback (quando qualquer BLOQUEADOR falhar)

| Passo | Ação | Responsável | Evidência |
|------:|------|-------------|-----------|
| 1 | Desabilitar webhook Evolution (ou apontar para staging) | | |
| 2 | Pausar Julia via Slack (`pausar_julia`) | | |
| 3 | Reverter deploy no Railway (último release estável) | | |
| 4 | Reverter migration (se aplicável) **ou** hotfix forward-only | | |
| 5 | Rodar /health/deep até voltar `healthy` + `deploy_safe=true` | | |

---

## Histórico de Execuções

| Data/Hora (BRT) | Versão/Commit | Executor | Resultado | Observações |
|-----------------|---------------|----------|-----------|-------------|
| 31/12/2025 15:00 | 1ed7d47 | Claude | PASS | Smoke test inicial pós-deploy |
| | | | | |

---

## Referências

- `docs/PROMPT-COVERAGE.md` - Detalhes das sentinelas e arquitetura
- `docs/DEPLOY-PROD-REPORT.md` - Relatório completo do deploy
- `docs/RUNBOOK.md` - Procedimentos operacionais
