# Deploy e Operacao

> Como fazer deploy e operar o sistema em producao

---

## Arquitetura de Deploy

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     LOAD BALANCER                            │
│                   (Nginx / Traefik)                          │
└─────────────────────────────┬───────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│    API Julia    │ │    API Julia    │ │    API Julia    │
│   (Container)   │ │   (Container)   │ │   (Container)   │
│    Port 8000    │ │    Port 8000    │ │    Port 8000    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Supabase      │ │     Redis       │ │   Evolution     │
│  (Managed)      │ │  (Container)    │ │  (Container)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Componentes para Deploy

| Componente | Tipo | Replicas |
|------------|------|----------|
| API Julia | Container | 1-3 |
| Scheduler | Container | 1 |
| Fila Worker | Container | 1-2 |
| Evolution API | Container | 1 |
| Redis | Container | 1 |
| Chatwoot | Container | 1 |
| Supabase | Managed | - |

---

## Docker Compose Producao

```yaml
# docker-compose.prod.yml

version: '3.8'

services:
  julia-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.production
    restart: always
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 1G

  julia-scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m app.workers scheduler
    env_file:
      - .env.production
    restart: always
    depends_on:
      - julia-api

  julia-fila:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m app.workers fila
    env_file:
      - .env.production
    restart: always
    depends_on:
      - julia-api

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: always
    command: redis-server --appendonly yes

  evolution-api:
    image: atendai/evolution-api:latest
    ports:
      - "8080:8080"
    volumes:
      - evolution-data:/evolution/instances
    env_file:
      - .env.evolution
    restart: always

volumes:
  redis-data:
  evolution-data:
```

---

## Dockerfile

```dockerfile
# Dockerfile

FROM python:3.13-slim

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copiar arquivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalar dependencias
RUN uv sync --frozen --no-dev

# Copiar codigo
COPY app/ ./app/

# Expor porta
EXPOSE 8000

# Comando padrao
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Variaveis de Producao

```bash
# .env.production

# App
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Evolution (usar URL interno do Docker)
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=julia-prod

# Redis (usar URL interno do Docker)
REDIS_URL=redis://redis:6379/0

# Rate Limits (mais restritivos em prod)
MAX_MSGS_POR_HORA=15
MAX_MSGS_POR_DIA=80

# Julia API (para scheduler)
JULIA_API_URL=http://julia-api:8000
```

---

## Deploy Commands

### Build e Push

```bash
# Build image
docker build -t julia-api:latest .

# Tag para registry
docker tag julia-api:latest registry.example.com/julia-api:latest

# Push
docker push registry.example.com/julia-api:latest
```

### Deploy

```bash
# Subir em producao
docker compose -f docker-compose.prod.yml up -d

# Ver logs
docker compose -f docker-compose.prod.yml logs -f julia-api

# Scale (se necessario)
docker compose -f docker-compose.prod.yml up -d --scale julia-api=3
```

### Rolling Update

```bash
# Atualizar sem downtime
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --no-deps julia-api
```

---

## Monitoramento

### Health Checks

Configurar no load balancer:

```nginx
# nginx.conf
upstream julia {
    server julia-api-1:8000;
    server julia-api-2:8000;
}

server {
    location /health {
        proxy_pass http://julia/health;
    }
}
```

### Prometheus Metrics (Futuro)

```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram

mensagens_recebidas = Counter(
    'julia_mensagens_recebidas_total',
    'Total de mensagens recebidas'
)

tempo_resposta = Histogram(
    'julia_tempo_resposta_segundos',
    'Tempo de resposta do LLM'
)
```

### Alertas

Configurar alertas para:

| Metrica | Threshold | Acao |
|---------|-----------|------|
| Error rate | > 5% | Notificar Slack |
| Latencia | > 5s | Notificar Slack |
| Circuit open | any | Notificar Slack urgente |
| Rate limit | > 90% | Notificar Slack |
| Deteccao bot | > 5% | Notificar Slack |

---

## Backup e Recovery

### Supabase

Supabase faz backup automatico. Para restaurar:

```bash
# Download backup via dashboard
# Ou usar pg_dump/pg_restore
```

### Redis

```bash
# Backup manual
docker exec redis redis-cli BGSAVE

# Copiar arquivo RDB
docker cp redis:/data/dump.rdb ./backups/
```

### Evolution (Sessoes WhatsApp)

```bash
# Backup das sessoes
docker cp evolution-api:/evolution/instances ./backups/evolution/

# Restaurar
docker cp ./backups/evolution/ evolution-api:/evolution/instances
```

---

## Logs

### Estrutura de Logs

```json
{
    "timestamp": "2025-12-07T10:30:00Z",
    "level": "INFO",
    "service": "julia-api",
    "message": "Mensagem processada",
    "context": {
        "medico_id": "uuid",
        "conversa_id": "uuid",
        "latencia_ms": 1234
    }
}
```

### Agregacao de Logs

Recomendado usar:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **Datadog**

---

## Seguranca em Producao

### Checklist

- [ ] HTTPS obrigatorio
- [ ] Secrets em vault (nao .env)
- [ ] RLS ativo no Supabase
- [ ] API keys rotacionadas
- [ ] Rate limiting no load balancer
- [ ] Logs sem dados sensiveis
- [ ] Backup automatico

### Rotacao de Secrets

```bash
# Rotacionar API key Anthropic
1. Gerar nova key no console
2. Atualizar .env.production
3. Restart containers
4. Revogar key antiga

# Mesma logica para outras keys
```

---

## Troubleshooting Producao

### Container reiniciando

```bash
# Ver logs
docker logs julia-api --tail 100

# Ver eventos
docker events --filter container=julia-api

# Comum: OOM (Out of Memory)
# Solucao: aumentar limite de memoria
```

### Conexao recusada

```bash
# Verificar rede Docker
docker network inspect julia-network

# Testar conectividade
docker exec julia-api ping redis
```

### Rate limit atingido

```bash
# Verificar uso atual
curl http://localhost:8000/health/rate

# Se necessario, resetar contadores
docker exec redis redis-cli DEL "rate:global:hour"
docker exec redis redis-cli DEL "rate:global:day"
```

### Circuit breaker aberto

```bash
# Verificar status
curl http://localhost:8000/health/circuit

# Aguardar recovery_timeout ou
# Restart para resetar estado
docker restart julia-api
```

---

## Runbook

### Pausar Julia (Emergencia)

```bash
# 1. Atualizar status no banco
# Via Supabase dashboard ou SQL:
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergencia - pausado manualmente', 'manual');

# 2. O webhook verifica este status e para de processar
```

### Retomar Julia

```bash
# 1. Atualizar status
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operacao', 'manual');
```

### Handoff Manual de Conversa

```sql
-- Marcar conversa para humano assumir
UPDATE conversations
SET controlled_by = 'human',
    escalation_reason = 'Handoff manual'
WHERE id = 'uuid-da-conversa';
```

---

## SLA e Disponibilidade

### Metas

| Metrica | Meta |
|---------|------|
| Uptime | 99.5% |
| Tempo resposta | < 5s |
| Taxa erro | < 1% |

### Calculo de Uptime

```
Uptime = (Tempo total - Tempo down) / Tempo total * 100

Ex: Mes de 30 dias
- 99.5% = max 3.6h de downtime
- 99.9% = max 43min de downtime
```

---

## Deploy Railway (Recomendado)

Railway oferece deploy simplificado com CI/CD integrado.

### Setup Inicial

1. **Criar Projeto**
   - https://railway.app → "New Project" → "Deploy from GitHub repo"
   - Selecionar repositório
   - Railway detecta Dockerfile automaticamente

2. **Adicionar Redis**
   - "New" → "Database" → "Redis"
   - Railway injeta `REDIS_URL` automaticamente

3. **Configurar Variáveis**

```bash
# No painel Variables do Railway:

# App
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Segurança
JWT_SECRET_KEY=<openssl rand -hex 32>
CORS_ORIGINS=https://app.revoluna.com

# Supabase (projeto de produção)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbG...

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

### Gerar Token de Deploy

1. Railway → Account Settings → Tokens
2. "Create Token" → Nome: `github-deploy`
3. Copiar token (formato: `rlw_xxxx`)
4. Adicionar como GitHub Secret: `RAILWAY_TOKEN`

### CI/CD Automático

O workflow `.github/workflows/ci.yml` faz deploy automático na main.

Para deploy manual:

```bash
# Via Railway CLI
npm install -g @railway/cli
railway login
railway up

# Via GitHub Actions
gh workflow run ci.yml --ref main
```

### Verificação

```bash
# Health check
curl https://seu-app.railway.app/health

# Resposta esperada
{"status": "healthy", "version": "1.0.0", "environment": "production"}
```

### Rollback

1. Railway → Deployments
2. Encontrar deploy estável anterior
3. Clicar "Redeploy"

---

## Supabase Produção

### Criar Projeto Separado

1. https://supabase.com/dashboard → "New Project"
2. Nome: `julia-prod`
3. Região: `South America (São Paulo)`
4. Salvar password

### Aplicar Schema

**Opção A: Supabase CLI**

```bash
# Instalar
brew install supabase/tap/supabase

# Login e link staging
supabase login
supabase link --project-ref SEU_REF_STAGING

# Exportar schema
supabase db dump -f schema.sql

# Link prod e aplicar
supabase link --project-ref SEU_REF_PROD
supabase db push
```

**Opção B: Dashboard**

1. Staging: Database → Backups → Download
2. Prod: SQL Editor → Colar e executar

### Habilitar Extensões

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

---

## GitHub Secrets

Repository → Settings → Secrets and variables → Actions

| Secret | Descrição |
|--------|-----------|
| `SUPABASE_URL` | URL projeto staging (testes CI) |
| `SUPABASE_SERVICE_KEY` | Service key staging |
| `ANTHROPIC_API_KEY` | API key Anthropic |
| `RAILWAY_TOKEN` | Token de deploy Railway |

---

## Checklist Deploy

- [ ] Supabase prod criado com schema aplicado
- [ ] Extensões habilitadas (vector, pg_trgm, unaccent)
- [ ] Railway projeto configurado
- [ ] Redis adicionado no Railway
- [ ] Todas variáveis de ambiente no Railway
- [ ] GitHub Secrets configurados
- [ ] CI/CD workflow testado
- [ ] Health check respondendo
- [ ] Evolution API apontando para URL Railway
- [ ] Webhook Evolution configurado
- [ ] Slack notificações funcionando
