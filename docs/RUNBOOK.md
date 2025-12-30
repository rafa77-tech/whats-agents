# Runbook - Operações de Produção

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           REGRAS CRÍTICAS                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  1. NUNCA MERGEAR CÓDIGO QUE DEPENDE DE MIGRATION NÃO APLICADA EM PROD      ║
║                                                                              ║
║  2. QUALQUER DEPLOY QUE FALHAR EM /health/deep = ROLLBACK IMEDIATO          ║
║     (SEM "DEPOIS EU VEJO")                                                   ║
║                                                                              ║
║  3. SE /health/deep RETORNAR "CRITICAL" = DEPLOY NO AMBIENTE ERRADO         ║
║     ROLLBACK IMEDIATO E VERIFICAR VARIÁVEIS DE AMBIENTE                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Fluxo de Migrations (ORDEM CORRETA)

### O padrão seguro é: MIGRATION PRIMEIRO, CÓDIGO DEPOIS

```
1. Criar migration localmente
2. Validar SQL (no dashboard ou staging)
3. APLICAR MIGRATION NO PROD (manual)  ← ANTES do merge!
4. Verificar /health/schema no PROD
5. Só então: commit/PR do código
6. Merge → deploy → /health/deep passa
```

### Por que essa ordem?

Se você mergea código que depende de migration não aplicada:
- Deploy sobe
- App tenta usar tabela/view que não existe
- ERRO EM PRODUÇÃO
- Você corre pra aplicar migration "em pânico"

Com a ordem correta:
- Banco já está pronto
- Código novo encontra schema atualizado
- Zero janela de erro

### Checklist de Migration

```
[ ] Migration testada localmente/staging
[ ] Migration APLICADA no Supabase PROD
[ ] /health/schema confirma versão correta
[ ] PR criado com código que depende da migration
[ ] CI passou
[ ] Merge feito
[ ] /health/deep retorna 200
```

---

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
| Block force push | ✅ |
| Require linear history | ✅ (opcional, mantém histórico limpo) |

**Resultado:**
- Ninguém (nem admin) pode push direto na main
- Todo código passa pelo CI antes de mergear
- PRs são o único caminho para produção

---

## Hard Guards de Ambiente

### O que são

Hard guards previnem o erro "deploy apontando pro banco errado":

1. **APP_ENV**: Variável no container (ex: `production`)
2. **environment marker**: Valor na tabela `app_settings` no banco
3. **SUPABASE_PROJECT_REF**: Variável no container
4. **supabase_project_ref marker**: Valor na tabela `app_settings`

### Como funciona

O `/health/deep` compara:
- `APP_ENV` do container com `environment` do banco
- `SUPABASE_PROJECT_REF` do container com `supabase_project_ref` do banco

Se não baterem → retorna `CRITICAL` → deploy falha.

### Configuração

**No Supabase PROD:**
```sql
INSERT INTO app_settings (key, value, description)
VALUES
    ('environment', 'production', 'Environment marker'),
    ('supabase_project_ref', 'SEU_PROJECT_REF_AQUI', 'Project reference')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

**No Railway (variáveis):**
```
APP_ENV=production
SUPABASE_PROJECT_REF=SEU_PROJECT_REF_AQUI
```

---

## Railway: Separação de Serviços

### Estrutura recomendada

```
railway-project/
├── julia-api       # RUN_MODE=api
├── julia-worker    # RUN_MODE=worker
└── julia-scheduler # RUN_MODE=scheduler (1 instância, sem autoscale!)
```

### RUN_MODE obrigatório

O entrypoint valida `RUN_MODE` e falha se não estiver setado:

```bash
# Válidos:
RUN_MODE=api        # Uvicorn server
RUN_MODE=worker     # ARQ consumer
RUN_MODE=scheduler  # APScheduler

# Inválido (container não sobe):
RUN_MODE não setado
RUN_MODE=qualquer_outra_coisa
```

### Cuidados

| Serviço | Instâncias | Autoscale |
|---------|------------|-----------|
| API | 1-N | Sim |
| Worker | 1-N | Sim |
| Scheduler | **1 FIXO** | **NÃO** |

⚠️ **Scheduler com mais de 1 instância = jobs duplicados!**

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
