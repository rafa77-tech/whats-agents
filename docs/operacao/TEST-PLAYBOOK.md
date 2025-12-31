# TEST-PLAYBOOK.md - Playbook de Testes por Ambiente

> **Sprint 18 - Auditoria e Integridade**
> Procedimentos de teste para ambientes DEV e PROD.

---

## Visao Geral

Este documento descreve os procedimentos de teste para validar que os ambientes estao configurados corretamente e seguros.

---

## Testes Pre-Deploy

### 1. Validar Ambiente Local

```bash
# Rodar testes unitarios
uv run pytest tests/unit/ -v --tb=short

# Rodar testes de integracao (requer Redis)
docker compose up -d redis
uv run pytest tests/integration/ -v --tb=short

# Verificar lint
uv run ruff check app/
uv run ruff format --check app/
```

### 2. Validar Docker Build

```bash
# Build local
docker build -t julia-api:test \
  --build-arg GIT_SHA=$(git rev-parse HEAD) \
  --build-arg BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) .

# Testar imports
docker run --rm --entrypoint python julia-api:test -c "import app; print('OK')"
```

---

## Testes Pos-Deploy

### 1. Health Check Basico

```bash
# PROD
curl -s https://api.revoluna.com/health | jq .

# DEV (ajustar URL)
curl -s https://dev-api.revoluna.com/health | jq .
```

**Esperado:**
```json
{
  "status": "healthy",
  "service": "julia-api"
}
```

### 2. Deep Health Check

```bash
# PROD
curl -s https://api.revoluna.com/health/deep | jq .

# DEV
curl -s https://dev-api.revoluna.com/health/deep | jq .
```

**Checklist do Response:**

- [ ] `status` = "healthy"
- [ ] `deploy_safe` = true
- [ ] `version.git_sha` != "unknown"
- [ ] `version.build_time` != "unknown"
- [ ] `checks.environment.status` = "ok"
- [ ] `checks.project_ref.status` = "ok" ou "skipped"
- [ ] `checks.dev_guardrails.status` = "ok" (DEV) ou "skipped" (PROD)
- [ ] `checks.redis.status` = "ok"
- [ ] `checks.supabase.status` = "ok"
- [ ] `checks.tables.status` = "ok"
- [ ] `checks.views.status` = "ok"
- [ ] `checks.prompts.status` = "ok"

### 3. Validar Schema Fingerprint

```bash
# Comparar fingerprint entre ambientes (devem ser similares se schema sincronizado)
DEV_FP=$(curl -s https://dev-api.revoluna.com/health/deep | jq -r '.schema.fingerprint')
PROD_FP=$(curl -s https://api.revoluna.com/health/deep | jq -r '.schema.fingerprint')

echo "DEV:  $DEV_FP"
echo "PROD: $PROD_FP"

if [ "$DEV_FP" = "$PROD_FP" ]; then
  echo "MATCH - Schemas sincronizados"
else
  echo "DRIFT - Schemas diferentes!"
fi
```

---

## Testes DEV Guardrails

### 1. Validar Allowlist Vazia Bloqueia

```bash
# Em ambiente DEV com OUTBOUND_ALLOWLIST vazia
# Tentar enviar mensagem deve retornar BLOCKED_DEV_ALLOWLIST

curl -X POST https://dev-api.revoluna.com/test/outbound \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "texto": "Teste"}'
```

**Esperado:**
```json
{
  "outcome": "BLOCKED_DEV_ALLOWLIST",
  "blocked": true
}
```

### 2. Validar Allowlist Configurada Permite

```bash
# Adicionar numero a allowlist no Railway:
# OUTBOUND_ALLOWLIST=5511999999999

# Redeploy e testar novamente
curl -X POST https://dev-api.revoluna.com/test/outbound \
  -H "Content-Type: application/json" \
  -d '{"telefone": "5511999999999", "texto": "Teste"}'
```

**Esperado:** Mensagem passa pelos guardrails

### 3. Validar /health/deep Reporta Allowlist

```bash
# DEV com allowlist vazia
curl -s https://dev-api.revoluna.com/health/deep | jq '.checks.dev_guardrails'
```

**Esperado:**
```json
{
  "status": "CRITICAL",
  "message": "DEV environment has EMPTY OUTBOUND_ALLOWLIST!...",
  "allowlist_configured": false
}
```

---

## Testes de Marcadores de Ambiente

### 1. Validar Environment Match

```bash
# Verificar app_settings no banco
# DEV
SELECT * FROM app_settings WHERE key = 'environment';
-- Deve retornar: value = 'dev'

# PROD
SELECT * FROM app_settings WHERE key = 'environment';
-- Deve retornar: value = 'production'
```

### 2. Validar Project Ref Match

```bash
# DEV
SELECT * FROM app_settings WHERE key = 'supabase_project_ref';
-- Deve retornar: value = 'ofpnronthwcsybfxnxgj'

# PROD
SELECT * FROM app_settings WHERE key = 'supabase_project_ref';
-- Deve retornar: value = 'jyqgbzhqavgpxqacduoi'
```

### 3. Testar Mismatch Detection

```bash
# Temporariamente setar APP_ENV errado e verificar /health/deep
# Deve retornar status CRITICAL com mensagem de mismatch
```

---

## Testes de Jobs Scheduler

### 1. Verificar Status dos Jobs

```bash
curl -s https://api.revoluna.com/health/jobs | jq '.status'
# Esperado: "healthy"

# Verificar jobs criticos
curl -s https://api.revoluna.com/health/jobs | jq '.alerts.critical_stale'
# Esperado: []
```

### 2. Verificar SLA dos Jobs

```bash
curl -s https://api.revoluna.com/health/jobs | jq '.jobs | to_entries[] | select(.value.is_stale == true) | .key'
# Esperado: Nenhum output (nenhum job stale)
```

---

## Testes WhatsApp

### 1. Verificar Conexao Evolution

```bash
curl -s https://api.revoluna.com/health/whatsapp | jq .
```

**Esperado:**
```json
{
  "connected": true,
  "state": "open"
}
```

### 2. Testar Envio (DEV apenas)

```bash
# APENAS em DEV com numero na allowlist
curl -X POST https://dev-api.revoluna.com/api/julia/test-send \
  -H "Content-Type: application/json" \
  -d '{
    "telefone": "5511999999999",
    "texto": "Teste de envio DEV"
  }'
```

---

## Checklist Pre-Producao

### Deploy PROD

- [ ] CI passou (lint, tests, build)
- [ ] `/health/deep` retorna `deploy_safe: true`
- [ ] `environment` match: APP_ENV = app_settings.environment
- [ ] `project_ref` match (se configurado)
- [ ] Prompts validados (sentinelas presentes)
- [ ] Redis conectado
- [ ] Supabase conectado
- [ ] WhatsApp conectado

### Deploy DEV

- [ ] CI passou
- [ ] `/health/deep` retorna `deploy_safe: true`
- [ ] `environment` = "dev"
- [ ] `OUTBOUND_ALLOWLIST` configurada
- [ ] `dev_guardrails.status` = "ok"
- [ ] Numero de teste na allowlist

---

## Troubleshooting Rapido

### /health/deep retorna 503

1. Verificar qual check falhou: `curl -s .../health/deep | jq '.checks | to_entries[] | select(.value.status != "ok")'`
2. Corrigir o check especifico
3. Re-testar

### CRITICAL: Environment Mismatch

1. Verificar `APP_ENV` no Railway
2. Verificar `app_settings.environment` no banco
3. Um dos dois esta errado - corrigir e redeploy

### DEV bloqueando tudo

1. Verificar `OUTBOUND_ALLOWLIST` no Railway
2. Se vazia, adicionar numeros de teste
3. Redeploy

### Schema fingerprint diferente

1. Comparar migrations entre ambientes
2. Aplicar migrations faltantes
3. Re-gerar fingerprint

---

## Historico

| Data | Alteracao |
|------|-----------|
| 2025-12-31 | Criacao do documento (Sprint 18 Auditoria) |
