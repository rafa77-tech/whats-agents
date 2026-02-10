# Deploy e Operacao

> Como fazer deploy e operar o sistema em producao

---

## Arquitetura de Deploy

O Agente Julia e composto por 3 servicos independentes rodando no Railway:

```
┌─────────────────────────────────────────────────────────────┐
│                     RAILWAY PROJECT                          │
│              remarkable-communication                        │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  whats-agents │    │ whats-agents  │    │ whats-agents  │
│               │    │               │    │               │
│ RUN_MODE=api  │    │ RUN_MODE=     │    │ RUN_MODE=     │
│               │    │ worker        │    │ scheduler     │
│               │    │               │    │               │
│ Uvicorn       │    │ ARQ worker    │    │ APScheduler   │
│ Port 8000     │    │ (fila)        │    │ (jobs)        │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Supabase   │    │    Redis    │    │  Evolution  │
│  (Managed)  │    │ (Railway)   │    │    API      │
│             │    │             │    │  (External) │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Componentes

| Servico | Imagem | RUN_MODE | Descricao |
|---------|--------|----------|-----------|
| whats-agents (api) | Dockerfile | `api` | FastAPI server (webhook, endpoints) |
| whats-agents (worker) | Dockerfile | `worker` | ARQ worker (fila de mensagens) |
| whats-agents (scheduler) | Dockerfile | `scheduler` | APScheduler (jobs agendados) |
| Redis | Railway Plugin | - | Cache e filas |
| Supabase | External | - | PostgreSQL + pgvector |
| Evolution API | External | - | WhatsApp gateway |

---

## Railway: 3 Servicos, 1 Dockerfile

Todos os 3 servicos usam o **mesmo Dockerfile** e a **mesma imagem Docker**.

O que diferencia cada servico e a variavel de ambiente `RUN_MODE`:

| Servico | RUN_MODE | Comando Executado |
|---------|----------|-------------------|
| API | `api` | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Worker | `worker` | `python -m app.workers.fila_worker` |
| Scheduler | `scheduler` | `python -m app.workers.scheduler` |

### Como Funciona

O `entrypoint.sh` le a variavel `RUN_MODE` e executa o comando apropriado:

```bash
# scripts/entrypoint.sh

case "$RUN_MODE" in
    api)
        exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
        ;;
    worker)
        exec python -m app.workers.fila_worker
        ;;
    scheduler)
        exec python -m app.workers.scheduler
        ;;
    *)
        echo "ERROR: Invalid RUN_MODE: $RUN_MODE"
        exit 1
        ;;
esac
```

---

## Setup Railway

### 1. Criar Projeto

1. Acesse https://railway.app
2. New Project → Deploy from GitHub repo
3. Selecione o repositorio `whatsapp-api`
4. Railway detecta o Dockerfile automaticamente

### 2. Adicionar Redis

1. New → Database → Redis
2. Railway injeta `REDIS_URL` automaticamente nos servicos

### 3. Criar 3 Servicos

Railway permite criar multiplos servicos a partir do mesmo repositorio.

**Servico 1: API**

1. Settings → Service Name: `whats-agents-api`
2. Variables → Add Variable:
   - `RUN_MODE=api`
   - `APP_ENV=production`
   - (mais variaveis abaixo)
3. Settings → Networking → Public Domain: Habilitar

**Servico 2: Worker**

1. New → GitHub Repo (mesmo repo)
2. Settings → Service Name: `whats-agents-worker`
3. Variables → Add Variable:
   - `RUN_MODE=worker`
   - `APP_ENV=production`
   - (copiar todas as outras variaveis do servico API)

**Servico 3: Scheduler**

1. New → GitHub Repo (mesmo repo)
2. Settings → Service Name: `whats-agents-scheduler`
3. Variables → Add Variable:
   - `RUN_MODE=scheduler`
   - `APP_ENV=production`
   - (copiar todas as outras variaveis do servico API)

---

## Variaveis de Ambiente (Producao)

Configurar as mesmas variaveis nos 3 servicos (exceto `RUN_MODE`):

### App

```bash
APP_NAME=Agente Julia
ENVIRONMENT=production
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
TZ=America/Sao_Paulo
```

### Seguranca

```bash
JWT_SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://dashboard.revoluna.app
```

### Supabase (Producao)

```bash
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...
SUPABASE_PROJECT_REF=xxxxx
```

### Anthropic

```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514
```

### Voyage AI

```bash
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3.5-lite
```

### Evolution API

```bash
EVOLUTION_API_URL=https://evolution.seudominio.com
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=Revoluna
MULTI_CHIP_ENABLED=true
```

### Chatwoot

```bash
CHATWOOT_URL=https://chatwoot.seudominio.com
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

### Slack

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_CHANNEL=#julia-gestao
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx
```

### Google

```bash
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-sa.json
GOOGLE_BRIEFINGS_FOLDER_ID=xxx
GOOGLE_TEMPLATES_FOLDER_ID=xxx
```

### Rate Limiting

```bash
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00
PILOT_MODE=false
```

### Empresa

```bash
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
```

### Redis

Railway injeta automaticamente:
```bash
REDIS_URL=redis://:password@redis.railway.internal:6379
```

---

## CI/CD Automatico

O workflow `.github/workflows/ci.yml` faz deploy automatico na main.

### Funcionamento

1. Push para `main` → Trigger workflow
2. Lint & Type Check
3. Run Tests
4. Build Docker Image
5. Deploy to Railway (3 servicos)
6. Health Check
7. Notificacao Slack

### Secrets do GitHub

Repository → Settings → Secrets and variables → Actions

| Secret | Descricao |
|--------|-----------|
| `RAILWAY_TOKEN` | Token de deploy Railway |
| `RAILWAY_PROJECT_ID` | ID do projeto Railway |
| `RAILWAY_APP_URL` | URL da API (para health check) |
| `SUPABASE_URL` | URL Supabase (para testes CI) |
| `SUPABASE_SERVICE_KEY` | Service key Supabase |
| `ANTHROPIC_API_KEY` | API key Anthropic |

### Deploy Manual

```bash
# Via Railway CLI
npm install -g @railway/cli
railway login
railway link

# Deploy API
railway up --detach --service whats-agents-api

# Deploy Worker
railway up --detach --service whats-agents-worker

# Deploy Scheduler
railway up --detach --service whats-agents-scheduler
```

---

## Health Checks

### API

```bash
# Basic health
curl https://seu-app.railway.app/health

# Deep health (verifica Redis, Supabase)
curl https://seu-app.railway.app/health/deep
```

Resposta esperada:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "git_sha": "abc123",
  "build_time": "2026-02-10T10:30:00Z",
  "checks": {
    "redis": "ok",
    "supabase": "ok"
  }
}
```

### Worker

O worker nao expoe porta. Verificar logs:

```bash
railway logs --service whats-agents-worker
```

Procurar por:
- `Worker started`
- `Processing message...`

### Scheduler

O scheduler nao expoe porta. Verificar logs:

```bash
railway logs --service whats-agents-scheduler
```

Procurar por:
- `Scheduler started`
- `Job executed: sync_briefings`

---

## Monitoramento

### Logs

```bash
# API
railway logs --service whats-agents-api

# Worker
railway logs --service whats-agents-worker

# Scheduler
railway logs --service whats-agents-scheduler

# Todos os servicos
railway logs

# Follow (streaming)
railway logs -f
```

### Metricas (Railway Dashboard)

1. Project → Metrics
2. Verificar para cada servico:
   - CPU Usage
   - Memory Usage
   - Restart Count

### Alertas

Configurar via Slack webhook (variaveis acima):

| Metrica | Threshold | Acao |
|---------|-----------|------|
| Error rate | > 5% | Notifica Slack |
| Circuit open | any | Notifica Slack urgente |
| Health check fail | 3x | Notifica Slack |

---

## Rollback

### Via Railway Dashboard

1. Railway → Deployments
2. Selecionar deploy anterior estaval
3. Click "Redeploy"

### Via CLI

```bash
# Listar deploys
railway deployments list --service whats-agents-api

# Rollback para deploy anterior
railway rollback <deployment-id> --service whats-agents-api --yes
```

### Rollback Automatico

O workflow CI/CD faz rollback automatico se health check falhar apos deploy.

---

## Troubleshooting

### Container reiniciando

```bash
# Ver logs
railway logs --service whats-agents-api --tail 100

# Comum: RUN_MODE nao definido
# Solucao: Verificar variavel RUN_MODE nas Settings
```

### Erro: "RUN_MODE environment variable is required!"

```bash
# Causa: Variavel RUN_MODE nao configurada
# Solucao: Railway → Service → Variables → Add Variable
RUN_MODE=api  # ou worker, ou scheduler
```

### Worker nao processa mensagens

```bash
# Verificar logs do worker
railway logs --service whats-agents-worker -f

# Verificar Redis
railway variables --service whats-agents-worker | grep REDIS_URL

# Testar conexao Redis (via API health check)
curl https://seu-app.railway.app/health/deep
```

### Scheduler nao executa jobs

```bash
# Verificar logs
railway logs --service whats-agents-scheduler -f

# Procurar por:
# - "Scheduler started"
# - "Job executed: <job_name>"
# - "Job failed: <error>"

# Se nao aparecer jobs, verificar timezone
railway variables --service whats-agents-scheduler | grep TZ
```

---

## Runbook

### Pausar Julia (Emergencia)

```bash
# Via Slack
# @julia pausar julia motivo: emergencia

# Ou via SQL (Supabase)
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergencia - pausado manualmente', 'manual');
```

### Retomar Julia

```bash
# Via Slack
# @julia retomar julia

# Ou via SQL
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operacao', 'manual');
```

### Restart Servico

```bash
# Via CLI
railway restart --service whats-agents-api

# Via Dashboard
# Railway → Service → Settings → Restart
```

### Escalar Replicas

Railway Pro permite replicas horizontais:

```bash
# Via Dashboard
# Railway → Service → Settings → Replicas → 2
```

**Importante:** Apenas o servico API deve ter replicas. Worker e Scheduler devem ter 1 replica cada.

---

## Checklist Deploy

- [ ] Supabase producao criado com schema aplicado
- [ ] Extensoes habilitadas (vector, pg_trgm, unaccent)
- [ ] Railway projeto configurado
- [ ] Redis adicionado no Railway
- [ ] 3 servicos criados (api, worker, scheduler)
- [ ] Variavel RUN_MODE configurada em cada servico
- [ ] Todas variaveis de ambiente nos 3 servicos
- [ ] GitHub Secrets configurados
- [ ] CI/CD workflow testado
- [ ] Health check respondendo (API)
- [ ] Worker processando mensagens
- [ ] Scheduler executando jobs
- [ ] Evolution API apontando para URL Railway
- [ ] Webhook Evolution configurado
- [ ] Slack notificacoes funcionando

---

## Documentacao Relacionada

- **Railway CLI:** `docs/integracoes/railway-quickref.md`
- **Railway Deploy:** `docs/integracoes/railway-deploy.md`
- **Configuracao:** `docs/setup/configuracao.md`
- **CI/CD Backend:** `.github/workflows/ci.yml`
