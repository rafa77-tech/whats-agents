# Smoke Test Pós-Deploy (PROD)

**Objetivo:** Validar invariantes críticos após deploy no Railway **ANTES** de apontar o webhook da Evolution.

**Versão:** 2.0
**Última atualização:** 30/12/2025
**Autor:** Equipe Julia + Auditoria Externa

---

## Pré-requisitos (BLOQUEADORES)

Antes de iniciar o smoke test, confirme:

- [ ] Deploy concluído no Railway (todos os serviços UP)
- [ ] Serviços criados: `julia-api` / `julia-worker` / `julia-scheduler`
- [ ] Variáveis de ambiente setadas:
  - [ ] `APP_ENV=production`
  - [ ] `SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi`
  - [ ] `SUPABASE_URL` (PROD)
  - [ ] `SUPABASE_SERVICE_KEY` (PROD)
  - [ ] `REDIS_URL`
  - [ ] `RUN_MODE` (diferente para cada serviço)
- [ ] Migrações/schema aplicados no Supabase PROD (bootstrap/01-schema.sql + 02-seeds.sql)
- [ ] Webhook Evolution **AINDA NÃO APONTADO** para PROD

---

## Evidência a Coletar

Para cada teste, anexar no ticket/PR de deploy:

- [ ] Output do curl `/health/deep` (JSON completo)
- [ ] Resultados das queries SQL (screenshots ou texto)
- [ ] Trechos de logs do Railway mostrando RUN_MODE
- [ ] Timestamp de cada verificação

---

## Teste 1 — Deep Health: Ambiente + Dependências (BLOQUEADOR)

### Comando

```bash
curl -sS https://SEU-APP.railway.app/health/deep | jq .
```

### Critério de Aceite (PASSA se TODOS)

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| HTTP Status | `200` | [ ] |
| `status` | `"healthy"` | [ ] |
| `checks.redis.status` | `"ok"` | [ ] |
| `checks.supabase.status` | `"ok"` | [ ] |
| `checks.tables.status` | `"ok"` | [ ] |
| `checks.views.status` | `"ok"` | [ ] |
| `checks.schema_version.status` | `"ok"` | [ ] |
| `checks.environment.status` | `"ok"` | [ ] |
| `checks.project_ref.status` | `"ok"` | [ ] |
| `deploy_safe` | `true` | [ ] |

### Validação de Hard Guards

| Verificação | Esperado | Resultado |
|-------------|----------|-----------|
| `APP_ENV` do container | `production` | [ ] |
| `environment` do banco | `production` | [ ] |
| APP_ENV == banco? | `true` | [ ] |
| `SUPABASE_PROJECT_REF` do container | `jyqgbzhqavgpxqacduoi` | [ ] |
| `supabase_project_ref` do banco | `jyqgbzhqavgpxqacduoi` | [ ] |
| Refs batem? | `true` | [ ] |

### Critério de FALHA

- Qualquer mismatch de ambiente = **CRITICAL**
- Ação: **STOP IMEDIATO** + não prosseguir + investigar variáveis

---

## Teste 2 — RUN_MODE: Serviços Segregados (BLOQUEADOR)

### Evidência (Railway Dashboard → Logs de cada serviço)

#### julia-api
```
=== Julia Entrypoint ===
RUN_MODE: api
APP_ENV: production
Starting API server...
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Checklist:**
- [ ] Log mostra `RUN_MODE: api`
- [ ] Log mostra `Starting API server...`
- [ ] **NÃO** mostra `Starting worker...` ou `Starting scheduler...`

#### julia-worker
```
=== Julia Entrypoint ===
RUN_MODE: worker
APP_ENV: production
Starting worker...
```

**Checklist:**
- [ ] Log mostra `RUN_MODE: worker`
- [ ] Log mostra `Starting worker...`
- [ ] **NÃO** mostra `Starting scheduler...`

#### julia-scheduler
```
=== Julia Entrypoint ===
RUN_MODE: scheduler
APP_ENV: production
Starting scheduler...
```

**Checklist:**
- [ ] Log mostra `RUN_MODE: scheduler`
- [ ] Log mostra `Starting scheduler...`
- [ ] **APENAS 1 INSTÂNCIA** do scheduler (verificar no Railway)

### Critério de FALHA

- Scheduler com mais de 1 réplica = **CRÍTICO** (jobs duplicados)
- Worker iniciando scheduler = **CRÍTICO**
- Ação: Ajustar `RUN_MODE` ou número de réplicas

---

## Teste 3 — Redis: Operação Real (BLOQUEADOR)

### Comando

```bash
curl -sS https://SEU-APP.railway.app/health/ready | jq .
```

### Critério de Aceite

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| HTTP Status | `200` | [ ] |
| `redis.connected` | `true` | [ ] |
| `redis.latency_ms` | `< 100` | [ ] |

### Teste Adicional (via /health/deep)

Verificar no output do Teste 1:
- [ ] `checks.redis.latency_ms` é razoável (< 50ms ideal)
- [ ] Sem erros de conexão nos logs

### Critério de FALHA

- Redis não conectado = **BLOQUEADOR**
- Latência > 500ms = **WARNING** (investigar)

---

## Teste 4 — Supabase: Schema Crítico (BLOQUEADOR)

### 4.1 Objetos Críticos Existem

Executar no **Supabase Dashboard → SQL Editor** (projeto PROD):

```sql
SELECT
  to_regclass('public.app_settings') AS app_settings,
  to_regclass('public.clientes') AS clientes,
  to_regclass('public.conversations') AS conversations,
  to_regclass('public.doctor_state') AS doctor_state,
  to_regclass('public.fila_mensagens') AS fila_mensagens,
  to_regclass('public.interacoes') AS interacoes,
  to_regclass('public.business_events') AS business_events,
  to_regclass('public.intent_log') AS intent_log,
  to_regclass('public.touch_reconciliation_log') AS touch_reconciliation_log,
  to_regclass('public.julia_status') AS julia_status,
  to_regclass('public.feature_flags') AS feature_flags;
```

**Critério:** TODAS as colunas retornam valor não-nulo (nome da tabela).

| Tabela | Existe? |
|--------|---------|
| app_settings | [ ] |
| clientes | [ ] |
| conversations | [ ] |
| doctor_state | [ ] |
| fila_mensagens | [ ] |
| interacoes | [ ] |
| business_events | [ ] |
| intent_log | [ ] |
| touch_reconciliation_log | [ ] |
| julia_status | [ ] |
| feature_flags | [ ] |

### 4.2 Views Críticas Existem

```sql
SELECT
  to_regclass('public.campaign_sends') AS campaign_sends,
  to_regclass('public.campaign_metrics') AS campaign_metrics;
```

| View | Existe? |
|------|---------|
| campaign_sends | [ ] |
| campaign_metrics | [ ] |

### 4.3 Markers de Ambiente

```sql
SELECT key, value
FROM public.app_settings
WHERE key IN ('environment', 'supabase_project_ref');
```

| Key | Valor Esperado | Valor Encontrado | OK? |
|-----|----------------|------------------|-----|
| environment | `production` | | [ ] |
| supabase_project_ref | `jyqgbzhqavgpxqacduoi` | | [ ] |

### 4.4 Feature Flags Essenciais

```sql
SELECT key, value->>'enabled' AS enabled
FROM public.feature_flags
WHERE key IN ('external_handoff', 'campaign_attribution', 'dynamic_lock', 'error_classifier');
```

| Flag | Esperado | Encontrado | OK? |
|------|----------|------------|-----|
| external_handoff | `true` | | [ ] |
| campaign_attribution | `true` | | [ ] |
| dynamic_lock | `true` | | [ ] |
| error_classifier | `true` | | [ ] |

### 4.5 Julia Status

```sql
SELECT status, motivo, alterado_via, created_at
FROM public.julia_status
ORDER BY created_at DESC
LIMIT 1;
```

| Campo | Valor | OK? |
|-------|-------|-----|
| status | `pausado` (antes de ativar) ou `ativo` | [ ] |
| alterado_via | `manual`, `slack`, `sistema`, ou `api` | [ ] |

### Critério de FALHA

- Qualquer tabela/view crítica ausente = **BLOQUEADOR**
- Markers de ambiente incorretos = **BLOQUEADOR**
- Ação: Aplicar migrations faltantes antes de continuar

---

## Teste 4b — Prompt Contract (BLOQUEADOR)

### Verificar via /health/deep

O campo `checks.prompts` no output do Teste 1 deve mostrar:

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| `status` | `ok` ou `warning` | [ ] |
| `missing` | `[]` (vazio) | [ ] |
| `inactive` | `[]` (vazio) | [ ] |
| `too_short` | `[]` (vazio) | [ ] |
| `missing_sentinels` | `[]` (vazio) | [ ] |
| `versions.julia_base` | `v2` | [ ] |

### Verificar Sentinelas no julia_base

```sql
SELECT nome, versao,
       conteudo LIKE '%[INVARIANT:INBOUND_ALWAYS_REPLY]%' AS inbound,
       conteudo LIKE '%[INVARIANT:OPTOUT_ABSOLUTE]%' AS optout,
       conteudo LIKE '%[INVARIANT:NO_CONFIRM_WITHOUT_RESERVATION]%' AS no_confirm,
       conteudo LIKE '%[INVARIANT:NO_IDENTITY_DEBATE]%' AS no_identity,
       conteudo LIKE '%[FALLBACK:DIRETRIZES_EMPTY_OK]%' AS fallback_ok,
       LENGTH(conteudo) AS tamanho
FROM prompts
WHERE nome = 'julia_base' AND ativo = true;
```

| Sentinela | Esperado | Encontrado |
|-----------|----------|------------|
| inbound | `true` | [ ] |
| optout | `true` | [ ] |
| no_confirm | `true` | [ ] |
| no_identity | `true` | [ ] |
| fallback_ok | `true` | [ ] |
| tamanho | `>= 2000` | [ ] |

### Critério de FALHA

- Qualquer sentinela bloqueadora ausente = **CRÍTICO**
- julia_base < 2000 chars = **CRÍTICO** (prompt truncado ou corrompido)
- Versão != v2 = **WARNING** (pode estar desatualizado)
- Ação: Verificar se UPDATE foi aplicado, re-executar se necessário

---

## Teste 5 — Contagem de Dados Migrados (RECOMENDADO)

Validar que migração DEV→PROD foi bem-sucedida:

```sql
SELECT
  'clientes' AS tabela, COUNT(*) AS registros FROM clientes
UNION ALL SELECT 'vagas', COUNT(*) FROM vagas
UNION ALL SELECT 'hospitais', COUNT(*) FROM hospitais
UNION ALL SELECT 'especialidades', COUNT(*) FROM especialidades
UNION ALL SELECT 'conhecimento_julia', COUNT(*) FROM conhecimento_julia
UNION ALL SELECT 'prompts', COUNT(*) FROM prompts
UNION ALL SELECT 'diretrizes', COUNT(*) FROM diretrizes
ORDER BY tabela;
```

| Tabela | Mínimo Esperado | Encontrado | OK? |
|--------|-----------------|------------|-----|
| clientes | > 29.000 | | [ ] |
| vagas | > 4.000 | | [ ] |
| hospitais | > 80 | | [ ] |
| especialidades | > 50 | | [ ] |
| conhecimento_julia | > 500 | | [ ] |
| prompts | = 3 | | [ ] |
| diretrizes | >= 4 | | [ ] |

> **Nota sobre prompts/diretrizes:**
> - `prompts`: 3 core (julia_base, julia_tools, julia_primeira_msg) com sentinelas
> - `diretrizes`: 4+ dinâmicas do Google Docs (foco_semana, tom_semana, etc.)
> - Ver `docs/PROMPT-COVERAGE.md` para detalhes

### Critério de FALHA

- Contagens de clientes/vagas/hospitais abaixo = **WARNING** (verificar migração)
- prompts < 3 = **CRÍTICO** (sistema sem prompts core)
- diretrizes = 0 = **WARNING** (briefing não sincronizado)

---

## Teste 6 — Fila e Reconciliation (RECOMENDADO)

### 6.1 Estrutura da Fila

```sql
SELECT
  status,
  COUNT(*) AS quantidade
FROM fila_mensagens
GROUP BY status
ORDER BY quantidade DESC;
```

**Critério:** Query executa sem erro (valida que tabela tem estrutura correta).

### 6.2 Campaign Metrics (View Funcional)

```sql
SELECT * FROM campaign_metrics LIMIT 1;
```

**Critério:** Query executa sem erro (valida que view não está quebrada).

### 6.3 Campaign Sends (View Funcional)

```sql
SELECT * FROM campaign_sends LIMIT 1;
```

**Critério:** Query executa sem erro.

---

## Teste 7 — Reconciliation Job (RECOMENDADO)

Se existir endpoint de teste:

```bash
curl -X POST "https://SEU-APP.railway.app/jobs/reconcile-touches?limite=1&horas=1" \
  -H "Authorization: Bearer SEU_JWT_TOKEN" | jq .
```

### Critério de Aceite

| Campo | Valor Esperado | Resultado |
|-------|----------------|-----------|
| HTTP Status | `200` | [ ] |
| `status` | `"completed"` | [ ] |
| Executa sem erro | `true` | [ ] |

---

## Decisão Final

### Se TODOS os testes BLOQUEADORES passaram:

1. **Ativar Julia** (se ainda não estiver ativa):
   ```sql
   INSERT INTO julia_status (status, motivo, alterado_via)
   VALUES ('ativo', 'Smoke test passou - ativando PROD', 'manual');
   ```

2. **Apontar webhook Evolution** para Railway:
   - URL: `https://SEU-APP.railway.app/webhook/evolution`

3. **Monitorar primeiras interações:**
   - [ ] Logs de inbound (primeiras 10 mensagens)
   - [ ] `/health/deep` a cada 5 minutos por 30 min
   - [ ] Slack notifications funcionando
   - [ ] `campaign_metrics` populando

---

## Se Algo Falhar

### Procedimento de Rollback

| Falha | Ação Imediata | Investigação |
|-------|---------------|--------------|
| Hard guard mismatch | NÃO apontar webhook, verificar variáveis Railway | Comparar APP_ENV com app_settings |
| Redis desconectado | NÃO apontar webhook, verificar Redis no Railway | Logs do serviço Redis |
| Tabela/view ausente | NÃO apontar webhook, aplicar migration | Comparar schema DEV vs PROD |
| Scheduler duplicado | Reduzir para 1 réplica | Verificar config no Railway |
| Health check 503 | NÃO apontar webhook | Verificar logs detalhados |

### Passos

1. **NÃO apontar webhook Evolution**
2. Documentar evidência da falha (logs, outputs)
3. Abrir ticket com evidências
4. Corrigir configuração/schema/variáveis
5. **Repetir smoke test do zero**
6. Só então liberar webhook

---

## Histórico de Execuções

| Data | Executor | Resultado | Notas |
|------|----------|-----------|-------|
| DD/MM/YYYY | Nome | PASSOU/FALHOU | Observações |

---

## Anexo: Comandos Úteis

### Health Checks

```bash
# Liveness (sempre 200 se app rodando)
curl -sS https://SEU-APP.railway.app/health

# Readiness (200 se Redis ok)
curl -sS https://SEU-APP.railway.app/health/ready

# Deep (200 se TUDO ok)
curl -sS https://SEU-APP.railway.app/health/deep | jq .

# Schema info
curl -sS https://SEU-APP.railway.app/health/schema | jq .

# Rate limit stats
curl -sS https://SEU-APP.railway.app/health/rate-limit | jq .
```

### Railway CLI

```bash
# Ver logs
railway logs -s julia-api --tail 100
railway logs -s julia-worker --tail 100
railway logs -s julia-scheduler --tail 100

# Status
railway status
```

### Supabase CLI

```bash
# Conectar ao PROD
supabase link --project-ref jyqgbzhqavgpxqacduoi

# Ver migrations
supabase db migrations list
```

---

*Documento de auditoria - Manter atualizado a cada deploy*
