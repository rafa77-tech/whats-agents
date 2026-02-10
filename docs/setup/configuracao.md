# Configuracao e Setup

> Como configurar e rodar o projeto localmente

---

## Pre-requisitos

| Requisito | Versao | Instalacao |
|-----------|--------|------------|
| Python | 3.13+ | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh | sh` |
| Docker | 24+ | [docker.com](https://docker.com) |
| Docker Compose | 2.0+ | Incluso no Docker Desktop |

---

## 1. Clonar o Repositorio

```bash
git clone <repo-url>
cd whatsapp-api
```

---

## 2. Instalar Dependencias Python

```bash
# Instalar uv (se ainda nao tem)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync

# Verificar instalacao
uv run python --version
```

---

## 3. Configurar Variaveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar com suas credenciais
nano .env  # ou code .env
```

### Variaveis Obrigatorias

```bash
# ==============================================
# APP
# ==============================================
APP_NAME=Agente Julia
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# ==============================================
# TIMEZONE (CRITICO)
# ==============================================
TZ=America/Sao_Paulo

# ==============================================
# DEPLOY / RUNTIME
# ==============================================
# APP_ENV: development, staging, production
APP_ENV=development

# RUN_MODE: Define qual servico o container executa
# OBRIGATORIO para containers Docker!
# Opcoes: api, worker, scheduler
RUN_MODE=api

# ==============================================
# SEGURANCA
# ==============================================
# JWT Secret para tokens de confirmacao externa
# OBRIGATORIO em producao! Gerar com: openssl rand -hex 32
JWT_SECRET_KEY=

# CORS - origens permitidas (separadas por virgula)
CORS_ORIGINS=*

# ==============================================
# SUPABASE (Banco de Dados)
# ==============================================
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_PROJECT_REF=

# ==============================================
# ANTHROPIC (Claude LLM)
# ==============================================
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# ==============================================
# VOYAGE AI (Embeddings para RAG)
# ==============================================
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=voyage-3.5-lite

# ==============================================
# EVOLUTION API (WhatsApp)
# ==============================================
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=Revoluna

# Multi-Chip (Sprint 26)
MULTI_CHIP_ENABLED=false

# ==============================================
# REDIS (Cache e Filas)
# ==============================================
REDIS_URL=redis://localhost:6379/0

# ==============================================
# MODO PILOTO (Sprint 32)
# ==============================================
# PILOT_MODE=true (default): Funcionalidades autonomas DESABILITADAS
# PILOT_MODE=false: Todas as funcionalidades habilitadas
PILOT_MODE=true

# ==============================================
# RATE LIMITING
# ==============================================
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# ==============================================
# LIMITES DE MENSAGEM
# ==============================================
MAX_MENSAGEM_CHARS=4000
MAX_MENSAGEM_CHARS_TRUNCAR=10000
MAX_MENSAGEM_CHARS_REJEITAR=50000

# ==============================================
# EMPRESA
# ==============================================
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
```

### Variaveis Opcionais

```bash
# ==============================================
# CHATWOOT (Supervisao Humana)
# ==============================================
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# ==============================================
# SLACK (Notificacoes e Comandos)
# ==============================================
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
SLACK_CHANNEL=#julia-gestao
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_SIGNING_SECRET=xxx

# ==============================================
# GOOGLE DOCS (Briefing)
# ==============================================
# Service Account credentials
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json

# ID do documento de briefing (LEGADO)
BRIEFING_DOC_ID=

# ID da pasta de briefings (RECOMENDADO - Sprint 11)
GOOGLE_BRIEFINGS_FOLDER_ID=

# ID da pasta de templates de campanha
# Estrutura esperada:
#   Templates/
#   ├── Discovery/
#   ├── Oferta/
#   ├── Reativacao/
#   ├── Followup/
#   └── Feedback/
GOOGLE_TEMPLATES_FOLDER_ID=

# ==============================================
# JULIA API (para scheduler)
# ==============================================
JULIA_API_URL=http://localhost:8000
```

---

## 4. Subir Servicos Docker

O projeto usa Docker Compose para:
- Evolution API (WhatsApp)
- Redis (Cache/Filas)
- Chatwoot (Supervisao)
- PostgreSQL (para Chatwoot)

```bash
# Subir todos os servicos
docker compose up -d

# Verificar status
docker compose ps

# Ver logs
docker compose logs -f evolution-api
docker compose logs -f redis
```

### Servicos e Portas

| Servico | Porta | URL |
|---------|-------|-----|
| Evolution API | 8080 | http://localhost:8080 |
| Chatwoot | 3000 | http://localhost:3000 |
| Redis | 6379 | redis://localhost:6379 |
| PostgreSQL | 5432 | localhost:5432 |
| PgAdmin | 4000 | http://localhost:4000 |

---

## 5. Configurar Supabase

### Criar Projeto

1. Acesse [supabase.com](https://supabase.com)
2. Crie novo projeto
3. Anote URL e Service Key

### Aplicar Migracoes

As migracoes sao aplicadas via MCP Supabase no Claude Code:

```
# No Claude Code, as migracoes ja foram aplicadas
# Para verificar:
mcp__supabase__list_migrations
```

### Migracoes Aplicadas (30)

```
20251201161446_enable_vector_extension
20251201161728_add_ai_fields_to_clientes
20251201162355_create_conversations_table
20251201165231_create_handoffs_table
20251201165319_create_doctor_context_table_v2
20251201165353_create_whatsapp_instances_table
20251201165429_add_conversation_to_interacoes
20251201170626_enable_rls_all_tables
20251205220329_create_vagas_schema
20251205223114_create_gestao_julia_schema
20251207103105_seed_especialidades
20251207103110_seed_periodos
20251207103115_seed_setores
20251207121037_create_fila_mensagens
20251207152343_create_metricas_conversa
20251207152351_create_avaliacoes_qualidade
20251207203326_create_metricas_deteccao_bot
20251207203834_create_briefing_sync_log
... (mais 12)
```

---

## 6. Configurar Evolution API

### 1. Acessar Painel

Acesse http://localhost:8080 e crie uma API key.

### 2. Criar Instancia WhatsApp

```bash
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: SUA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "julia",
    "qrcode": true
  }'
```

### 3. Escanear QR Code

```bash
# Ver QR code
curl http://localhost:8080/instance/qrcode/julia \
  -H "apikey: SUA_API_KEY"
```

### 4. Configurar Webhook

```bash
curl -X POST http://localhost:8080/webhook/set/julia \
  -H "apikey: SUA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://host.docker.internal:8000/webhook/evolution",
    "webhook_by_events": false,
    "events": ["messages.upsert"]
  }'
```

---

## 7. Rodar a API

### Desenvolvimento (com reload)

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### Producao

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verificar

```bash
# Health check
curl http://localhost:8000/health

# Esperado:
# {"status": "ok", "timestamp": "..."}
```

---

## 8. Rodar Workers

### Scheduler (jobs agendados)

```bash
uv run python -m app.workers scheduler
```

### Fila Worker (mensagens agendadas)

```bash
uv run python -m app.workers fila
```

---

## 9. Rodar Testes

```bash
# Todos os testes
uv run pytest

# Com verbose
uv run pytest -v

# Apenas um arquivo
uv run pytest tests/test_optout.py

# Ignorar pasta
uv run pytest tests/ --ignore=tests/optout/
```

---

## Estrutura de Configuracao

### app/core/config.py

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Agente Julia"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    # Anthropic
    ANTHROPIC_API_KEY: str
    LLM_MODEL: str = "claude-3-5-haiku-20241022"
    LLM_MODEL_COMPLEX: str = "claude-sonnet-4-20250514"

    # Evolution
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str
    EVOLUTION_INSTANCE: str = "julia"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Rate Limits
    MAX_MSGS_POR_HORA: int = 20
    MAX_MSGS_POR_DIA: int = 100

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Troubleshooting

### Erro: "Connection refused" no Redis

```bash
# Verificar se Redis esta rodando
docker compose ps redis

# Se nao estiver, subir
docker compose up -d redis
```

### Erro: "401 Unauthorized" no Supabase

1. Verificar SUPABASE_SERVICE_KEY (nao anon key)
2. Key deve comecar com `eyJ`

### Erro: "Could not connect" no Evolution

```bash
# Verificar se Evolution esta rodando
docker compose logs evolution-api

# Reiniciar se necessario
docker compose restart evolution-api
```

### Erro: Porta ja em uso

```bash
# Verificar o que esta usando a porta
lsof -i :8000

# Matar processo
kill -9 <PID>
```

---

## Comandos Uteis

```bash
# Ver logs em tempo real
docker compose logs -f

# Reiniciar servico especifico
docker compose restart redis

# Parar tudo
docker compose down

# Parar e remover volumes
docker compose down -v

# Reconstruir imagens
docker compose build --no-cache

# Ver uso de recursos
docker stats
```
