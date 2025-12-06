# Setup do Projeto - Agente Júlia

Checklist de configuração com status atual.

---

## Status Geral

| Componente | Status | Observação |
|------------|--------|------------|
| Supabase | ✅ Configurado | MCP funcionando, schema executado |
| Anthropic | ⏳ Pendente | Obter API key |
| Google Docs | ⏳ Pendente | Configurar API |
| Slack | ⏳ Pendente | Criar webhook |
| Evolution API | ✅ Docker OK | Testar conexão |
| Chatwoot | ✅ Docker OK | Configurar inbox |

---

## 1. Supabase (Banco de Dados)

### Status: ✅ Configurado

| Item | Status |
|------|--------|
| Projeto criado | ✅ |
| MCP configurado no Claude Code | ✅ |
| Extensão pgvector habilitada | ✅ |
| Schema executado (27 tabelas) | ✅ |
| 14 migrações aplicadas | ✅ |

### Variáveis de ambiente
```bash
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_SERVICE_KEY=eyJ...
```

---

## 2. Anthropic (Claude API)

### Status: ⏳ Pendente

| Item | Status | Ação |
|------|--------|------|
| Criar conta Anthropic | [ ] | https://console.anthropic.com |
| Gerar API key | [ ] | Settings > API Keys |
| Adicionar pagamento | [ ] | Settings > Billing |

### Variáveis de ambiente
```bash
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514
```

**Custo estimado:** ~$25/mês para 1000 msgs/dia (estratégia híbrida)

---

## 3. Google Cloud (Google Docs API)

### Status: ⏳ Pendente

| Item | Status | Ação |
|------|--------|------|
| Criar projeto no GCP | [ ] | https://console.cloud.google.com |
| Habilitar Google Docs API | [ ] | APIs & Services > Enable APIs |
| Criar Service Account | [ ] | IAM & Admin > Service Accounts |
| Baixar JSON credentials | [ ] | Keys > Add Key > JSON |
| Criar Google Doc de briefing | [ ] | Google Docs > Novo documento |
| Compartilhar doc com SA | [ ] | Compartilhar > email do SA |

### Variáveis de ambiente
```bash
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
BRIEFING_DOC_ID=1abc...xyz
```

---

## 4. Slack (Notificações)

### Status: ⏳ Pendente

| Item | Status | Ação |
|------|--------|------|
| Criar canal #julia-gestao | [ ] | Canais > Criar |
| Criar Slack App | [ ] | https://api.slack.com/apps |
| Criar Incoming Webhook | [ ] | Features > Incoming Webhooks |

### Variáveis de ambiente
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T.../B.../xxx
SLACK_CHANNEL=#julia-gestao
```

---

## 5. Evolution API (WhatsApp)

### Status: ✅ Docker rodando | ⏳ Conexão pendente

| Item | Status | Ação |
|------|--------|------|
| Container rodando | ✅ | `docker compose ps` |
| Acessar dashboard | [ ] | http://localhost:8080 |
| Criar instância | [ ] | Dashboard > New Instance |
| Conectar número | [ ] | QR Code |
| Configurar webhook | [ ] | Instance > Webhooks |

### Variáveis de ambiente
```bash
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=sua_chave
EVOLUTION_INSTANCE=julia
```

### Webhook a configurar
```
URL: http://[SEU_SERVIDOR]:8000/webhook/evolution
Events: messages.upsert, connection.update
```

---

## 6. Chatwoot (Supervisão)

### Status: ✅ Docker rodando | ⏳ Configuração pendente

| Item | Status | Ação |
|------|--------|------|
| Container rodando | ✅ | `docker compose ps` |
| Criar conta admin | [ ] | http://localhost:3000 |
| Criar inbox WhatsApp | [ ] | Settings > Inboxes |
| Configurar webhook | [ ] | Settings > Integrations |
| Gerar API key | [ ] | Profile > Access Token |

### Variáveis de ambiente
```bash
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1
```

---

## 7. Infraestrutura Local

### Status: ✅ OK

| Item | Status |
|------|--------|
| Docker instalado | ✅ |
| Docker Compose | ✅ |
| uv (Python) | ✅ |
| Python 3.13+ | ✅ |

### Comandos úteis
```bash
docker compose up -d      # Subir serviços
docker compose down       # Parar
docker compose ps         # Status
docker compose logs -f    # Logs
```

---

## Arquivo .env

Criar arquivo `.env` na raiz:

```bash
# SUPABASE (configurado)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# ANTHROPIC (pendente)
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# GOOGLE DOCS (pendente)
GOOGLE_APPLICATION_CREDENTIALS=./credentials/google-sa.json
BRIEFING_DOC_ID=xxx

# SLACK (pendente)
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
SLACK_CHANNEL=#julia-gestao

# EVOLUTION API
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxx
EVOLUTION_INSTANCE=julia

# CHATWOOT
CHATWOOT_URL=http://localhost:3000
CHATWOOT_API_KEY=xxx
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_ID=1

# RATE LIMITING
MAX_MSGS_POR_HORA=20
MAX_MSGS_POR_DIA=100
HORARIO_INICIO=08:00
HORARIO_FIM=20:00

# APP
NOME_EMPRESA=Revoluna
GESTOR_WHATSAPP=5511999999999
ENVIRONMENT=development
```

---

## Próximos Passos

1. **Obter API key Anthropic** - Criar conta e gerar chave
2. **Configurar Slack** - Criar app e webhook
3. **Testar Evolution** - Conectar número de teste
4. **Configurar Chatwoot** - Criar inbox e webhook
5. **Configurar Google Docs** - Service account e doc de briefing

---

## Troubleshooting

### Evolution API não responde
```bash
docker compose ps evolution-api
docker compose logs -f evolution-api
curl http://localhost:8080/
```

### Chatwoot não inicia
```bash
docker compose logs rails
docker compose exec rails bundle exec rails db:migrate
```

### Supabase MCP não conecta
```bash
# Testar conexão direta
curl -H "apikey: $SUPABASE_SERVICE_KEY" "$SUPABASE_URL/rest/v1/"
```
