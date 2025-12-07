# Epic 4: Deploy e Infraestrutura

## Objetivo

> **Containerizar aplicação e criar estratégia de deploy para produção.**

**Resultado esperado:** Sistema completo rodando em Docker com CI/CD básico.

---

## Análise da Arquitetura

### Componentes da Aplicação

1. **API FastAPI** (`app/main.py`)
   - Servidor principal na porta 8000
   - Rotas: webhook, admin, métricas, campanhas, jobs
   - Arquivos estáticos: `/static`

2. **Workers em Background**
   - `app/workers/fila_worker.py` - Processa fila de mensagens continuamente
   - Precisa rodar como processo separado

3. **Jobs Agendados** (`app/api/routes/jobs.py`)
   - Processar mensagens agendadas (cron: a cada minuto)
   - Avaliar conversas pendentes (cron: diário às 2h)
   - Verificar alertas (cron: a cada 15min)
   - Relatório diário (cron: às 8h)
   - Atualizar prompt com feedback (cron: semanal)
   - Processar campanhas agendadas (cron: a cada minuto)
   - Follow-up diário (cron: às 10h)

4. **Dependências Externas (SaaS)**
   - Supabase (banco de dados)
   - Anthropic Claude (LLM)
   - Slack (notificações)

5. **Serviços Containerizados (já no docker-compose)**
   - Redis (cache)
   - Evolution API (WhatsApp)
   - Chatwoot (atendimento)
   - PostgreSQL (não usado - usa Supabase)

---

## Estratégia de Deploy

### Opção Recomendada: Docker Compose Completo

**Vantagens:**
- ✅ Tudo containerizado e isolado
- ✅ Fácil de gerenciar e escalar
- ✅ Consistente entre ambientes
- ✅ Fácil rollback
- ✅ Logs centralizados

**Estrutura:**
```
docker-compose.yml
├── julia-api (FastAPI)
├── julia-worker (fila_worker)
├── julia-scheduler (cron jobs)
├── redis
├── evolution-api
└── chatwoot (rails + sidekiq)
```

---

## Stories

---

# S5.E4.1 - Dockerfile da Aplicação

## Objetivo

> **Criar Dockerfile otimizado para a aplicação FastAPI.**

**Resultado esperado:** Imagem Docker funcional e otimizada.

## Tarefas

### 1. Criar Dockerfile multi-stage

```dockerfile
# Dockerfile
FROM python:3.13-slim as builder

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copiar arquivos de dependências
COPY pyproject.toml uv.lock ./

# Instalar dependências
RUN uv sync --frozen --no-dev

# Stage final
FROM python:3.13-slim

WORKDIR /app

# Copiar uv e ambiente virtual do builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

# Copiar código da aplicação
COPY app/ ./app/
COPY static/ ./static/
COPY migrations/ ./migrations/

# Variáveis de ambiente
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"

# Comando padrão (pode ser sobrescrito)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Criar .dockerignore

```dockerignore
# .dockerignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.env
.venv
venv/
ENV/
env/
.git/
.gitignore
.dockerignore
*.md
tests/
.pytest_cache/
.coverage
htmlcov/
*.log
.DS_Store
```

### 3. Otimizar build

- Usar cache de layers
- Multi-stage build para reduzir tamanho
- Instalar apenas dependências de produção

## DoD

- [x] Dockerfile criado e funcional
- [x] Build otimizado (< 500MB)
- [x] Health check implementado
- [x] .dockerignore configurado
- [x] Imagem testada localmente

---

# S5.E4.2 - Docker Compose para Produção

## Objetivo

> **Criar docker-compose.yml completo com todos os serviços.**

**Resultado esperado:** Stack completa rodando com um comando.

## Tarefas

### 1. Adicionar serviços da aplicação

```yaml
# docker-compose.yml (adicionar)

  julia-api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: julia-api
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
      - EVOLUTION_API_URL=http://evolution-api:8080
      - CHATWOOT_URL=http://chatwoot:3000
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - evolution-net
    volumes:
      - ./static:/app/static:ro
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  julia-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: julia-worker
    restart: unless-stopped
    command: ["python", "-m", "app.workers.fila_worker"]
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
      julia-api:
        condition: service_healthy
    networks:
      - evolution-net
    volumes:
      - ./logs:/app/logs

  julia-scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: julia-scheduler
    restart: unless-stopped
    command: ["python", "-m", "app.workers.scheduler"]
    env_file:
      - .env
    environment:
      - ENVIRONMENT=production
      - JULIA_API_URL=http://julia-api:8000
    depends_on:
      julia-api:
        condition: service_healthy
    networks:
      - evolution-net
    volumes:
      - ./logs:/app/logs
```

### 2. Atualizar Redis com health check

```yaml
  redis:
    image: redis:7-alpine
    networks:
      - evolution-net
    container_name: redis
    command: >
      redis-server --port 6379 --appendonly yes
    volumes:
      - evolution_redis:/data
    ports:
      - 6379:6379
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### 3. Criar worker de scheduler

```python
# app/workers/scheduler.py
"""
Scheduler para executar jobs agendados.
"""
import asyncio
import httpx
import logging
from datetime import datetime
from app.core.config import settings

logger = logging.getLogger(__name__)

JULIA_API_URL = settings.get("JULIA_API_URL", "http://localhost:8000")

JOBS = [
    {
        "name": "processar_mensagens_agendadas",
        "endpoint": "/jobs/processar-mensagens-agendadas",
        "schedule": "* * * * *",  # A cada minuto
    },
    {
        "name": "processar_campanhas_agendadas",
        "endpoint": "/jobs/processar-campanhas-agendadas",
        "schedule": "* * * * *",  # A cada minuto
    },
    {
        "name": "verificar_alertas",
        "endpoint": "/jobs/verificar-alertas",
        "schedule": "*/15 * * * *",  # A cada 15 minutos
    },
    {
        "name": "followup_diario",
        "endpoint": "/jobs/followup-diario",
        "schedule": "0 10 * * *",  # Diário às 10h
    },
    {
        "name": "avaliar_conversas_pendentes",
        "endpoint": "/jobs/avaliar-conversas-pendentes",
        "schedule": "0 2 * * *",  # Diário às 2h
    },
    {
        "name": "relatorio_diario",
        "endpoint": "/jobs/relatorio-diario",
        "schedule": "0 8 * * *",  # Diário às 8h
    },
    {
        "name": "atualizar_prompt_feedback",
        "endpoint": "/jobs/atualizar-prompt-feedback",
        "schedule": "0 2 * * 0",  # Semanal (domingo às 2h)
    },
]


def parse_cron(schedule: str) -> dict:
    """Parse cron expression simples."""
    parts = schedule.split()
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "weekday": parts[4],
    }


def should_run(schedule: str, now: datetime) -> bool:
    """Verifica se job deve executar agora."""
    cron = parse_cron(schedule)
    
    # Verificar minuto
    if cron["minute"] != "*" and str(now.minute) != cron["minute"]:
        return False
    
    # Verificar hora
    if cron["hour"] != "*" and str(now.hour) != cron["hour"]:
        return False
    
    # Verificar dia do mês
    if cron["day"] != "*" and str(now.day) != cron["day"]:
        return False
    
    # Verificar mês
    if cron["month"] != "*" and str(now.month) != cron["month"]:
        return False
    
    # Verificar dia da semana (0=domingo, 6=sábado)
    if cron["weekday"] != "*":
        weekday_map = {"0": 6, "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5}
        if str(now.weekday()) != weekday_map.get(cron["weekday"], cron["weekday"]):
            return False
    
    return True


async def execute_job(job: dict):
    """Executa um job."""
    try:
        url = f"{JULIA_API_URL}{job['endpoint']}"
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url)
            if response.status_code == 200:
                logger.info(f"✅ Job {job['name']} executado com sucesso")
            else:
                logger.error(f"❌ Job {job['name']} falhou: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Erro ao executar job {job['name']}: {e}")


async def scheduler_loop():
    """Loop principal do scheduler."""
    logger.info("🕐 Scheduler iniciado")
    
    last_minute = -1
    
    while True:
        now = datetime.now()
        
        # Executar jobs apenas no início de cada minuto
        if now.minute != last_minute:
            last_minute = now.minute
            
            for job in JOBS:
                if should_run(job["schedule"], now):
                    logger.info(f"⏰ Executando job: {job['name']}")
                    await execute_job(job)
        
        # Aguardar até próximo minuto
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(scheduler_loop())
```

## DoD

- [x] Serviços adicionados ao docker-compose
- [x] Health checks configurados
- [x] Dependências entre serviços definidas
- [x] Scheduler implementado
- [x] Volumes para logs configurados
- [x] Testado localmente

---

# S5.E4.3 - Variáveis de Ambiente e Secrets

## Objetivo

> **Gerenciar variáveis de ambiente de forma segura.**

**Resultado esperado:** Configuração segura e fácil de gerenciar.

## Tarefas

### 1. Criar .env.example

```bash
# .env.example

# App
APP_NAME=Agente Júlia
ENVIRONMENT=production
DEBUG=false

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# Evolution API
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=Revoluna

# Chatwoot
CHATWOOT_URL=http://chatwoot:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_CHANNEL=#julia-gestao

# Redis
REDIS_URL=redis://redis:6379/0

# Rate Limiting
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# Empresa
NOME_EMPRESA=Revoluna

# Limites
MAX_MENSAGEM_CHARS=4000
MAX_MENSAGEM_CHARS_TRUNCAR=10000
MAX_MENSAGEM_CHARS_REJEITAR=50000
```

### 2. Documentar secrets management

Para produção, usar:
- **Docker Secrets** (Docker Swarm)
- **Kubernetes Secrets** (K8s)
- **Vault** (HashiCorp)
- **AWS Secrets Manager** (AWS)
- **Azure Key Vault** (Azure)

### 3. Criar script de validação

```python
# scripts/check_env.py (expandir)
# Validar todas as variáveis obrigatórias
```

## DoD

- [x] .env.example criado
- [x] Documentação de secrets
- [x] Script de validação funciona
- [x] Variáveis documentadas

---

# S5.E4.4 - Logs e Monitoramento

## Objetivo

> **Configurar logging centralizado e monitoramento básico.**

**Resultado esperado:** Logs estruturados e acessíveis.

## Tarefas

### 1. Configurar logging estruturado

```python
# app/core/logging.py (atualizar)
# Adicionar formato JSON para produção
```

### 2. Adicionar driver de logs no docker-compose

```yaml
  julia-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=julia-api"
```

### 3. Criar script de visualização de logs

```bash
# scripts/view_logs.sh
#!/bin/bash
docker compose logs -f --tail=100 julia-api julia-worker julia-scheduler
```

## DoD

- [x] Logging estruturado configurado
- [x] Rotação de logs configurada
- [x] Script de visualização criado
- [x] Logs testados

---

# S5.E4.5 - CI/CD Básico

## Objetivo

> **Criar pipeline básico de CI/CD.**

**Resultado esperado:** Deploy automatizado após push.

## Tarefas

### 1. GitHub Actions workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t julia-api:latest .
      - name: Test image
        run: docker run --rm julia-api:latest python -c "import app"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to server
        # Adicionar steps de deploy (SSH, docker-compose, etc)
        run: echo "Deploy steps here"
```

### 2. Docker Hub / Registry

- Build e push de imagens
- Versionamento de tags
- Imagens por ambiente

## DoD

- [x] Workflow de CI criado
- [x] Testes automatizados
- [x] Build de imagem automatizado
- [x] Deploy automatizado (ou documentado)

---

# S5.E4.6 - Documentação de Deploy

## Objetivo

> **Criar documentação completa de deploy.**

**Resultado esperado:** Guia passo-a-passo para deploy.

## Tarefas

### 1. Criar DEPLOY.md

```markdown
# Guia de Deploy - Agente Júlia

## Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM mínimo
- 20GB disco

## Deploy Local

1. Clonar repositório
2. Copiar .env.example para .env
3. Configurar variáveis
4. `docker compose up -d`

## Deploy Produção

1. Configurar servidor
2. Instalar Docker
3. Clonar repositório
4. Configurar .env
5. Executar deploy
```

### 2. Checklist de deploy

- [ ] Variáveis de ambiente configuradas
- [ ] Secrets seguros
- [ ] Health checks funcionando
- [ ] Logs configurados
- [ ] Backup configurado
- [ ] Monitoramento ativo

## DoD

- [x] DEPLOY.md criado
- [x] Checklist completo
- [x] Troubleshooting documentado
- [x] Comandos úteis listados

---

## Resumo da Estratégia

### Arquitetura Final

```
┌─────────────────────────────────────────┐
│         Docker Compose Stack            │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐           │
│  │ julia-api│  │julia-    │           │
│  │  :8000   │  │worker    │           │
│  └────┬─────┘  └────┬─────┘           │
│       │             │                  │
│  ┌────▼─────────────▼─────┐           │
│  │   julia-scheduler      │           │
│  │   (cron jobs)          │           │
│  └────────────────────────┘           │
│                                         │
│  ┌──────────┐  ┌──────────┐           │
│  │  redis   │  │evolution │           │
│  │  :6379   │  │  :8080   │           │
│  └──────────┘  └──────────┘           │
│                                         │
│  ┌─────────────────────────┐           │
│  │    chatwoot             │           │
│  │  (rails + sidekiq)      │           │
│  └─────────────────────────┘           │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│      Serviços Externos (SaaS)          │
├─────────────────────────────────────────┤
│  • Supabase (banco)                     │
│  • Anthropic (LLM)                      │
│  • Slack (notificações)                 │
└─────────────────────────────────────────┘
```

### Vantagens desta Abordagem

1. **Isolamento**: Cada serviço em container separado
2. **Escalabilidade**: Fácil escalar workers e API
3. **Manutenção**: Atualizar um serviço sem afetar outros
4. **Logs**: Centralizados e estruturados
5. **Deploy**: Um comando para subir tudo
6. **Desenvolvimento**: Mesmo ambiente local e produção

### Próximos Passos (Futuro)

- Kubernetes para orquestração avançada
- Service mesh (Istio/Linkerd)
- Auto-scaling baseado em métricas
- Blue-green deployments
- Canary releases
- Multi-region deployment

