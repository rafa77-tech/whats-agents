# Agente Júlia

Escalista virtual autônoma para staffing médico da Revoluna.

Júlia é um agente de IA que prospecta médicos, oferece plantões, gerencia relacionamentos e fecha vagas via WhatsApp.

**Objetivo principal:** Passar no teste de Turing - médicos não devem perceber que estão falando com uma IA.

## Para Desenvolvedores

| Recurso | Link |
|---------|------|
| Documentação Completa | [docs/README.md](docs/README.md) |
| Setup Local | [docs/setup/setup.md](docs/setup/setup.md) |
| Arquitetura | [docs/arquitetura/visao-geral.md](docs/arquitetura/visao-geral.md) |
| Convenções de Código | [app/CONVENTIONS.md](app/CONVENTIONS.md) |
| Integrações | [docs/integracoes/README.md](docs/integracoes/README.md) |

## Para Claude Code

O arquivo **CLAUDE.md** é a fonte única de verdade para instruções de IA.

## Quick Start

```bash
# Instalar dependências Python
uv sync

# Subir serviços (Evolution API, Chatwoot, Redis)
docker compose up -d

# Rodar aplicação
uv run uvicorn app.main:app --reload

# Rodar testes
uv run pytest
```

## Stack Tecnológico

| Componente | Tecnologia |
|------------|------------|
| Backend | Python 3.13+ / FastAPI |
| LLM | Claude (Haiku 80% + Sonnet 20%) |
| Banco de Dados | Supabase (PostgreSQL + pgvector) |
| WhatsApp | Evolution API |
| Supervisão | Chatwoot |
| Notificações | Slack |
| Cache/Filas | Redis |
| Embeddings | Voyage AI |

## Serviços Locais

| Serviço | Porta | URL |
|---------|-------|-----|
| Evolution API | 8080 | http://localhost:8080 |
| Chatwoot | 3000 | http://localhost:3000 |
| n8n | 5678 | http://localhost:5678 |
| PgAdmin | 4000 | http://localhost:4000 |
| Redis | 6379 | - |

## Estrutura do Projeto

```
/whatsapp-api
├── app/                  # Código principal
│   ├── api/routes/       # Endpoints FastAPI (28 routers)
│   ├── services/         # Serviços de negócio (267 módulos)
│   ├── tools/            # Tools do agente LLM
│   ├── pipeline/         # Pipeline de processamento
│   ├── prompts/          # Sistema de prompts dinâmicos
│   └── workers/          # Jobs agendados (10 workers)
├── docs/                 # Documentação técnica
├── planning/             # Planejamento de sprints
├── tests/                # Testes automatizados (2662 testes)
├── dashboard/            # Frontend Next.js
├── CLAUDE.md             # Instruções para Claude Code
└── docker-compose.yml    # Serviços Docker
```

## Comandos Úteis

```bash
# Docker
docker compose up -d             # Subir serviços
docker compose down              # Parar
docker compose logs -f <serviço> # Ver logs

# Python
uv sync                          # Instalar dependências
uv add <pacote>                  # Adicionar pacote
uv run pytest                    # Rodar testes

# Dashboard
cd dashboard && npm run validate # Validar frontend
```

## Configuração

Copie o arquivo de exemplo e configure suas variáveis:

```bash
cp .env.example .env
```

Variáveis obrigatórias:
- `ANTHROPIC_API_KEY` - API key do Claude
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` - Credenciais Supabase
- `EVOLUTION_API_KEY` - API key Evolution
- `SLACK_WEBHOOK_URL` - Webhook do Slack

---

*Projeto iniciado em 05/12/2025 | Revoluna*
