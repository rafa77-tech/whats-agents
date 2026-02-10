# Runbook - Operações de Produção

Enterprise-grade operational procedures for Agente Júlia production system.

---

## CRITICAL RULES - READ FIRST

```
╔════════════════════════════════════════════════════════════════════════════════╗
║                      REGRAS CRÍTICAS DE OPERAÇÃO                              ║
║                                                                                ║
║  1. NUNCA mergear código que depende de migration NÃO aplicada em PROD       ║
║     Ordem correta: MIGRATION FIRST → CÓDIGO DEPOIS                           ║
║                                                                                ║
║  2. APP_ENV no container MUST match 'environment' na tabela app_settings     ║
║     SUPABASE_PROJECT_REF no container MUST match na tabela app_settings      ║
║     Mismatch = /health/deep retorna CRITICAL = DEPLOY FALHA                  ║
║                                                                                ║
║  3. QUALQUER falha em /health/deep = ROLLBACK IMEDIATO                       ║
║     Não espere estabilizar. Não tente "depois eu vejo". ROLLBACK NOW.        ║
║                                                                                ║
║  4. Scheduler MUST ser 1 instância (sem autoscale)                           ║
║     Múltiplas instâncias = jobs duplicados = CAOS                            ║
║                                                                                ║
║  5. Sempre aplicar migrations manualmente ANTES de fazer merge do código     ║
║     Verificar /health/schema para confirmar versão correta                   ║
║                                                                                ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

---

## Deployment Architecture

### Production Environment

| Component | Configuration | Critical Note |
|-----------|---------------|---------------|
| **Platform** | Railway (remarkable-communication project) | |
| **Services** | 3 distinct services | Each with own RUN_MODE |
| **julia-api** | RUN_MODE=api | Uvicorn FastAPI server |
| **julia-worker** | RUN_MODE=worker | ARQ message queue consumer |
| **julia-scheduler** | RUN_MODE=scheduler | APScheduler cron jobs |
| **Environment** | production | AUTO-DEPLOY from main branch |
| **Auto-scaling** | API and Worker only | **Scheduler: 1 instance, NO autoscale** |

### Hard Guards (Environment Validation)

The system prevents accidental deployment to wrong environment through hard guards:

| Guard | Source | Validation |
|-------|--------|-----------|
| APP_ENV | Railway variable | Must equal `environment` in app_settings table |
| SUPABASE_PROJECT_REF | Railway variable | Must equal `supabase_project_ref` in app_settings table |
| Validation Point | /health/deep endpoint | Runs at startup and every health check |

**If guards fail:** /health/deep returns HTTP 503 CRITICAL and deployment fails.

---

## Health Checks

### Health Endpoint Reference

All health endpoints return JSON with structured response. Use for monitoring and CI/CD validation.

#### /health (Liveness Probe)

Purpose: Basic liveness check
Response: Always HTTP 200 if application is running
Use case: Kubernetes/container orchestration
Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health
```

#### /health/ready (Readiness Probe)

Purpose: Check if service can accept requests
Checks: Redis connection
Response: HTTP 200 if ready, HTTP 503 if not
Use case: Load balancer routing
Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health/ready
```

#### /health/deep (Comprehensive Health Check)

**CRITICAL:** Use this for deployment validation.

Checks performed (in order):
1. Redis ping and connectivity
2. Supabase connection
3. Critical tables exist (clientes, conversations, interacoes, job_executions)
4. Critical views exist (metricas_conversa, avaliacoes_qualidade)
5. Schema version matches expected migration level
6. Hard guard validation (APP_ENV and SUPABASE_PROJECT_REF)

Response on success: HTTP 200 with full status
Response on failure: HTTP 503 with detailed error listing

Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health/deep | jq '.'
```

Expected successful response structure:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-09T12:34:56Z",
  "environment": "production",
  "project_ref": "jyqgbzhqavgpxqacduoi",
  "redis": {"status": "connected"},
  "supabase": {"status": "connected"},
  "tables": {"status": "all_exist"},
  "views": {"status": "all_exist"},
  "migrations": {
    "current_version": "X",
    "status": "up_to_date"
  }
}
```

#### /health/schema (Migration Debug)

Purpose: Debug migration and schema version info
Response: HTTP 200 with migration history
Use case: Troubleshooting schema mismatches
Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health/schema | jq '.'
```

#### /health/rate (Rate Limiting Status)

Purpose: Check current rate limit usage
Response: HTTP 200 with usage statistics per namespace
Use case: Monitor if approaching limits
Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health/rate | jq '.'
```

#### /health/circuit (Circuit Breaker Status)

Purpose: Check circuit breaker states
Response: HTTP 200 with status of all protected services
Use case: Detect cascading failures
Copy-pasteable:
```bash
curl -s https://whats-agents-production.up.railway.app/health/circuit | jq '.'
```

---

## Migration Flow (CRITICAL ORDER)

### Safe Pattern: MIGRATION FIRST, CODE SECOND

This prevents the catastrophic scenario where code depends on schema that doesn't exist yet.

### Step-by-Step Checklist

```
[ ] 1. DEVELOPMENT: Create migration locally
         - File: migrations/YYYYMMDD_description.sql
         - Validate SQL syntax locally
         - Test on development database first

[ ] 2. STAGING: Test migration on staging Supabase project
         - Run full integration tests with new schema
         - Verify no unexpected side effects
         - Check performance of new indices/constraints

[ ] 3. PRODUCTION: Apply migration MANUALLY to prod Supabase
         - DO NOT use auto-apply during deployment
         - Use Supabase SQL Editor or MCP tool
         - Verify successful execution
         - Note exact timestamp of application

[ ] 4. VALIDATION: Verify /health/schema on production
         - Call /health/schema endpoint
         - Confirm migration version matches expectation
         - Check schema_version in app_settings table

[ ] 5. CODE: Create PR with code that depends on migration
         - Reference migration in PR description
         - Mention that migration already applied to prod
         - Code review should verify this dependency

[ ] 6. CI: All tests must pass
         - Unit tests with schema mocks
         - Integration tests with staging schema
         - Type checking and linting

[ ] 7. MERGE: Merge PR to main
         - CI must pass before merge
         - Branch protection requires PR

[ ] 8. DEPLOY: Automatic deployment triggers
         - Railway auto-deploys from main
         - Monitor deployment in Railway Dashboard
         - Wait for /health/deep to pass

[ ] 9. VALIDATION: Final health check
         - Call /health/deep endpoint
         - Confirm HTTP 200 response
         - Review logs for any errors
```

### Why This Order Matters

**WRONG order (code first, migration after):**
1. Code merged and deployed
2. App starts and tries to access new table/view
3. Table doesn't exist → application crashes
4. You panic and apply migration manually
5. Restart container
6. Window of downtime while debugging and fixing

**CORRECT order (migration first, code second):**
1. Database schema ready before code deployment
2. Code deployed and immediately finds schema it expects
3. No validation errors in /health/deep
4. Zero downtime, zero risk

### What "Apply Migration Manually" Means

Use one of these methods:

**Method 1: Supabase SQL Editor (Easiest)**
```
1. Go to https://app.supabase.com
2. Select project 'jyqgbzhqavgpxqacduoi'
3. SQL Editor
4. New Query
5. Paste migration SQL
6. Run (verify for syntax before executing!)
7. Confirm "completed successfully"
```

**Method 2: MCP Tool (Fastest)**
```bash
mcp__supabase__apply_migration --sql "$(cat migrations/YYYYMMDD_description.sql)"
```

**Method 3: psql directly (Advanced)**
```bash
psql postgresql://user:pass@host/db < migrations/YYYYMMDD_description.sql
```

### Common Mistakes and How to Avoid Them

| Mistake | Why It Happens | How to Avoid |
|---------|----------------|--------------|
| Merging code before migration applies | Developer assumes migration is done | Checklist step 3 is mandatory before step 5 |
| Applying migration after deploy | "I'll just do it quickly later" | Apply before opening PR |
| Forgetting to update app_settings version | Manual step is easy to forget | Add to checklist |
| Using wrong Supabase project | Multiple projects in account | Copy-paste project ref from .env |
| Migration in wrong file (old PR) | Conflicting migration files | Use timestamp in filename |

---

## Deployment Procedures

### Normal Deployment Flow

```
Feature branch → Commit → PR → CI pipeline → Merge → Auto-deploy → Health check
```

Detailed steps:

```bash
# 1. Feature branch (already created from main)
git checkout feature/your-feature

# 2. Make changes and commit
git add .
git commit -m "feature: description"

# 3. Push branch
git push origin feature/your-feature

# 4. Create PR on GitHub
# - Set base to 'main'
# - Add description and testing instructions
# - Link any related issues
# - Request reviewers

# 5. CI Pipeline Runs Automatically
# - Lint & Type Check status
# - Run Tests status
# - Build Docker Image status
# - Must ALL pass before merge allowed

# 6. Code Review (Required by branch protection)
# - At least one approval needed
# - Reviewers check logic and safety

# 7. Merge PR
# - GitHub squash/rebase/merge (use project standard)
# - Delete feature branch

# 8. Automatic Deployment
# - Railway detects push to main
# - Pulls latest code
# - Builds container
# - Deploys to production

# 9. Monitor Deployment
railway status
railway logs -f  # Stream logs during deploy

# 10. Validate Health
curl -s https://whats-agents-production.up.railway.app/health/deep | jq '.'
# Response must be HTTP 200, status "healthy"
```

**Expected time:** ~5-10 minutes from merge to full deployment

### Manual Deployment (Emergency)

Use only if automatic deployment fails.

**Option 1: Via Railway CLI**

```bash
# Login to Railway
railway login

# Ensure you're in correct project directory
pwd
# Should be: /Users/rafaelpivovar/Documents/Projetos/whatsapp-api

# Deploy current main branch
railway up

# Monitor logs
railway logs -f
```

**Option 2: Re-trigger GitHub Action**

```bash
# Via GitHub CLI
gh workflow run ci.yml --ref main

# Monitor online: https://github.com/rafa77-tech/whatsapp-api/actions
```

### Rollback Procedures

**Scenario:** Deploy is bad, /health/deep fails, or critical errors in logs

**Rollback Steps:**

```bash
# 1. Confirm current deployment status
railway status

# 2. View deployment history (last 10)
railway logs --deployment

# 3. Find the last STABLE deployment
# Look for timestamp and status before the bad one

# 4. In Railway Dashboard (UI method - safest)
# a. Go to https://dashboard.railway.app
# b. Select project 'remarkable-communication'
# c. Select service 'whats-agents'
# d. Click 'Deployments' tab
# e. Find last stable deployment in list
# f. Click three-dots menu → 'Redeploy'
# g. Confirm (this will roll back code)

# 5. Monitor logs after redeploy
railway logs -f

# 6. Validate health after redeploy
curl -s https://whats-agents-production.up.railway.app/health/deep | jq '.'

# 7. If still broken, escalate to team lead
```

**Do NOT:**
- Force push to main (requires admin override)
- Modify production variables during incident
- Skip health check validation
- Rollback more than once without investigation

**After Rollback:**
1. Root cause analysis required before re-deploying
2. Document what went wrong
3. Add preventive test case to CI
4. Discuss in team retrospective

---

## Incident Response Scenarios

### Scenario 1: App Not Responding (HTTP Timeout)

**Symptoms:**
- Requests to /health timeout
- Chatwoot reports "service unavailable"
- Railway logs not appearing

**Diagnosis:**

```bash
# Step 1: Check deployment status
railway status

# Step 2: Check recent logs (last 50 lines)
railway logs -n 50

# Look for:
# - "Application startup failed"
# - "CRITICAL" errors
# - "Connection refused" for Redis/Supabase
```

**Resolution:**

```bash
# If recent deployment is the culprit:
# 1. Rollback (see Rollback Procedures above)

# If Redis is down:
# 1. Go to Railway Dashboard
# 2. Check Redis service status
# 3. If Red/Error: select service → click Restart

# If app crashed silently:
# 1. Restart container
railway restart

# 2. Monitor logs
railway logs -f

# 3. Validate health (wait 30-60 seconds)
sleep 30
curl -s https://whats-agents-production.up.railway.app/health/deep
```

---

### Scenario 2: /health/deep Returns 503 CRITICAL

**Symptoms:**
- /health/deep returns HTTP 503
- Status shows "CRITICAL"
- Deployment fails at health check stage

**Check what failed:**

```bash
curl -s https://whats-agents-production.up.railway.app/health/deep | jq '.'

# Look in response for failures in:
# - redis: {status: "error"}
# - supabase: {status: "error"}
# - hard_guards: {status: "mismatch"}
# - tables: {missing: ["table_name"]}
# - migrations: {status: "outdated"}
```

**Fix by Category:**

**Case 1: Redis Connection Error**
```bash
# Check Redis is running
railway logs -n 50 | grep -i redis

# Restart Redis service in Railway Dashboard
# Then restart API service
railway restart

# Re-check health
curl -s https://whats-agents-production.up.railway.app/health/deep
```

**Case 2: Supabase Connection Error**
```bash
# Verify variables are set correctly
echo $SUPABASE_URL
echo $SUPABASE_PROJECT_REF

# Check Supabase status page: https://status.supabase.com
# If Supabase is down, wait for recovery
# If variables wrong, update in Railway Dashboard and redeploy

# To redeploy with new variables:
railway up
```

**Case 3: Hard Guard Mismatch (Environment)**
```bash
# This means APP_ENV variable doesn't match database value
# Find current APP_ENV in Railway Variables
# APP_ENV=production (must match)

# Check database value:
# Go to Supabase SQL Editor and run:
SELECT key, value FROM app_settings WHERE key IN ('environment', 'supabase_project_ref');

# Both must exist and match Railway variables
# If missing, insert them:
INSERT INTO app_settings (key, value, description) VALUES
  ('environment', 'production', 'Environment marker'),
  ('supabase_project_ref', 'jyqgbzhqavgpxqacduoi', 'Project reference')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

# Restart container:
railway restart
```

**Case 4: Migration Outdated / Schema Mismatch**
```bash
# Check what version we're at:
curl -s https://whats-agents-production.up.railway.app/health/schema | jq '.current_version'

# Check what migrations exist locally:
ls -lah migrations/ | grep "\.sql"

# Check what's been applied to Supabase:
SELECT version, description, installed_on FROM public._migrations ORDER BY version DESC;

# If there's a gap:
# 1. Get migration file from migrations/ directory
# 2. Apply it manually to Supabase via SQL Editor
# 3. Verify /health/schema shows new version
# 4. Restart container
railway restart

# Re-check health
curl -s https://whats-agents-production.up.railway.app/health/deep
```

**Case 5: Table or View Missing**
```bash
# Check response shows which table/view is missing
# Example response: {tables: {missing: ["metricas_conversa"]}}

# Check if it's a view (might need to be created):
SELECT COUNT(*) FROM information_schema.views
WHERE table_name = 'metricas_conversa';

# If result is 0, the view doesn't exist
# This means a migration didn't apply correctly

# Solution: Manually create the view from migrations
# 1. Find migration that creates this view
# 2. Get the CREATE VIEW statement
# 3. Run it in Supabase SQL Editor
# 4. Restart API
railway restart

# 5. Re-check health
curl -s https://whats-agents-production.up.railway.app/health/deep
```

---

### Scenario 3: Julia Paused or Not Responding

**Symptoms:**
- Médicos report no response from Julia
- Messages queue up in Chatwoot
- Conversations show no new messages from Julia

**Check Status:**

```bash
# Check julia_status table
SELECT * FROM public.julia_status ORDER BY created_at DESC LIMIT 5;

# Look at status column:
# - 'ativo' = working normally
# - 'pausado' = manually paused
# - 'error' = error state
```

**If Status is 'pausado':**

```bash
# This was manually paused (emergency pause)
# Check the reason:
SELECT motivo, alterado_via, created_at FROM julia_status
WHERE status = 'pausado' ORDER BY created_at DESC LIMIT 1;

# Resume Julia:
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operacao normal', 'manual');

# Verify:
SELECT status FROM julia_status ORDER BY created_at DESC LIMIT 1;
```

**If Status is 'ativo' but no responses:**

```bash
# Check if there are messages in queue
SELECT COUNT(*) as fila_count FROM public.fila_mensagens
WHERE processada = false AND created_at > NOW() - INTERVAL '5 minutes';

# Check worker logs
railway logs -n 100 | grep -i "worker\|fila\|error"

# Check scheduler logs
railway logs -n 100 | grep -i "scheduler\|job\|cron"

# Check if messages are being processed
SELECT COUNT(*) as processadas FROM public.fila_mensagens
WHERE processada = true AND updated_at > NOW() - INTERVAL '5 minutes';

# If fila is growing but not processing, worker might be stuck
# Restart worker service:
railway restart

# Monitor worker logs:
railway logs -f | grep -i "fila\|worker"
```

---

### Scenario 4: High Latency or Slow Responses

**Symptoms:**
- API responses taking > 30 seconds
- Timeout errors in Chatwoot integration
- Circuit breaker errors in logs

**Diagnosis:**

```bash
# Check what's slow
curl -s https://whats-agents-production.up.railway.app/health/rate | jq '.latency'

# Check CPU and memory usage in Railway Dashboard
# - High CPU: queries are slow or inefficient
# - High Memory: potential memory leak

# Check database query performance
SELECT query, mean_time, max_time, calls FROM pg_stat_statements
ORDER BY mean_time DESC LIMIT 10;

# Look for:
# - Queries with high mean_time (> 1000ms)
# - Queries called many times with high total time
# - Missing indices
```

**Quick Fixes:**

```bash
# 1. Restart API service (might clear caches/buffers)
railway restart

# 2. Check if specific endpoint is slow
# Time a request:
time curl -s https://whats-agents-production.up.railway.app/health

# 3. If still slow, scale up temporarily
# Go to Railway Dashboard → Service → Settings → RAM
# Increase from default to 2GB temporarily
# Monitor if response time improves

# 4. Check for N+1 queries in code review
# Look at recent deployments for query optimization

# 5. Clear caches if applicable
# Some services use Redis for caching:
redis-cli FLUSHDB  # CAUTION: only if you understand impact
```

---

### Scenario 5: Integration with External Services Broken

**Symptoms:**
- Chatwoot integration failing
- Evolution API returning errors
- Supabase queries failing
- Slack notifications not sending

**Check Integration Health:**

```bash
# All integrations tested via circuit breaker status
curl -s https://whats-agents-production.up.railway.app/health/circuit | jq '.integrations'

# Response shows circuit state:
# - "closed" = working
# - "open" = failing (requests will be rejected)
# - "half_open" = recovering

# Check logs for specific integration errors
railway logs -n 200 | grep -i "evolution\|chatwoot\|supabase\|slack"
```

**Troubleshoot by Integration:**

**Evolution API:**
```bash
# Check credentials and URL
echo "EVOLUTION_API_URL: $EVOLUTION_API_URL"
echo "EVOLUTION_API_KEY: [redacted]"

# Verify in Railway variables (don't print key):
# EVOLUTION_API_URL should be http://localhost:8080 (self-hosted)
# EVOLUTION_API_KEY should be valid

# Check if Evolution service is running (if self-hosted):
# curl http://localhost:8080/health

# In logs, look for:
railway logs -f | grep -i "evolution"
```

**Chatwoot:**
```bash
# Check credentials
echo "CHATWOOT_API_URL: $CHATWOOT_API_URL"
# Should be something like: http://localhost:3000 or production URL

# Check contact sync logs
railway logs -f | grep -i "chatwoot"

# Verify contact exists in Chatwoot
# Go to Chatwoot UI and search for contact
```

**Supabase:**
```bash
# Check connection
curl -s https://whats-agents-production.up.railway.app/health/deep | jq '.supabase'

# Should show: {status: "connected"}

# If failed, check:
# 1. SUPABASE_URL is correct
# 2. SUPABASE_SERVICE_KEY is valid (hasn't expired)
# 3. Supabase project is not paused
# 4. Internet connectivity is OK

# To verify credentials work:
curl -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  $SUPABASE_URL/rest/v1/app_settings?limit=1
# Should return JSON, not 401 Unauthorized
```

**Slack:**
```bash
# Check credentials
echo "SLACK_BOT_TOKEN: [redacted]"

# Check if Slack app is installed in workspace
# Go to https://api.slack.com/apps and find app

# Check token scopes are correct:
# - chat:write
# - channels:read
# - groups:read
# - users:read

# Test webhook:
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from Runbook"}' \
  $SLACK_WEBHOOK_URL
```

---

## Emergency Procedures

### Emergency Pause Julia (All Conversations)

Use only in critical situations (data corruption, security breach, mass spam, etc).

```bash
# Connect to Supabase
# Go to SQL Editor
# Run:

INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Emergência - pausado manualmente', 'manual');

# Verify pause took effect (might take up to 10 seconds):
SELECT status FROM julia_status ORDER BY created_at DESC LIMIT 1;

# Should return: pausado

# Julia will stop responding to ALL conversations
# Messages will queue in fila_mensagens but won't be processed
```

**Side effects:**
- All conversations show "no response" to médicos
- Messages pile up in queue
- Scheduler still runs but jobs that depend on Julia status will skip
- No messages sent until resumed

**To Resume:**

```bash
# After fixing issue, run:

INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('ativo', 'Retomando operacao', 'manual');

# Queue will start processing again
# This might spike CPU as catching up on backlog
```

### Emergency: Kill Long-Running Worker Jobs

If worker is stuck processing a job (hangs > 30 minutes):

```bash
# Check what job is running
SELECT job_id, job_name, started_at, status FROM job_executions
WHERE status = 'executando' AND started_at < NOW() - INTERVAL '30 minutes';

# Option 1: Just restart worker (kills all jobs)
railway restart

# Option 2: Kill specific job in database (advanced)
UPDATE job_executions
SET status = 'falha', ended_at = NOW()
WHERE job_id = 'xxxxx-xxxxx-xxxxx' AND status = 'executando';

# Monitor logs:
railway logs -f
```

### Emergency: Clear Circuit Breaker Trips

If a service integration is tripped and in "open" state, manually reset:

```bash
# Check circuit state
curl -s https://whats-agents-production.up.railway.app/health/circuit | jq '.integrations'

# To reset circuit (if available in app):
# Usually circuits auto-reset after cool-down period
# If not, restart API:
railway restart

# After restart, circuit returns to "closed" state
```

---

## Secrets Management

### Production Secrets Location

All secrets stored in Railway environment variables, NOT in code or .env files.

| Secret Name | Value Type | Frequency | Provider | Location |
|-------------|-----------|-----------|----------|----------|
| SUPABASE_URL | Database URL | Static | Supabase | Production project settings |
| SUPABASE_SERVICE_KEY | API key | 90 days | Supabase | Production project settings |
| ANTHROPIC_API_KEY | API key | 90 days | Anthropic console | https://console.anthropic.com |
| EVOLUTION_API_URL | Base URL | Static | Self-hosted / Evolution | Admin console |
| EVOLUTION_API_KEY | API key | 90 days | Evolution | Admin console |
| SLACK_BOT_TOKEN | OAuth token | When compromised | Slack | https://api.slack.com/apps |
| SLACK_WEBHOOK_URL | Webhook URL | When compromised | Slack | https://api.slack.com/apps |
| VOYAGE_API_KEY | API key | 90 days | Voyage AI | https://dash.voyageai.com |
| GOOGLE_SERVICE_ACCOUNT | JSON credentials | 180 days | Google Cloud | https://console.cloud.google.com |
| REDIS_URL | Connection string | Auto-managed | Railway | Auto-injected by Railway |
| APP_ENV | String | Static | Code | "production" |
| SUPABASE_PROJECT_REF | String | Static | Code | "jyqgbzhqavgpxqacduoi" |

### Secret Rotation Procedure

**Prerequisites:**
- Access to Railway Dashboard
- Access to secret provider (Anthropic, Supabase, etc)
- 30 minutes availability
- Verified non-production environment to test first

**Rotation Checklist (Using ANTHROPIC_API_KEY as example):**

```
[ ] 1. LOGIN TO PROVIDER
      Go to https://console.anthropic.com
      Navigate to API keys section
      Verify current key exists and is active

[ ] 2. CREATE NEW KEY
      Click "Create new key"
      Copy immediately (appears once)
      Store temporarily in secure location (1password, etc)
      Note timestamp and copy to clipboard

[ ] 3. UPDATE STAGING FIRST (optional but recommended)
      Go to Railway Dashboard
      Select staging service if exists
      Variables → Edit
      ANTHROPIC_API_KEY = [paste new key]
      Save (auto-redeploys)
      Wait 30 seconds for deploy
      Test: curl /health/deep
      Should return HTTP 200

[ ] 4. UPDATE PRODUCTION
      Go to Railway Dashboard → remarkable-communication → whats-agents
      Variables → ANTHROPIC_API_KEY
      Delete old value
      Paste new value
      Save (auto-redeploys)
      Note: Railway auto-deploys when variable changes

[ ] 5. MONITOR DEPLOYMENT
      Click Deployments tab
      Watch for new deployment starting
      Click to view logs
      Look for startup messages:
         - "Application startup complete"
         - No "401 Unauthorized" errors
         - No "Invalid API key" errors

[ ] 6. VALIDATE HEALTH (wait 60 seconds after deploy finishes)
      curl -s https://whats-agents-production.up.railway.app/health/deep
      Response must be HTTP 200
      If 503, check logs:
      railway logs -n 50 | grep -i "auth\|key\|anthropic"

[ ] 7. FUNCTIONAL TEST
      Send a test message to Julia via WhatsApp
      Verify Julia responds
      Check logs for no auth errors:
      railway logs -f | grep -i "anthropic\|error"

[ ] 8. REVOKE OLD KEY (wait 24 hours of stability first)
      Return to https://console.anthropic.com
      Find old key in list
      Click "Delete" or "Revoke"
      Confirm deletion
      Note: Cannot be undone

[ ] 9. DOCUMENT
      Add to team wiki:
         - Date rotated
         - Which key was rotated
         - No issues encountered
         - Attestation of functional test
```

### Rotation Schedule

| Secret | Interval | Next Review | Owner | Status |
|--------|----------|------------|-------|--------|
| ANTHROPIC_API_KEY | 90 days | 2026-05-09 | Eng Lead | Last rotated: 2026-02-09 |
| SUPABASE_SERVICE_KEY | 90 days | 2026-05-09 | Eng Lead | Last rotated: 2026-02-09 |
| EVOLUTION_API_KEY | 90 days | 2026-05-09 | Ops Lead | Last rotated: 2026-02-09 |
| VOYAGE_API_KEY | 90 days | 2026-05-09 | Eng Lead | Last rotated: 2026-02-09 |
| GOOGLE_SERVICE_ACCOUNT | 180 days | 2026-08-09 | Cloud Eng | Last rotated: 2026-02-09 |
| SLACK_BOT_TOKEN | On demand | As needed | DevOps | Rotated if compromised |

### Troubleshooting Secret Rotation

**Problem: "Invalid API Key" after rotation**

```bash
# Check for common mistakes:
# 1. Key contains leading/trailing spaces?
#    Go to Railway → Variables → Check value carefully
#    Copy-paste again if unsure

# 2. Key was actually revoked already?
#    Check provider console (Anthropic, Supabase, etc)
#    If revoked, create new key

# 3. Environment variable name is wrong?
#    Check that variable name matches code expectations
#    Should be: ANTHROPIC_API_KEY (not anthropic_key, etc)

# 4. Re-deploy manually
railway up

# 5. Check logs immediately after restart
railway logs -f | head -50
```

**Problem: Service still using old key (cached)**

```bash
# This shouldn't happen (Railway auto-restarts on var change)
# But if it does:

# Manual restart:
railway restart

# Monitor logs to confirm old key is gone:
railway logs -f | grep -i "api.*key\|auth"
```

---

## Database Maintenance

### High-Volume Tables

These tables grow rapidly and require regular maintenance:

| Table | Rows/Day | Weekly | Monthly | Notes |
|-------|----------|--------|---------|-------|
| job_executions | ~10,000 | VACUUM ANALYZE | Check bloat | Historical, can archive old |
| interacoes | ~1,000 | VACUUM | Check indices | Conversation interactions |
| business_events | ~5,000 | VACUUM ANALYZE | Check bloat | Analytics events |
| mensagens_grupo | ~2,000 | VACUUM | Check indices | Group message log |
| health_incidents | ~10/week | Monthly | Check bloat | System health logs |
| fila_mensagens | Variable | After purge | Monthly | Message queue, purges processed |

### Weekly Maintenance (Every Monday 2 AM UTC)

```sql
-- Execute in Supabase SQL Editor

-- 1. Vacuum high-volume tables
VACUUM ANALYZE job_executions;
VACUUM ANALYZE interacoes;
VACUUM ANALYZE business_events;
VACUUM ANALYZE mensagens_grupo;

-- 2. Check for missing indices on foreign keys
SELECT
  t.tablename,
  c.column_name,
  CASE WHEN ix.indexname IS NULL THEN 'MISSING' ELSE 'OK' END as status
FROM information_schema.table_constraints tc
JOIN information_schema.tables t ON tc.table_name = t.tablename
JOIN information_schema.columns c ON c.table_name = t.tablename AND c.column_name LIKE '%_id'
LEFT JOIN pg_indexes ix ON ix.tablename = t.tablename
  AND ix.indexname LIKE '%' || c.column_name || '%'
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND t.schemaname = 'public'
ORDER BY t.tablename;

-- 3. Check table sizes
SELECT
  relname as tabela,
  pg_size_pretty(pg_total_relation_size(relid)) as tamanho_total
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;

-- 4. Identify dead tuples that should be vacuumed
SELECT
  relname as tabela,
  n_live_tup as linhas_vivas,
  n_dead_tup as linhas_mortas,
  ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) as perc_mortas,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
WHERE n_dead_tup > 100
  AND schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

### Monthly Maintenance (First Monday of month, 2 AM UTC)

```sql
-- Additional deep maintenance beyond weekly

-- 1. Reindex large tables (safe in production with CONCURRENTLY)
-- Check which indices need rebuilding:
SELECT
  relname as tabela,
  indexrelname as indice,
  idx_scan as usos,
  pg_size_pretty(pg_relation_size(indexrelid)) as tamanho
FROM pg_stat_user_indexes
WHERE idx_scan < 10  -- Used fewer than 10 times
  AND pg_relation_size(indexrelid) > 1000000  -- Larger than 1MB
  AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 2. Analyze query performance
-- Look for slow queries that might benefit from new indices
SELECT
  query,
  calls,
  mean_time,
  max_time,
  ROUND(total_time / calls) as avg_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
  AND mean_time > 100  -- Queries averaging > 100ms
ORDER BY total_time DESC
LIMIT 20;

-- 3. Archive old job executions (optional, only if tables are very large)
-- This keeps the table small and queries fast
-- Create an archive table first:
-- CREATE TABLE job_executions_archive AS
--   SELECT * FROM job_executions WHERE created_at < NOW() - INTERVAL '90 days';
-- Then delete from main table:
-- DELETE FROM job_executions WHERE created_at < NOW() - INTERVAL '90 days';
```

### Creating Missing Indices (Critical)

PostgreSQL does NOT automatically create indices for foreign keys. Check weekly and add as needed.

```sql
-- Safe way to add index without blocking queries:
CREATE INDEX CONCURRENTLY idx_table_fk_column
ON table_name(foreign_key_column);

-- Example for known missing indices:
CREATE INDEX CONCURRENTLY idx_interacoes_cliente_id ON interacoes(cliente_id);
CREATE INDEX CONCURRENTLY idx_interacoes_conversa_id ON interacoes(conversa_id);
CREATE INDEX CONCURRENTLY idx_job_executions_job_name ON job_executions(job_name);
CREATE INDEX CONCURRENTLY idx_campanhas_criado_por ON campanhas(criado_por);
CREATE INDEX CONCURRENTLY idx_envios_campanha_id ON envios(campanha_id);
CREATE INDEX CONCURRENTLY idx_mensagens_grupo_grupo_id ON mensagens_grupo(grupo_id);
CREATE INDEX CONCURRENTLY idx_conversas_grupo_grupo_id ON conversas_grupo(grupo_id);
CREATE INDEX CONCURRENTLY idx_business_events_medico_id ON business_events(medico_id);
CREATE INDEX CONCURRENTLY idx_business_events_conversa_id ON business_events(conversa_id);

-- Verify index was created:
SELECT indexname FROM pg_indexes WHERE tablename = 'interacoes';
```

### When to VACUUM vs VACUUM FULL

| Scenario | Command | Blocking | Use Case |
|----------|---------|----------|----------|
| Regular maintenance | VACUUM | No | Weekly cleanup (safe in production) |
| Regular + statistics | VACUUM ANALYZE | No | After large imports or deletes |
| Reclaim disk space | VACUUM FULL | **YES** | Only during low-traffic windows, NOT production |
| Emergency bloat | VACUUM FULL ANALYZE | **YES** | Only if disk is critical, requires downtime |

---

## Workers and Scheduled Jobs

### Worker Services

Three independent worker processes handle different tasks:

**julia-api** (RUN_MODE=api)
- FastAPI HTTP server
- Handles webhook from Evolution API
- Handles HTTP endpoints
- Auto-scales 1-N instances

**julia-worker** (RUN_MODE=worker)
- ARQ message queue consumer
- Processes jobs from fila_mensagens queue
- Handles async processing of messages
- Auto-scales 1-N instances

**julia-scheduler** (RUN_MODE=scheduler)
- APScheduler cron jobs
- Scheduled tasks defined in app/workers/scheduler.py
- **MUST BE 1 INSTANCE ONLY** (no autoscale)
- Duplicates cause duplicate job execution

### Scheduled Jobs Reference

| Job | Frequency | Time | Purpose | If Fails |
|-----|-----------|------|---------|----------|
| processar-mensagens-agendadas | Every minute | Every :00 sec | Process queued messages | Messages delay |
| processar-campanhas-agendadas | Every minute | Every :00 sec | Process campaign sends | Campaign delays |
| verificar-alertas | Every 15 min | :00, :15, :30, :45 | Check alert conditions | Alerts late |
| avaliar-conversas-pendentes | Daily | 2:00 AM UTC | Grade pending conversations | Quality metrics late |
| processar-pausas-expiradas | Daily | 6:00 AM UTC | Handle paused conversation resumption | Pauses don't auto-clear |
| relatorio-diario | Daily | 8:00 AM UTC | Generate daily report | Daily report missing |
| processar-followups | Daily | 10:00 AM UTC | Send follow-up messages | Follow-ups don't send |
| sincronizar-briefing | Hourly | :00 every hour | Sync Julia briefing from Google Docs | Briefing stale |
| report-semanal | Weekly | Monday 9:00 AM | Generate weekly metrics report | Weekly report missing |
| atualizar-prompt-feedback | Weekly | Sunday 2:00 AM | Update prompts based on feedback | Prompts don't improve |
| Period reports | Daily | 10 AM, 1 PM, 5 PM, 8 PM | Period-based performance reports | Period reports missing |

### View Scheduled Jobs Status

```bash
# Check which jobs have run recently
SELECT
  job_name,
  status,
  started_at,
  ended_at,
  CASE WHEN status = 'sucesso' THEN 'OK' ELSE 'ERROR' END as status_display,
  ROUND(EXTRACT(EPOCH FROM (ended_at - started_at))::numeric, 2) as duracao_segundos
FROM job_executions
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC
LIMIT 50;

-- Check for jobs that are stuck (running > 30 min)
SELECT
  job_id,
  job_name,
  started_at,
  NOW() - started_at as tempo_decorrido
FROM job_executions
WHERE status = 'executando'
  AND started_at < NOW() - INTERVAL '30 minutes';

-- Check jobs with high failure rate
SELECT
  job_name,
  COUNT(*) as total_execucoes,
  SUM(CASE WHEN status = 'falha' THEN 1 ELSE 0 END) as falhas,
  ROUND(100 * SUM(CASE WHEN status = 'falha' THEN 1 ELSE 0 END) / COUNT(*), 2) as taxa_falha_perc
FROM job_executions
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY job_name
HAVING SUM(CASE WHEN status = 'falha' THEN 1 ELSE 0 END) > 0
ORDER BY taxa_falha_perc DESC;
```

### Kill Stuck Job

```bash
# If a job is stuck running > 30 minutes:

-- Option 1: Kill via database
UPDATE job_executions
SET status = 'falha',
    ended_at = NOW(),
    erro = 'Killed manually due to timeout'
WHERE job_id = 'XXXXX-XXXXX-XXXXX'
  AND status = 'executando';

-- Option 2: Kill worker and let job retry
railway restart  # Kills all running jobs

-- Monitor:
railway logs -f | grep -i "job\|scheduler"
```

---

## Contact and Escalation

### On-Call Rotation

| Role | Name | Phone | Email | GitHub |
|------|------|-------|-------|--------|
| Eng Lead | [Name] | [Phone] | [Email] | [Username] |
| DevOps Lead | [Name] | [Phone] | [Email] | [Username] |
| Database Admin | [Name] | [Phone] | [Email] | [Username] |
| Product Manager | [Name] | [Phone] | [Email] | [Username] |

**Fill in contact information in your team wiki**

### Escalation Path

```
Level 1: Service degradation (slow, partial failures)
  → On-call engineer (assess, try restart/rollback)
  → Time limit: 15 minutes to determine root cause

Level 2: Service down (total outage)
  → Eng Lead + DevOps Lead (in parallel)
  → Declare incident in #incidents Slack
  → Time limit: 5 minutes to start recovery
  → Communicate status every 10 minutes

Level 3: Data corruption or security issue
  → Escalate to CTO immediately
  → Pause Julia to prevent further damage
  → Do NOT attempt emergency patches
  → Preserve logs and database state for forensics

Critical Incident Protocol:
  1. Declare incident in #incidents: "CRITICAL INCIDENT: [brief description]"
  2. Set status page to degraded
  3. Notify customers of ETA (under-promise, over-deliver)
  4. Post updates every 10 minutes minimum
  5. Post RCA within 24 hours
```

### Runbook Updates

This document should be reviewed and updated:

- **Weekly**: During on-call transitions
- **Monthly**: After each incident
- **Quarterly**: Full review and drill

Last updated: 2026-02-09
Next review: 2026-02-16
