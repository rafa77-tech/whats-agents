# Relatório Completo de Deploy - Julia API para Produção

**Data:** 30 de Dezembro de 2025
**Versão:** 2.0
**Autor:** Claude Code (assistido por Rafael Pivovar)
**Status:** ✅ Concluído

---

## Sumário

1. [Contexto e Ambientes](#1-contexto-e-ambientes)
2. [Configuração do Railway](#2-configuração-do-railway)
3. [CI/CD Pipeline](#3-cicd-pipeline)
4. [Dockerfile e Entrypoint](#4-dockerfile-e-entrypoint)
5. [Hard Guards de Ambiente](#5-hard-guards-de-ambiente)
6. [Bootstrap do Supabase PROD](#6-bootstrap-do-supabase-prod)
7. [Problema LID (Evolution API v2)](#7-problema-lid-evolution-api-v2)
8. [Erros Corrigidos Durante Deploy](#8-erros-corrigidos-durante-deploy)
9. [Migração de Dados DEV → PROD](#9-migração-de-dados-dev--prod)
10. [Validação e Health Checks](#10-validação-e-health-checks)
11. [Runbook e Operações](#11-runbook-e-operações)
12. [Commits Relacionados](#12-commits-relacionados)
13. [Lições Aprendidas](#13-lições-aprendidas)

---

## 1. Contexto e Ambientes

### 1.1 Infraestrutura

| Componente | DEV | PROD |
|------------|-----|------|
| **Supabase Project** | ofpnronthwcsybfxnxgj | jyqgbzhqavgpxqacduoi |
| **Nome** | banco_medicos | julia-prod |
| **API URL** | https://ofpnronthwcsybfxnxgj.supabase.co | https://jyqgbzhqavgpxqacduoi.supabase.co |
| **Região** | us-east-1 | us-east-1 |

### 1.2 Stack de Produção

| Componente | Tecnologia | Hospedagem |
|------------|------------|------------|
| Backend | Python 3.13+ / FastAPI | Railway |
| Banco de Dados | PostgreSQL + pgvector | Supabase |
| Cache/Filas | Redis | Railway (add-on) |
| WhatsApp | Evolution API v2 | Externo |
| LLM | Claude Haiku + Sonnet | Anthropic API |
| CI/CD | GitHub Actions | GitHub |

---

## 2. Configuração do Railway

### 2.1 Estrutura de Serviços

O Railway hospeda 3 serviços separados, todos usando o mesmo repositório:

```
railway-project/
├── julia-api       # RUN_MODE=api      (escala: 1-N)
├── julia-worker    # RUN_MODE=worker   (escala: 1-N)
└── julia-scheduler # RUN_MODE=scheduler (escala: 1 FIXO!)
```

⚠️ **CRÍTICO:** O scheduler NUNCA pode ter mais de 1 instância, ou jobs duplicam!

### 2.2 Arquivo `railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": null,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### 2.3 Variáveis de Ambiente no Railway

**Variáveis obrigatórias para cada serviço:**

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `RUN_MODE` | Tipo de serviço | `api`, `worker`, ou `scheduler` |
| `APP_ENV` | Ambiente (hard guard) | `production` |
| `SUPABASE_PROJECT_REF` | Ref do projeto (hard guard) | `jyqgbzhqavgpxqacduoi` |
| `SUPABASE_URL` | URL do Supabase PROD | `https://jyqgbzhqavgpxqacduoi.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Service key PROD | `eyJ...` |
| `REDIS_URL` | Injetado automaticamente | `redis://...` |
| `ANTHROPIC_API_KEY` | API key Anthropic | `sk-ant-...` |
| `JWT_SECRET_KEY` | Para tokens externos | `openssl rand -hex 32` |

**Lista completa (28 variáveis):**

```bash
# App
APP_NAME=Agente Julia
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Deploy/Runtime (CRÍTICOS)
APP_ENV=production
SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi
RUN_MODE=api  # Diferente para cada serviço!

# Segurança
JWT_SECRET_KEY=<gerado>
CORS_ORIGINS=https://app.revoluna.com

# Supabase PROD
SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# Voyage AI
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3.5-lite

# Evolution API
EVOLUTION_API_URL=https://evolution.seudominio.com
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=Revoluna

# Chatwoot
CHATWOOT_URL=https://chatwoot.seudominio.com
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_CHANNEL=#julia-gestao
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx

# Rate Limiting
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# Empresa
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
```

### 2.4 Redis no Railway

O Redis é adicionado como serviço via:
1. Railway Dashboard → "New" → "Database" → "Redis"
2. Railway injeta `REDIS_URL` automaticamente nos serviços vinculados

---

## 3. CI/CD Pipeline

### 3.1 Workflow GitHub Actions

**Arquivo:** `.github/workflows/ci.yml`

```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Job 1: Lint & Type Check
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      - run: uv run ruff check app/
      - run: uv run ruff format --check app/

  # Job 2: Testes (com Redis)
  test:
    needs: lint
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync --frozen
      - run: uv run pytest -v --tb=short
        env:
          ENVIRONMENT: test
          REDIS_URL: redis://localhost:6379/0
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  # Job 3: Build Docker
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Job 4: Deploy to Railway (apenas main)
  deploy:
    needs: build
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: railway up --detach

      - name: Wait for deployment
        run: sleep 60

      - name: Deep health check
        run: |
          APP_URL="${{ secrets.RAILWAY_APP_URL }}"
          for i in $(seq 1 5); do
            HTTP_STATUS=$(curl -s -o /tmp/response.json -w "%{http_code}" "$APP_URL/health/deep")
            if [ "$HTTP_STATUS" = "200" ]; then
              echo "Health check passed!"
              exit 0
            fi
            echo "Attempt $i failed, retrying in 15s..."
            sleep 15
          done
          echo "Health check failed!"
          exit 1

      - name: Notify Slack
        if: always()
        run: |
          curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d '{"text":"Deploy ${{ job.status }}: ${{ github.sha }}"}'
```

### 3.2 GitHub Secrets Necessários

| Secret | Descrição | Onde obter |
|--------|-----------|------------|
| `SUPABASE_URL` | URL projeto staging (testes) | Supabase Dashboard |
| `SUPABASE_SERVICE_KEY` | Service key staging | Supabase Dashboard |
| `ANTHROPIC_API_KEY` | API key Anthropic | console.anthropic.com |
| `RAILWAY_TOKEN` | Token de deploy | Railway → Account → Tokens |
| `RAILWAY_APP_URL` | URL da API no Railway | Railway Dashboard |
| `SLACK_WEBHOOK_URL` | Webhook Slack | Slack App settings |

### 3.3 Gerar Railway Token

1. Railway Dashboard → Account Settings → Tokens
2. "Create Token" → Nome: `github-deploy`
3. Copiar token (formato: `rlw_xxxx`)
4. Adicionar como GitHub Secret: `RAILWAY_TOKEN`

---

## 4. Dockerfile e Entrypoint

### 4.1 Dockerfile (multi-stage)

```dockerfile
# Dockerfile multi-stage para Agente Júlia
FROM python:3.13-slim AS builder

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

WORKDIR /app

# Copiar arquivos de dependências e instalar
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Stage final
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar ambiente do builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copiar código
COPY app/ ./app/
COPY static/ ./static/
COPY migrations/ ./migrations/
COPY scripts/entrypoint.sh ./entrypoint.sh

RUN mkdir -p /app/logs && chmod +x /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# Entrypoint valida RUN_MODE
ENTRYPOINT ["/app/entrypoint.sh"]
```

### 4.2 Entrypoint Script

**Arquivo:** `scripts/entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "=== Julia Entrypoint ==="
echo "RUN_MODE: ${RUN_MODE:-not set}"
echo "APP_ENV: ${APP_ENV:-not set}"

# Validar RUN_MODE obrigatório
if [ -z "$RUN_MODE" ]; then
    echo "ERROR: RUN_MODE environment variable is required!"
    echo ""
    echo "Valid values:"
    echo "  - api       : Run FastAPI server (uvicorn)"
    echo "  - worker    : Run ARQ worker (fila consumer)"
    echo "  - scheduler : Run APScheduler (cron jobs)"
    exit 1
fi

# Executar baseado no RUN_MODE
case "$RUN_MODE" in
    api)
        echo "Starting API server..."
        exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
        ;;
    worker)
        echo "Starting worker..."
        exec python -m app.workers.fila_worker
        ;;
    scheduler)
        echo "Starting scheduler..."
        exec python -m app.workers.scheduler
        ;;
    *)
        echo "ERROR: Invalid RUN_MODE: $RUN_MODE"
        echo "Valid values: api, worker, scheduler"
        exit 1
        ;;
esac
```

**Benefícios:**
- Container falha imediatamente se `RUN_MODE` não estiver definido
- Evita "container fazendo tudo por acidente"
- Log claro do que está sendo executado

---

## 5. Hard Guards de Ambiente

### 5.1 O Problema

Risco de deploy apontando para banco errado:
- Variável `SUPABASE_URL` apontando para staging
- Deploy em produção usando dados de desenvolvimento
- Dados de produção corrompidos por testes

### 5.2 A Solução: Markers no Banco

**Tabela `app_settings` no Supabase PROD:**

```sql
INSERT INTO app_settings (key, value, description)
VALUES
    ('environment', 'production', 'Environment marker - CRÍTICO'),
    ('supabase_project_ref', 'jyqgbzhqavgpxqacduoi', 'Project ref - CRÍTICO')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

**Variáveis no Railway:**

```
APP_ENV=production
SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi
```

### 5.3 Validação no Health Check

O endpoint `/health/deep` compara:

| Container | Banco | Match? |
|-----------|-------|--------|
| `APP_ENV=production` | `environment='production'` | ✅ OK |
| `APP_ENV=production` | `environment='staging'` | ❌ CRITICAL |
| `SUPABASE_PROJECT_REF=jyq...` | `supabase_project_ref='jyq...'` | ✅ OK |
| `SUPABASE_PROJECT_REF=jyq...` | `supabase_project_ref='ofp...'` | ❌ CRITICAL |

Se mismatch → HTTP 503 → Pipeline falha → Deploy bloqueado.

---

## 6. Bootstrap do Supabase PROD

### 6.1 Estratégia

1. Exportar schema do DEV/staging via Supabase CLI
2. Aplicar schema no PROD (sem dados)
3. Aplicar seeds mínimos (markers, feature flags)
4. Migrar dados via psql

### 6.2 Passos Executados

**Passo 1: Exportar schema**
```bash
supabase login
supabase link --project-ref ofpnronthwcsybfxnxgj  # DEV
supabase db dump -f bootstrap/01-schema.sql
```

**Passo 2: Aplicar no PROD**
```bash
supabase link --project-ref jyqgbzhqavgpxqacduoi  # PROD
supabase db push
```

Alternativa: Colar SQL no Dashboard → SQL Editor

**Passo 3: Aplicar seeds**

**Arquivo:** `bootstrap/02-seeds.sql`

```sql
-- Hard Guards
INSERT INTO app_settings (key, value, description)
VALUES
    ('environment', 'production', 'Environment marker'),
    ('supabase_project_ref', 'jyqgbzhqavgpxqacduoi', 'Project reference')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Feature Flags
INSERT INTO feature_flags (key, value, description)
VALUES
    ('external_handoff', '{"enabled": true}'::jsonb, 'Handoff externo'),
    ('campaign_attribution', '{"enabled": true}'::jsonb, 'Atribuição'),
    ('dynamic_lock', '{"enabled": true}'::jsonb, 'Lock dinâmico'),
    ('error_classifier', '{"enabled": true}'::jsonb, 'Classificador de erros')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Julia Status (PAUSADA para validação)
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Deploy inicial - aguardando validação', 'manual');
```

### 6.3 Erro Encontrado: Estrutura de Seeds

**Problema:** Seeds originais usavam estrutura errada:

```sql
-- ERRADO: coluna 'enabled' não existe
INSERT INTO feature_flags (key, enabled, description) VALUES ...

-- ERRADO: alterado_via com valor inválido
INSERT INTO julia_status (..., alterado_via) VALUES (..., 'deploy');
```

**Correção (commit `2419220`):**

```sql
-- CORRETO: usar 'value' JSONB
INSERT INTO feature_flags (key, value, description)
VALUES ('external_handoff', '{"enabled": true}'::jsonb, ...)

-- CORRETO: usar valor válido
INSERT INTO julia_status (..., alterado_via) VALUES (..., 'manual');
-- Valores aceitos: 'slack', 'sistema', 'api', 'manual'
```

### 6.4 Resultado do Bootstrap

| Item | Quantidade |
|------|------------|
| Tabelas | 72 |
| Views | 9 |
| Functions | 204 |
| Extensions | 4 (vector, pg_trgm, unaccent, pgcrypto) |

---

## 7. Problema LID (Evolution API v2)

### 7.1 Descrição

O Evolution API v2 introduziu **Linked ID (LID)** - identificador interno do WhatsApp para dispositivos vinculados.

**Formato LID:** `211484206436558@lid`
**Formato Esperado:** `5511999999999@s.whatsapp.net`

### 7.2 Sintomas

1. Mensagens chegavam mas Julia não respondia
2. Logs mostravam telefones vazios ou inválidos
3. Erro: `cliente_id vazio após processamento`
4. Médicos não eram identificados no banco

### 7.3 Análise do Payload

```json
{
  "key": {
    "remoteJid": "211484206436558@lid",           // LID (sem telefone)
    "remoteJidAlt": "5511981677736@s.whatsapp.net", // Telefone real!
    "fromMe": false,
    "id": "3A287F9E01CFA289E153"
  },
  "message": {
    "conversation": "Oi, tenho interesse"
  }
}
```

**Descoberta:** O campo `remoteJidAlt` contém o telefone real!

### 7.4 Solução Implementada

**Arquivo:** `app/services/parser.py`

```python
def is_lid_format(jid: str) -> bool:
    """Verifica se JID está no formato LID."""
    if not jid:
        return False
    return jid.endswith("@lid")

def parsear_mensagem(data: dict) -> Optional[MensagemRecebida]:
    key = data.get("key", {})
    jid = key.get("remoteJid", "")
    jid_alt = key.get("remoteJidAlt", "")

    is_lid = is_lid_format(jid)

    # Se é LID e tem jid_alt, usa o alt para extrair telefone
    if is_lid and jid_alt:
        telefone = extrair_telefone(jid_alt)
        logger.info(f"LID detectado. Usando remoteJidAlt: {jid_alt}")
    else:
        telefone = extrair_telefone(jid)

    return MensagemRecebida(
        telefone=telefone,
        remote_jid=jid,       # Preserva JID original para respostas
        remote_jid_alt=jid_alt,
        is_lid=is_lid,
        # ...
    )
```

**Arquivo:** `app/schemas/mensagem.py`

```python
class MensagemRecebida(BaseModel):
    telefone: str
    remote_jid: Optional[str] = None
    remote_jid_alt: Optional[str] = None
    is_lid: bool = False
    # ...
```

### 7.5 Testes Adicionados

**Arquivo:** `tests/test_parser.py` - 9 novos testes:

```python
def test_lid_verdadeiro():
    assert is_lid_format("211484206436558@lid") == True

def test_lid_falso_whatsapp_normal():
    assert is_lid_format("5511999999999@s.whatsapp.net") == False

def test_mensagem_lid_com_remote_jid_alt():
    """LID com remoteJidAlt deve extrair telefone do alt."""
    data = {
        "key": {
            "remoteJid": "211484206436558@lid",
            "remoteJidAlt": "5511981677736@s.whatsapp.net",
            "fromMe": False,
            "id": "ABC123"
        },
        "message": {"conversation": "Oi"}
    }
    msg = parsear_mensagem(data)
    assert msg.telefone == "5511981677736"
    assert msg.is_lid == True
    assert msg.remote_jid == "211484206436558@lid"
```

---

## 8. Erros Corrigidos Durante Deploy

### 8.1 Redis Expire Time Error

**Erro:**
```
invalid expire time in 'setex' command
```

**Causa:** Código tentava invalidar cache com TTL=0:
```python
# ERRADO
await cache_set_json(cache_key, None, 0)
```

**Correção:** `app/services/policy/repository.py`
```python
# CORRETO
await cache_delete(cache_key)
```

### 8.2 Missing Column metricas_conversa

**Erro:**
```
Could not find the 'total_mensagens_humano' column of 'metricas_conversa'
```

**Correção:** Migration aplicada:
```sql
ALTER TABLE metricas_conversa
ADD COLUMN IF NOT EXISTS total_mensagens_humano INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS houve_handoff BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS motivo_handoff TEXT,
ADD COLUMN IF NOT EXISTS duracao_total_minutos INTEGER;
```

### 8.3 Evolution API fetchAllGroups 500

**Erro:**
```
HTTP 500 Internal Server Error on /group/fetchAllGroups
```

**Causa:** Endpoint incorreto - buscava todos os grupos ao invés de um específico.

**Correção:** `app/services/whatsapp.py`
```python
# Antes (incorreto)
url = f"{self.base_url}/group/fetchAllGroups/{self.instance}"

# Depois (correto)
url = f"{self.base_url}/group/participants/{self.instance}?groupJid={group_jid}"
```

### 8.4 Seeds com Estrutura Errada

**Erro:**
```
column "enabled" of relation "feature_flags" does not exist
```

**Correção:** Usar coluna correta (`value` JSONB):
```sql
-- Antes
INSERT INTO feature_flags (key, enabled, description) ...

-- Depois
INSERT INTO feature_flags (key, value, description)
VALUES ('key', '{"enabled": true}'::jsonb, 'description')
```

### 8.5 Certificados SSL com Espaços no Nome

**Erro (ao rodar psql):**
```
psql: error: unexpected spaces found in "/path/prod-ca-2021 banco_medicos.crt"
```

**Correção:** Renomear arquivos:
```bash
mv "prod-ca-2021 banco_medicos.crt" supabase-dev.crt
mv "prod-ca-2021 julia-prod.crt" supabase-prod.crt
```

### 8.6 Senhas com Caracteres Especiais

**Erro:**
```
FATAL: Tenant or user not found
connection on socket "@_rP6nB!y7d2_@aws-0-us-east-1..."
```

**Causa:** Caracteres especiais (@, !, ?) não estavam URL-encoded.

**Correção:** URL-encode senhas:
```bash
# @ -> %40, ! -> %21, ? -> %3F
DEV_PASSWORD_ENCODED="NerBr.LFcpfQN%3F9"        # Original: NerBr.LFcpfQN?9
PROD_PASSWORD_ENCODED="h%40%40_rP6nB%21y7d2_"   # Original: h@@_rP6nB!y7d2_
```

### 8.7 Pooler vs Conexão Direta

**Erro (usando pooler):**
```
FATAL: Tenant or user not found
```

**Correção:** Usar conexão direta ao invés de pooler:
```bash
# Pooler (problemático para pg_dump)
postgresql://postgres:xxx@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# Direto (funciona)
postgresql://postgres:xxx@db.jyqgbzhqavgpxqacduoi.supabase.co:5432/postgres
```

---

## 9. Migração de Dados DEV → PROD

### 9.1 Estratégia

| Tamanho | Método | Tabelas |
|---------|--------|---------|
| Pequenas (<100 registros) | MCP SQL direto | especialidades, periodos, setores, etc |
| Grandes (>1.000 registros) | psql/pg_dump | clientes, vagas, conhecimento_julia |

### 9.2 Tabelas Migradas via MCP

| Tabela | Registros |
|--------|-----------|
| especialidades | 57 |
| periodos | 6 |
| setores | 9 |
| formas_recebimento | 5 |
| tipos_vaga | 4 |
| hospitais | 90 |
| hospitais_alias | 5 |
| especialidades_alias | 81 |

### 9.3 Script de Migração psql

**Arquivo:** `scripts/migrate-to-prod.sh`

```bash
#!/bin/bash
# Certificados SSL
CERT_DEV="/path/supabase-dev.crt"
CERT_PROD="/path/supabase-prod.crt"

# Senhas URL-encoded
DEV_PASSWORD_ENCODED="NerBr.LFcpfQN%3F9"
PROD_PASSWORD_ENCODED="h%40%40_rP6nB%21y7d2_"

# Connection strings - CONEXÃO DIRETA
DEV_DB="postgresql://postgres:${DEV_PASSWORD_ENCODED}@db.ofpnronthwcsybfxnxgj.supabase.co:5432/postgres?sslmode=require"
PROD_DB="postgresql://postgres:${PROD_PASSWORD_ENCODED}@db.jyqgbzhqavgpxqacduoi.supabase.co:5432/postgres?sslmode=require"

# Funções
export_table() {
    pg_dump "$DEV_DB" --table="$1" --data-only --column-inserts --on-conflict-do-nothing > "$DUMP_DIR/$1.sql"
}

import_table() {
    psql "$PROD_DB" -f "$DUMP_DIR/$1.sql"
}

# Uso
case "${1:-menu}" in
    test)   test_connection "DEV" "$DEV_DB"; test_connection "PROD" "$PROD_DB" ;;
    export) export_table "clientes"; export_table "vagas"; ... ;;
    import) import_table "clientes"; import_table "vagas"; ... ;;
    migrate) $0 export && $0 import ;;
esac
```

### 9.4 Comandos Executados

```bash
# Testar conexões
./scripts/migrate-to-prod.sh test
# DEV: 29.651 clientes ✅
# PROD: 1 cliente ✅

# Migrar
./scripts/migrate-to-prod.sh migrate
```

### 9.5 Resultado da Migração

| Tabela | DEV | PROD | Diferença | Motivo |
|--------|-----|------|-----------|--------|
| clientes | 29.651 | 29.648 | -3 | ON CONFLICT DO NOTHING |
| vagas | 4.980 | 4.972 | -8 | ON CONFLICT DO NOTHING |
| conhecimento_julia | 529 | 529 | 0 | ✅ |
| hospitais | 90 | 90 | 0 | ✅ |
| especialidades | 57 | 57 | 0 | ✅ |
| diretrizes | 26 | 26 | 0 | ✅ |
| prompts | 52 | 52 | 0 | ✅ |
| julia_status | 1 | 3 | +2 | PROD já tinha registros |
| campanhas | 7 | 7 | 0 | ✅ |

---

## 10. Validação e Health Checks

### 10.1 Endpoints de Health

| Endpoint | Uso | Retorno |
|----------|-----|---------|
| `/health` | Liveness | Sempre 200 se app rodando |
| `/health/ready` | Readiness | 200 se Redis conectado |
| `/health/deep` | CI/CD | 200 se TUDO ok, 503 se algo falhar |
| `/health/schema` | Debug | Info de migrations |
| `/health/rate-limit` | Monitoramento | Estatísticas de rate limit |

### 10.2 Deep Health Check

O `/health/deep` verifica:

1. **Redis** - Ping
2. **Supabase** - Conexão
3. **Environment guard** - APP_ENV == banco
4. **Project ref guard** - SUPABASE_PROJECT_REF == banco
5. **Tabelas críticas** - clientes, conversations, fila_mensagens, etc
6. **Views críticas** - campaign_sends, campaign_metrics
7. **Schema version** - Última migration aplicada

**Exemplo de resposta:**
```json
{
  "status": "healthy",
  "checks": {
    "environment": {"status": "ok", "value": "production"},
    "project_ref": {"status": "ok"},
    "redis": {"status": "ok", "latency_ms": 1.2},
    "supabase": {"status": "ok"},
    "tables": {"status": "ok", "missing": []},
    "views": {"status": "ok", "missing": []},
    "schema_version": {"status": "ok", "version": "20251230120000"}
  },
  "deploy_safe": true
}
```

### 10.3 Smoke Test Checklist

```
✅ /health/deep retorna 200 com todos checks ok
✅ /jobs/reconcile-touches executa sem erro
✅ Rate limit stats retorna (Redis ok)
✅ Logs no Railway sem erros críticos
```

### 10.4 Avisos do Supabase Linter

| Tipo | Quantidade | Severidade |
|------|------------|------------|
| RLS Enabled No Policy | 32 tabelas | INFO |
| Security Definer View | 10 views | ERROR |
| Function Search Path Mutable | 6 funções | WARN |
| RLS Disabled in Public | 3 tabelas | ERROR |
| Extension in Public | 3 extensões | WARN |

**Recomendação:** Tratar em sprint futura de segurança.

---

## 11. Runbook e Operações

### 11.1 Regras Críticas

```
╔═══════════════════════════════════════════════════════════════════════╗
║  1. NUNCA MERGEAR CÓDIGO QUE DEPENDE DE MIGRATION NÃO APLICADA       ║
║  2. QUALQUER DEPLOY QUE FALHAR EM /health/deep = ROLLBACK IMEDIATO   ║
║  3. SE /health/deep RETORNAR "CRITICAL" = AMBIENTE ERRADO            ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### 11.2 Fluxo de Migrations

**ORDEM CORRETA: MIGRATION PRIMEIRO, CÓDIGO DEPOIS**

```
1. Criar migration localmente
2. Validar SQL (staging)
3. APLICAR MIGRATION NO PROD (manual) ← ANTES do merge!
4. Verificar /health/schema no PROD
5. Só então: commit/PR do código
6. Merge → deploy → /health/deep passa
```

### 11.3 Deploy Manual (emergência)

```bash
# Via Railway CLI
railway login
railway up

# Via GitHub Actions
gh workflow run ci.yml --ref main
```

### 11.4 Rollback

1. Railway Dashboard → Deployments
2. Encontrar último deploy estável
3. Clicar "Redeploy"

### 11.5 Pausar Julia (emergência)

```sql
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergência - pausado manualmente', 'manual');
```

### 11.6 Retomar Julia

```sql
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operação', 'manual');
```

---

## 12. Commits Relacionados

| Hash | Descrição |
|------|-----------|
| `d503207` | fix: corrige erros secundários do deploy |
| `af6fd84` | fix(lid): extrai telefone de remoteJidAlt quando remoteJid é LID |
| `eecce14` | Revert "fix(pipeline): adiciona fallback para resolver LID via banco" |
| `944a150` | fix(pipeline): adiciona fallback para resolver LID via banco |
| `2419220` | fix(bootstrap): corrige estrutura de seeds para PROD |
| `c97bcf6` | chore(bootstrap): exporta schema do banco_medicos |
| `860e20e` | docs(deploy): bootstrap completo + smoke test checklist |
| `21238e8` | docs(deploy): guia de bootstrap para Supabase PROD |
| `6f32600` | feat(deploy): hard guards de ambiente + RUN_MODE obrigatório |
| `bf3819b` | feat(deploy): health check robusto + CI assertivo + runbook |
| `70dd1da` | ci(railway): configura deploy automático no Railway |

---

## 13. Lições Aprendidas

### 13.1 Evolution API v2

- O formato LID é mudança significativa que afeta identificação de usuários
- Sempre verificar campos alternativos (`remoteJidAlt`) no payload
- Manter o `remoteJid` original para operações de resposta

### 13.2 Migração de Dados

- Para volumes grandes (>10k registros), usar `pg_dump`/`psql`
- URL encoding de senhas é crítico para conexões diretas
- Conexão direta (`db.*.supabase.co:5432`) é mais confiável que pooler

### 13.3 Railway

- Separar serviços (api, worker, scheduler) com `RUN_MODE`
- Scheduler SEMPRE deve ter 1 instância fixa
- Health checks profundos no CI/CD previnem deploys ruins

### 13.4 Ambientes Múltiplos

- Hard guards (markers no banco) previnem deploy no ambiente errado
- Configurar MCP separados para DEV e PROD
- Sempre verificar qual ambiente antes de operações

### 13.5 Supabase

- Certificados SSL não podem ter espaços no nome
- Estrutura de tabelas pode diferir (sempre verificar antes de seeds)
- Linter de segurança deve ser executado após migrations

---

## Anexos

### A. Connection Strings (sem senhas)

```
DEV:  postgresql://postgres:***@db.ofpnronthwcsybfxnxgj.supabase.co:5432/postgres
PROD: postgresql://postgres:***@db.jyqgbzhqavgpxqacduoi.supabase.co:5432/postgres
```

### B. URLs de Referência

- Supabase DEV: https://supabase.com/dashboard/project/ofpnronthwcsybfxnxgj
- Supabase PROD: https://supabase.com/dashboard/project/jyqgbzhqavgpxqacduoi
- Railway Dashboard: https://railway.app/dashboard
- Database Linter Docs: https://supabase.com/docs/guides/database/database-linter
- Evolution API Docs: https://doc.evolution-api.com

### C. Arquivos Criados/Modificados

| Arquivo | Tipo | Descrição |
|---------|------|-----------|
| `scripts/migrate-to-prod.sh` | Criado | Script migração psql |
| `scripts/entrypoint.sh` | Criado | Entrypoint Docker com RUN_MODE |
| `data/supabase-dev.crt` | Criado | Certificado SSL DEV |
| `data/supabase-prod.crt` | Criado | Certificado SSL PROD |
| `bootstrap/01-schema.sql` | Criado | Schema exportado |
| `bootstrap/02-seeds.sql` | Criado | Seeds para PROD |
| `bootstrap/README.md` | Criado | Guia de bootstrap |
| `bootstrap/SMOKE-TEST.md` | Criado | Checklist de smoke test |
| `.github/workflows/ci.yml` | Modificado | CI/CD com Railway |
| `railway.json` | Criado | Config Railway |
| `Dockerfile` | Modificado | Multi-stage + entrypoint |
| `docs/runbook.md` | Criado | Runbook operacional |
| `docs/deploy.md` | Atualizado | Documentação Railway |
| `app/services/parser.py` | Modificado | Suporte LID |
| `app/schemas/mensagem.py` | Modificado | Campos LID |
| `app/services/policy/repository.py` | Modificado | Fix cache_delete |
| `app/services/whatsapp.py` | Modificado | Fix endpoint grupos |
| `tests/test_parser.py` | Modificado | 9 testes LID |

---

*Relatório gerado pelo Claude Code em 30/12/2025*
