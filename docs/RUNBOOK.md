# Runbook - Operações de Produção

## Branch Protection (Obrigatório)

### Configurar no GitHub

Repository → Settings → Branches → Add rule

**Branch name pattern:** `main`

**Proteções obrigatórias:**

| Setting | Valor |
|---------|-------|
| Require a pull request before merging | ✅ |
| Require approvals | 1 (opcional, mas recomendado) |
| Require status checks to pass | ✅ |
| Required status checks | `Lint & Type Check`, `Run Tests`, `Build Docker Image` |
| Require branches to be up to date | ✅ |
| Do not allow bypassing | ✅ |

**Resultado:**
- Ninguém (nem admin) pode push direto na main
- Todo código passa pelo CI antes de mergear
- PRs são o único caminho para produção

---

## Migrations

### Processo (Manual com Runbook)

**ANTES de qualquer deploy:**

1. **Verificar migrations pendentes**
   ```bash
   # Lista migrations aplicadas
   curl https://SEU-APP.railway.app/health/schema | jq .
   ```

2. **Se houver migration nova no código:**
   - Aplicar migration no Supabase PROD via Dashboard ou CLI
   - Aguardar confirmação
   - Só então fazer merge do PR

3. **Verificar após deploy:**
   ```bash
   curl https://SEU-APP.railway.app/health/deep | jq .
   ```

### Checklist de Migration

```
[ ] Migration testada em staging/dev
[ ] Migration aplicada no Supabase PROD
[ ] /health/schema mostra versão correta
[ ] PR mergeado
[ ] /health/deep retorna 200
```

### Em caso de erro

Se o deploy subir com migration faltando:

1. **NÃO entre em pânico** - o health check vai falhar
2. Aplique a migration manualmente no Supabase
3. O próximo health check deve passar
4. Se não passar, verifique logs do Railway

---

## Deploy

### Fluxo Normal

```
Feature Branch → PR → CI passa → Merge → Deploy automático → Health Check
```

### Deploy Manual (emergência)

```bash
# Via Railway CLI
railway login
railway up

# Via GitHub Actions
gh workflow run ci.yml --ref main
```

### Rollback

1. Railway Dashboard → Deployments
2. Encontrar último deploy estável
3. Clicar "Redeploy"

---

## Health Checks

### Endpoints

| Endpoint | Uso | Retorno |
|----------|-----|---------|
| `/health` | Liveness | Sempre 200 se app rodando |
| `/health/ready` | Readiness | 200 se Redis conectado |
| `/health/deep` | CI/CD | 200 se TUDO ok, 503 se algo falhar |
| `/health/schema` | Debug | Info de migrations |

### Deep Health Check

O `/health/deep` verifica:

1. **Redis** - ping
2. **Supabase** - conexão
3. **Tabelas críticas** - existem e respondem
4. **Views críticas** - existem e respondem
5. **Schema version** - última migration >= esperada

Se qualquer check falhar → HTTP 503 → Deploy marcado como falho.

---

## Incidentes

### App não responde

```bash
# 1. Verificar status Railway
railway status

# 2. Ver logs
railway logs --tail 100

# 3. Se necessário, restart
railway restart
```

### Health check falhando

```bash
# 1. Identificar o que está falhando
curl https://SEU-APP.railway.app/health/deep | jq .

# 2. Comum: Migration faltando
# Solução: Aplicar migration no Supabase

# 3. Comum: Redis desconectado
# Solução: Verificar serviço Redis no Railway

# 4. Comum: View não existe
# Solução: Criar view via SQL no Supabase
```

### Pausar Julia (emergência)

```sql
-- No Supabase SQL Editor
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergência - pausado manualmente', 'manual');
```

### Retomar Julia

```sql
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operação', 'manual');
```

---

## Secrets Management

### GitHub Secrets necessários

| Secret | Obrigatório | Ambiente |
|--------|-------------|----------|
| `SUPABASE_URL` | ✅ | Staging (para testes) |
| `SUPABASE_SERVICE_KEY` | ✅ | Staging (para testes) |
| `ANTHROPIC_API_KEY` | ✅ | Produção |
| `RAILWAY_TOKEN` | ✅ | Deploy |
| `RAILWAY_APP_URL` | ✅ | Health check |
| `SLACK_WEBHOOK_URL` | ❌ | Notificações |

### Railway Variables (produção)

Todas as variáveis do `.env.example` devem estar configuradas no Railway.

**Críticas:**
- `SUPABASE_URL` → Projeto PROD
- `SUPABASE_SERVICE_KEY` → Service key PROD
- `REDIS_URL` → Injetada automaticamente pelo Railway

---

## Monitoramento

### Logs

```bash
# Railway logs
railway logs -f

# Filtrar por erro
railway logs | grep -i error
```

### Métricas

- Railway Dashboard → métricas de CPU/Memory
- `/health/rate-limit` → uso de rate limit
- `/health/circuits` → status circuit breakers

### Alertas

Configurados via Slack:
- Deploy success/failure
- Health check failures (manual verificar)
