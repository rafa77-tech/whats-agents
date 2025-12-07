# Runbook Operacional - Júlia

## Arquitetura

```
[WhatsApp] → [Evolution API] → [FastAPI] → [Claude API]
                                    ↓
                              [Supabase]
                                    ↓
                              [Chatwoot]
                                    ↓
                              [Redis Cache]
```

## Serviços

| Serviço | URL | Health Check |
|---------|-----|--------------|
| API | http://localhost:8000 | `/health` |
| Evolution | http://localhost:8080 | `/status` |
| Chatwoot | http://localhost:3000 | `/api/v1/profile` |
| Redis | localhost:6379 | `redis-cli PING` |

## Comandos Úteis

### Docker

```bash
# Ver status
docker compose ps

# Logs
docker compose logs -f api

# Reiniciar serviço
docker compose restart api

# Ver logs de erro
docker compose logs api | grep ERROR
```

### Banco de Dados

```sql
-- Conversas ativas
SELECT COUNT(*) FROM conversations WHERE status = 'active';

-- Fila pendente
SELECT COUNT(*) FROM fila_mensagens WHERE status = 'pendente';

-- Handoffs pendentes
SELECT * FROM handoffs WHERE status = 'pendente' ORDER BY created_at DESC;

-- Últimas mensagens
SELECT * FROM interacoes ORDER BY created_at DESC LIMIT 10;

-- Performance de queries
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### Redis

```bash
# Conectar ao Redis
redis-cli

# Ver todas as chaves
KEYS *

# Ver chaves de cache
KEYS medico:*
KEYS vagas:*
KEYS contexto:*

# Limpar cache
FLUSHDB

# Ver TTL de uma chave
TTL medico:telefone:5511999999999
```

## Procedimentos

### 1. Alta taxa de erros

**Sintomas:**
- Logs mostram muitos erros
- Usuários reportam problemas

**Diagnóstico:**
1. Verificar logs: `docker compose logs -f api | grep ERROR`
2. Verificar métricas: `GET /admin/metricas/performance`
3. Verificar saúde: `GET /admin/metricas/health`
4. Verificar Redis: `redis-cli PING`
5. Verificar conexão Supabase: testar query simples

**Solução:**
- Se Redis offline: `docker compose restart redis`
- Se banco lento: verificar índices, conexões
- Se API key inválida: verificar variáveis de ambiente

### 2. WhatsApp desconectado

**Sintomas:**
- Mensagens não são enviadas
- Erro "WhatsApp not connected"

**Diagnóstico:**
1. Acessar Evolution: http://localhost:8080
2. Verificar status da instância
3. Verificar logs: `docker compose logs evolution`

**Solução:**
- Se desconectado, escanear QR novamente
- Se instância não existe, criar nova
- Testar envio manual via Evolution API

### 3. Fila congestionada

**Sintomas:**
- Fila cresce mas não processa
- Mensagens não são enviadas

**Diagnóstico:**
1. Verificar quantidade: `SELECT COUNT(*) FROM fila_mensagens WHERE status = 'pendente'`
2. Verificar worker: `docker compose logs -f worker`
3. Verificar rate limiting

**Solução:**
- Se worker travado: `docker compose restart worker`
- Se rate limit: aguardar ou ajustar limites
- Se muitos erros: verificar logs e corrigir causa raiz

### 4. Handoff não notificado

**Sintomas:**
- Label adicionada mas Júlia continua respondendo
- Gestor não recebe notificação

**Diagnóstico:**
1. Verificar webhook Slack configurado
2. Verificar campo `controlled_by` na conversa
3. Verificar logs de handoff: `docker compose logs api | grep handoff`

**Solução:**
- Se webhook não configurado: configurar em Chatwoot
- Se campo não atualiza: verificar integração
- Se Slack não notifica: verificar webhook URL

### 5. Performance degradada

**Sintomas:**
- Respostas muito lentas (> 30s)
- Queries demorando muito

**Diagnóstico:**
1. `GET /admin/metricas/performance`
2. Identificar operação lenta
3. Verificar uso de recursos: `docker stats`
4. Verificar cache hit rate

**Solução:**
- Se banco lento: verificar índices, executar `ANALYZE`
- Se LLM lento: verificar status Anthropic
- Se cache miss alto: verificar Redis
- Se CPU alto: escalar recursos

### 6. Cache não funciona

**Sintomas:**
- Queries sempre vão ao banco
- Performance ruim

**Diagnóstico:**
1. Verificar Redis: `redis-cli PING`
2. Verificar chaves: `redis-cli KEYS "*"`
3. Verificar TTL: `redis-cli TTL medico:telefone:...`

**Solução:**
- Se Redis offline: `docker compose restart redis`
- Se chaves expiram rápido: aumentar TTL
- Se cache não invalida: verificar lógica de invalidação

## Variáveis de Ambiente

### Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SUPABASE_URL` | URL do projeto Supabase | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Chave de serviço | `eyJ...` |
| `ANTHROPIC_API_KEY` | Chave da API Anthropic | `sk-ant-...` |
| `EVOLUTION_URL` | URL da Evolution API | `http://localhost:8080` |
| `EVOLUTION_API_KEY` | Chave da Evolution | `xxx` |
| `REDIS_URL` | URL do Redis | `redis://localhost:6379` |

### Opcionais

| Variável | Descrição | Default |
|----------|-----------|---------|
| `LOG_LEVEL` | Nível de log | `INFO` |
| `MAX_WORKERS` | Workers paralelos | `4` |
| `CACHE_TTL` | TTL do cache em segundos | `300` |

### Chatwoot

| Variável | Descrição |
|----------|-----------|
| `CHATWOOT_URL` | URL do Chatwoot |
| `CHATWOOT_API_TOKEN` | Token de API |
| `CHATWOOT_ACCOUNT_ID` | ID da conta |
| `CHATWOOT_INBOX_ID` | ID do inbox |

### Slack

| Variável | Descrição |
|----------|-----------|
| `SLACK_WEBHOOK_URL` | URL do webhook |

## Troubleshooting

### Mensagens não estão sendo enviadas

**Sintomas:**
- Fila cresce mas não processa
- Logs mostram erros de envio

**Diagnóstico:**
1. Verificar status Evolution API
2. Verificar conexão WhatsApp
3. Verificar rate limiting
4. Verificar logs: `docker compose logs api | grep "enviar"`

**Solução:**
- Se Evolution offline: reiniciar container
- Se WhatsApp desconectado: reconectar via QR
- Se rate limit: aguardar ou ajustar limites
- Se erro de autenticação: verificar API key

### Respostas muito lentas

**Sintomas:**
- Tempo de resposta > 30s
- Usuários reclamando

**Diagnóstico:**
1. `GET /admin/metricas/performance`
2. Identificar operação lenta
3. Verificar uso de recursos
4. Verificar cache hit rate

**Solução:**
- Se banco lento: verificar índices, conexões
- Se LLM lento: verificar status Anthropic
- Se cache miss alto: verificar Redis
- Se CPU alto: escalar recursos

### Handoff não funciona

**Sintomas:**
- Label adicionada mas Júlia continua respondendo
- Gestor não notificado

**Diagnóstico:**
1. Verificar webhook Chatwoot configurado
2. Verificar campo `controlled_by` na conversa
3. Verificar logs de handoff

**Solução:**
- Se webhook não configurado: configurar em Chatwoot
- Se campo não atualiza: verificar integração
- Se Slack não notifica: verificar webhook URL

## Monitoramento

### Métricas Principais

- **Tempo de resposta**: < 5s (ideal), < 10s (aceitável)
- **Taxa de handoff**: < 20%
- **Score de qualidade**: > 7/10
- **Cache hit rate**: > 80%
- **Taxa de erro**: < 1%

### Alertas

- Performance crítica: tempo > 2s
- Performance warning: tempo > 1s
- Taxa de handoff alta: > 20%
- Score baixo: < 5/10
- Sem respostas: 0 mensagens em 30min

### Dashboards

- Métricas em tempo real: `/admin/metricas/performance`
- Health check: `/admin/metricas/health`
- Dashboard de métricas: `/static/dashboard.html`

## Manutenção

### Backup

```bash
# Backup do banco (Supabase)
# Fazer via interface do Supabase

# Backup do Redis
redis-cli --rdb /backup/redis.rdb
```

### Limpeza

```sql
-- Limpar conversas antigas (> 90 dias)
DELETE FROM conversations WHERE created_at < NOW() - INTERVAL '90 days';

-- Limpar interações antigas
DELETE FROM interacoes WHERE created_at < NOW() - INTERVAL '90 days';

-- Limpar fila antiga
DELETE FROM fila_mensagens WHERE status = 'enviada' AND enviada_em < NOW() - INTERVAL '30 days';
```

### Atualização

```bash
# Atualizar código
git pull
docker compose build
docker compose up -d

# Verificar logs
docker compose logs -f api
```

