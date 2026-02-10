# Setup do Projeto - Agente Júlia

**Nota:** Todos os serviços estão configurados e em produção. Este guia é para novos desenvolvedores configurando o ambiente local.

Checklist de configuração com status atual.

---

## Status Geral

| Componente | Status | Observação |
|------------|--------|------------|
| Supabase | ✅ Configurado | MCP funcionando, 64+ tabelas |
| Anthropic | ✅ Configurado | Haiku 3.5 + Sonnet 4 (híbrido) |
| Google Docs | ✅ Configurado | Briefing sync ativo |
| Slack | ✅ Configurado | Notificações + NLP commands |
| Evolution API | ✅ Configurado | WhatsApp em produção |
| Chatwoot | ✅ Configurado | Supervisor ativo |
| Redis | ✅ Configurado | Cache, queues, rate limiting |
| Railway | ✅ Configurado | 3 serviços em produção |

---

## 1. Supabase (Banco de Dados)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Projeto criado | ✅ |
| MCP configurado no Claude Code | ✅ |
| Extensão pgvector habilitada | ✅ |
| Schema executado (64+ tabelas) | ✅ |
| Migrações aplicadas | ✅ |

### Variáveis de ambiente
```bash
SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

### Ferramentas MCP disponíveis
```bash
mcp__supabase__execute_sql         # Executar SQL
mcp__supabase__apply_migration     # Aplicar migration
mcp__supabase__list_tables         # Listar tabelas
mcp__supabase__get_project_url     # Obter URL do projeto
```

**Documentação:** `docs/arquitetura/banco-de-dados.md`

---

## 2. Anthropic (Claude API)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Conta Anthropic | ✅ |
| API key gerada | ✅ |
| Billing configurado | ✅ |
| Estratégia híbrida | ✅ (80% Haiku, 20% Sonnet) |

### Variáveis de ambiente
```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514
```

**Custo atual:** ~$25/mês para 1000 msgs/dia (estratégia híbrida)

**Documentação:** Estratégia híbrida documentada em `CLAUDE.md`

---

## 3. Google Cloud (Google Docs API)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Projeto no GCP | ✅ |
| Google Docs API habilitada | ✅ |
| Service Account criada | ✅ |
| JSON credentials | ✅ |
| Google Doc de briefing | ✅ |
| Doc compartilhado com SA | ✅ |

### Variáveis de ambiente
```bash
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
BRIEFING_DOC_ID=1abc...xyz
```

**Funcionalidade:** Sync automático de briefing (Sprint 7)

---

## 4. Slack (Notificações + NLP Commands)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Canal #julia-gestao | ✅ |
| Slack App criada | ✅ |
| Incoming Webhook | ✅ |
| Bot Token | ✅ |
| NLP Commands (14 tools) | ✅ |
| Helena Agent (analytics) | ✅ |

### Variáveis de ambiente
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
SLACK_CHANNEL=#julia-gestao
SLACK_BOT_TOKEN=xoxb-...
```

**Funcionalidades:**
- Notificações de handoff, erros, métricas
- Comandos NLP: métricas, médicos, vagas, campanhas (Sprint 9)
- Helena Agent: analytics via SQL dinâmico (Sprint 47)

---

## 5. Evolution API (WhatsApp)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Container rodando | ✅ |
| Instância criada | ✅ |
| Número conectado | ✅ |
| Webhook configurado | ✅ |
| Multi-instância | ✅ (Sprint 6) |

### Variáveis de ambiente
```bash
EVOLUTION_API_URL=https://evolution.exemplo.com
EVOLUTION_API_KEY=sua_chave
EVOLUTION_INSTANCE=julia
```

### Webhook configurado
```
URL: https://api.exemplo.com/webhook/evolution
Events: messages.upsert, connection.update
```

**Documentação:** `docs/integracoes/evolution-api-quickref.md`

---

## 6. Chatwoot (Supervisão)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Container rodando | ✅ |
| Conta admin criada | ✅ |
| Inbox WhatsApp | ✅ |
| Webhook configurado | ✅ |
| API key gerada | ✅ |
| Handoff IA→Humano | ✅ |

### Variáveis de ambiente
```bash
CHATWOOT_URL=https://chatwoot.exemplo.com
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

**Funcionalidades:**
- Handoff automático (sentimento negativo, pedido humano)
- Handoff manual via label "humano"
- Supervisão de conversas

**Documentação:** `docs/integracoes/chatwoot-api-quickref.md`

---

## 7. Redis (Cache, Queues, Rate Limiting)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Container rodando | ✅ |
| Rate limiting | ✅ (20/hora, 100/dia) |
| Cache de sessões | ✅ |
| Fila de mensagens | ✅ |
| Circuit breaker | ✅ |

### Variáveis de ambiente
```bash
REDIS_URL=redis://localhost:6379
REDIS_DB=0
```

**Funcionalidades:**
- Rate limiting crítico para WhatsApp (evitar ban)
- Cache de contexto de conversas
- Fila de mensagens agendadas
- Circuit breaker para resiliência

**Documentação:** Rate limiting documentado em `CLAUDE.md`

---

## 8. Railway (Deploy Produção)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Projeto criado | ✅ |
| 3 serviços deployados | ✅ |
| Variáveis de ambiente | ✅ |
| Domínio customizado | ✅ |
| CI/CD ativo | ✅ |

### Serviços em produção
```bash
1. whatsapp-api      # FastAPI app
2. worker            # Background jobs
3. scheduler         # Cron jobs (campanhas, warmer)
```

### Variáveis críticas
```bash
# Todas as variáveis acima +
DATABASE_URL=postgresql://...
ENVIRONMENT=production
LOG_LEVEL=info
```

**Documentação:**
- `docs/integracoes/railway-quickref.md`
- `docs/integracoes/railway-deploy.md`

---

## 9. Infraestrutura Local

### Status: ✅ OK

| Item | Status |
|------|--------|
| Docker instalado | ✅ |
| Docker Compose | ✅ |
| uv (Python) | ✅ |
| Python 3.13+ | ✅ |

### Comandos úteis
```bash
# Docker services
docker compose up -d              # Subir serviços
docker compose down               # Parar
docker compose ps                 # Status
docker compose logs -f evolution-api  # Logs específicos

# Python dependencies
uv sync                          # Instalar dependências
uv add <pacote>                  # Adicionar pacote

# Development
uv run pytest                    # Rodar testes
uv run uvicorn app.main:app --reload  # Rodar API local
```

---

## Arquivo .env

Criar arquivo `.env` na raiz para desenvolvimento local:

```bash
# SUPABASE
SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# ANTHROPIC
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# GOOGLE DOCS
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
BRIEFING_DOC_ID=xxx

# SLACK
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_CHANNEL=#julia-gestao
SLACK_BOT_TOKEN=xoxb-...

# EVOLUTION API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=julia

# CHATWOOT
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# REDIS
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# RATE LIMITING (CRÍTICO - evitar ban WhatsApp)
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# APP
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
ENVIRONMENT=development
LOG_LEVEL=debug

# VOYAGE AI (embeddings)
VOYAGE_API_KEY=pa-...
```

**Nota:** Solicitar `.env` completo ao time para ter valores reais de produção.

---

## Próximos Passos (Onboarding)

Para novos desenvolvedores:

1. **Clonar repositório**
   ```bash
   git clone <repo-url>
   cd whatsapp-api
   ```

2. **Instalar dependências**
   ```bash
   uv sync
   ```

3. **Configurar .env**
   - Solicitar arquivo `.env` ao time
   - Ou criar novo com valores de desenvolvimento

4. **Subir serviços locais**
   ```bash
   docker compose up -d
   ```

5. **Verificar conexões**
   ```bash
   # Evolution API
   curl http://localhost:8080/

   # Chatwoot
   curl http://localhost:3000/

   # Redis
   docker compose exec redis redis-cli ping
   ```

6. **Rodar testes**
   ```bash
   uv run pytest
   ```

7. **Rodar API local**
   ```bash
   uv run uvicorn app.main:app --reload
   ```

8. **Ler documentação**
   - `CLAUDE.md` - Fonte única de verdade
   - `docs/arquitetura/` - Arquitetura do sistema
   - `docs/julia/` - Persona e prompts
   - `app/CONVENTIONS.md` - Convenções de código

---

## Troubleshooting

### Evolution API não responde
```bash
docker compose ps evolution-api
docker compose logs -f evolution-api
curl http://localhost:8080/

# Verificar se porta está em uso
lsof -i :8080
```

### Chatwoot não inicia
```bash
docker compose logs chatwoot
docker compose exec chatwoot bundle exec rails db:migrate

# Recriar database (CUIDADO)
docker compose down
docker volume rm whatsapp-api_chatwoot_postgres_data
docker compose up -d
```

### Redis não conecta
```bash
docker compose ps redis
docker compose logs redis
docker compose exec redis redis-cli ping

# Verificar porta
lsof -i :6379
```

### Supabase MCP não conecta
```bash
# Testar conexão direta
curl -H "apikey: $SUPABASE_SERVICE_KEY" "$SUPABASE_URL/rest/v1/"

# Verificar MCP instalado
claude mcp list

# Reconfigurar se necessário
claude mcp add supabase --transport http "https://mcp.supabase.com/mcp?project_ref=jyqgbzhqavgpxqacduoi"
```

### API local não inicia
```bash
# Verificar porta 8000
lsof -i :8000

# Verificar logs
uv run uvicorn app.main:app --reload --log-level debug

# Verificar .env
cat .env | grep -v "^#" | grep -v "^$"
```

### Testes falhando
```bash
# Rodar testes com verbose
uv run pytest -vv

# Rodar teste específico
uv run pytest tests/test_agent.py::test_processar_mensagem -vv

# Verificar coverage
uv run pytest --cov=app --cov-report=html
```

### Dashboard (Next.js) não inicia
```bash
cd dashboard
npm install
npm run dev

# Verificar porta 3001
lsof -i :3001

# Build para verificar erros
npm run build
```

---

## Recursos Adicionais

### Documentação
- `CLAUDE.md` - Guia principal do projeto
- `docs/arquitetura/` - Arquitetura e design
- `docs/setup/` - Configuração e deploy
- `docs/operacao/` - Runbooks e procedimentos
- `docs/integracoes/` - APIs externas
- `docs/julia/` - Persona, prompts, conhecimento

### Quick References
- `docs/integracoes/evolution-api-quickref.md` - Evolution API
- `docs/integracoes/chatwoot-api-quickref.md` - Chatwoot
- `docs/integracoes/railway-quickref.md` - Railway CLI

### Ferramentas
```bash
# Railway CLI
railway login
railway logs -n 50
railway status

# Supabase MCP
mcp__supabase__list_tables
mcp__supabase__execute_sql

# Docker
docker compose ps
docker compose logs -f <service>
docker compose restart <service>
```

---

## Contato

Para dúvidas ou acesso a credenciais, contatar o time via Slack #julia-gestao.
