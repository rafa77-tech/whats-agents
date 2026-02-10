# Disaster Recovery - Recuperação de Desastres

Enterprise-grade disaster recovery procedures for Agente Julia production system.

---

## RTO/RPO Targets

| Component | RTO (Recovery Time) | RPO (Data Loss) | Criticality |
|-----------|---------------------|-----------------|-------------|
| **API Service** | < 5 minutes | 0 (stateless) | CRITICAL |
| **Worker Service** | < 10 minutes | < 1 minute | HIGH |
| **Scheduler Service** | < 15 minutes | < 5 minutes | HIGH |
| **Supabase Database** | < 30 minutes | < 15 minutes | CRITICAL |
| **Redis Cache** | < 5 minutes | Acceptable (cache) | MEDIUM |
| **Evolution API** | < 30 minutes | < 5 minutes | CRITICAL |
| **Chatwoot** | < 1 hour | < 30 minutes | LOW |

**Definições:**
- **RTO (Recovery Time Objective)**: Tempo máximo aceitável para restaurar serviço
- **RPO (Recovery Point Objective)**: Quantidade máxima aceitável de perda de dados
- **Criticality**: Impacto no negócio se componente falhar

---

## Backup Strategy

### 1. Supabase Database (PostgreSQL)

#### Backup Automático (Managed by Supabase)

Supabase realiza backups automáticos:

| Tipo | Frequência | Retenção | Configuração |
|------|------------|----------|--------------|
| Full Backup | Diário (2 AM UTC) | 7 dias (Free), 30 dias (Pro) | Automático |
| Point-in-Time Recovery (PITR) | Contínuo | 7 dias (Pro+) | Requer upgrade |
| WAL Archiving | Real-time | 7 dias | Automático (Pro+) |

**Verificar backups disponíveis:**

1. Acesse https://app.supabase.com
2. Selecione projeto `jyqgbzhqavgpxqacduoi`
3. Settings → Database → Backups
4. Verifique lista de backups disponíveis

**Limitações importantes:**
- Free tier: apenas 7 dias de retenção
- Backups não podem ser baixados diretamente (apenas restore in-place)
- PITR requer plano Pro ou superior

#### Backup Manual (pg_dump)

Para garantir controle total e retenção estendida, realizar backups manuais mensais.

**Procedimento:**

```bash
# 1. Obter connection string do Supabase
# Dashboard → Settings → Database → Connection String (Direct connection)
# Formato: postgresql://postgres:[password]@[host]:5432/postgres

# 2. Fazer dump completo (schema + dados)
pg_dump "postgresql://postgres:[password]@db.jyqgbzhqavgpxqacduoi.supabase.co:5432/postgres" \
  --format=custom \
  --file="backup-julia-$(date +%Y%m%d-%H%M%S).dump" \
  --verbose

# 3. Backup apenas schema (para versionamento)
pg_dump "postgresql://..." \
  --schema-only \
  --file="schema-julia-$(date +%Y%m%d).sql"

# 4. Backup apenas dados específicos (tabelas críticas)
pg_dump "postgresql://..." \
  --data-only \
  --table=clientes \
  --table=conversations \
  --table=interacoes \
  --table=vagas \
  --file="dados-criticos-$(date +%Y%m%d).dump"

# 5. Comprimir para storage
gzip backup-julia-*.dump

# 6. Upload para storage seguro (S3, Google Cloud Storage, etc)
# Exemplo com AWS CLI:
aws s3 cp backup-julia-*.dump.gz s3://julia-backups/monthly/

# 7. Verificar integridade
gzip -t backup-julia-*.dump.gz
echo $?  # Deve retornar 0
```

**Agenda recomendada:**
- Diário: Supabase automático (7 dias)
- Semanal: pg_dump manual (4 semanas de retenção)
- Mensal: pg_dump completo + upload para storage externo (12 meses de retenção)

#### Backup de Dados Específicos (Compliance/Auditoria)

```sql
-- Exportar dados de auditoria (últimos 90 dias)
COPY (
  SELECT * FROM business_events
  WHERE created_at > NOW() - INTERVAL '90 days'
) TO '/tmp/business_events_backup.csv' WITH CSV HEADER;

-- Exportar conversas completas (para análise pós-incidente)
COPY (
  SELECT c.*, i.mensagem, i.sender, i.timestamp
  FROM conversations c
  LEFT JOIN interacoes i ON i.conversa_id = c.id
  WHERE c.created_at > NOW() - INTERVAL '30 days'
  ORDER BY c.id, i.timestamp
) TO '/tmp/conversas_backup.csv' WITH CSV HEADER;

-- Exportar job executions (para análise de falhas)
COPY (
  SELECT * FROM job_executions
  WHERE created_at > NOW() - INTERVAL '30 days'
  ORDER BY created_at DESC
) TO '/tmp/jobs_backup.csv' WITH CSV HEADER;
```

### 2. Railway Services (Stateless)

Railway services são stateless - o código está no GitHub.

**Backup implícito:**
- Código versionado: GitHub (main branch)
- Variáveis de ambiente: Railway Dashboard (exportar manualmente)
- Configuração de serviços: railway.toml (se existir)

**Procedimento de backup de variáveis:**

```bash
# Via CLI (se disponível)
railway variables > railway-vars-backup-$(date +%Y%m%d).txt

# Via Dashboard (manual)
# 1. Railway Dashboard → Service → Variables
# 2. Copiar todas as variáveis para arquivo seguro
# 3. NUNCA commitar esse arquivo no Git
# 4. Armazenar em 1Password, Vault, ou similar
```

**Template de variáveis críticas para backup:**

```bash
# Backup manual em 2026-02-10
# IMPORTANTE: Arquivo sensível, não versionar

# Supabase
SUPABASE_URL=https://jyqgbzhqavgpxqacduoi.supabase.co
SUPABASE_SERVICE_KEY=[REDACTED]
SUPABASE_PROJECT_REF=jyqgbzhqavgpxqacduoi

# Anthropic
ANTHROPIC_API_KEY=[REDACTED]
LLM_MODEL=claude-3-5-haiku-20241022
LLM_MODEL_COMPLEX=claude-sonnet-4-20250514

# Evolution API
EVOLUTION_API_URL=[REDACTED]
EVOLUTION_API_KEY=[REDACTED]
EVOLUTION_INSTANCE=Revoluna

# Redis
REDIS_URL=[REDACTED - Railway auto-inject]

# Configuração crítica
APP_ENV=production
RUN_MODE=[api|worker|scheduler por serviço]
PILOT_MODE=false

# Voyage AI
VOYAGE_API_KEY=[REDACTED]

# Slack
SLACK_BOT_TOKEN=[REDACTED]
SLACK_WEBHOOK_URL=[REDACTED]

# JWT
JWT_SECRET_KEY=[REDACTED]

# CORS
CORS_ORIGINS=[production domains]
```

### 3. Redis (Cache - Acceptable Loss)

Redis é usado apenas para cache e rate limiting - perda de dados é aceitável.

**O que acontece se Redis for perdido:**
- Rate limits resetam (temporariamente mais permissivo)
- Cache de contexto é perdido (rebuild automático)
- Sessões Slack expiram (usuários devem reiniciar conversa)

**Backup (opcional):**

Redis em Railway possui snapshots automáticos, mas para compliance:

```bash
# Backup manual (se necessário)
redis-cli --rdb /tmp/redis-backup-$(date +%Y%m%d).rdb

# Ou via comando SAVE
redis-cli SAVE
```

**Não é recomendado investir em backup sofisticado de Redis** - melhor focar em Supabase.

### 4. Evolution API (WhatsApp)

Evolution API armazena:
- Sessões WhatsApp (auth tokens)
- Configuração de instâncias
- Webhooks configurados

**Backup:**

```bash
# Via API (exportar configuração de instância)
curl -X GET "http://localhost:8080/instance/fetchInstances" \
  -H "apikey: $EVOLUTION_API_KEY" \
  > evolution-instances-backup-$(date +%Y%m%d).json

# Backup de webhook config
curl -X GET "http://localhost:8080/webhook/find/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  > evolution-webhook-backup-$(date +%Y%m%d).json
```

**Dados persistentes (se self-hosted):**
- Evolution usa volume Docker para sessões
- Verificar `docker-compose.yml` para path do volume
- Fazer backup do volume: `docker cp evolution-api:/evolution/instances ./backup-instances/`

### 5. Chatwoot (Supervisão)

Chatwoot possui seu próprio PostgreSQL.

**Backup (se self-hosted):**

```bash
# Via docker compose
docker compose exec chatwoot-postgres pg_dump -U chatwoot chatwoot \
  > chatwoot-backup-$(date +%Y%m%d).sql

# Comprimir
gzip chatwoot-backup-*.sql
```

**Se usando Chatwoot Cloud (SaaS):**
- Backups gerenciados pela Chatwoot
- Exportar conversas manualmente se necessário (via API)

---

## Restore Procedures

### 1. Restaurar Supabase Database

#### Cenário A: Restore de Backup Automático (Supabase Dashboard)

**Quando usar:**
- Corrupção de dados nas últimas 7 dias
- Rollback de migration problemática
- Dados deletados acidentalmente

**Procedimento:**

```
[ ] 1. AVALIAR IMPACTO
      - Quantos dados serão perdidos? (verificar RPO)
      - Serviços precisam ser pausados durante restore?
      - Comunicar equipe e stakeholders

[ ] 2. PAUSAR JULIA (OPCIONAL MAS RECOMENDADO)
      - Evita writes durante restore
      - SQL: INSERT INTO julia_status (status, motivo) VALUES ('pausado', 'Restore em andamento');
      - Verificar: SELECT status FROM julia_status ORDER BY created_at DESC LIMIT 1;

[ ] 3. PAUSAR SERVIÇOS RAILWAY
      - Dashboard → cada serviço → Settings → "Pause"
      - Evita conflitos durante restore

[ ] 4. SUPABASE DASHBOARD
      - https://app.supabase.com
      - Projeto jyqgbzhqavgpxqacduoi
      - Settings → Database → Backups
      - Selecionar backup desejado
      - Click "Restore" (confirmar timestamp)

[ ] 5. AGUARDAR RESTORE (10-30 minutos dependendo do tamanho)
      - Supabase mostra progresso
      - NÃO interromper durante processo

[ ] 6. VALIDAR DADOS
      - Conectar via SQL Editor
      - SELECT COUNT(*) FROM clientes;
      - SELECT COUNT(*) FROM conversations;
      - SELECT MAX(created_at) FROM interacoes;  -- Verificar até que ponto foi restaurado

[ ] 7. RECRIAR DADOS PERDIDOS (se necessário)
      - Se RPO > 0, dados entre backup e incidente foram perdidos
      - Avaliar se é possível recriar manualmente
      - Documentar perda para post-mortem

[ ] 8. VALIDAR HEALTH
      - Unpause serviços Railway
      - curl https://whats-agents-production.up.railway.app/health/deep
      - Verificar HTTP 200 e status "healthy"

[ ] 9. RETOMAR JULIA
      - SQL: INSERT INTO julia_status (status, motivo) VALUES ('ativo', 'Restore concluído');

[ ] 10. MONITORAR POR 1 HORA
      - railway logs -f
      - Verificar se não há erros
      - Testar fluxo end-to-end (enviar mensagem teste)
```

#### Cenário B: Restore de Backup Manual (pg_dump)

**Quando usar:**
- Backup automático Supabase não disponível
- Restore para timestamp mais antigo que 7 dias
- Migração para novo projeto Supabase

**Procedimento:**

```bash
# 1. Download do backup
aws s3 cp s3://julia-backups/monthly/backup-julia-20260201.dump.gz .
gunzip backup-julia-20260201.dump.gz

# 2. Validar integridade do arquivo
file backup-julia-20260201.dump
# Deve mostrar: PostgreSQL custom database dump

# 3. CRITICAL: Criar novo projeto Supabase (ou usar staging)
# NUNCA restaurar diretamente sobre produção sem testar

# 4. Obter connection string do projeto destino
DEST_URL="postgresql://postgres:[password]@db.[new-project].supabase.co:5432/postgres"

# 5. Restore completo
pg_restore --verbose \
  --clean \
  --no-owner \
  --no-acl \
  --dbname="$DEST_URL" \
  backup-julia-20260201.dump

# 6. Verificar dados restaurados
psql "$DEST_URL" -c "SELECT COUNT(*) FROM clientes;"
psql "$DEST_URL" -c "SELECT COUNT(*) FROM conversations;"

# 7. Se validação OK, atualizar variáveis Railway para apontar para novo projeto
# Railway Dashboard → Variables
# SUPABASE_URL=[novo projeto]
# SUPABASE_SERVICE_KEY=[novo service key]
# SUPABASE_PROJECT_REF=[novo ref]

# 8. Deploy automático será triggered
# Validar /health/deep após deploy
```

#### Cenário C: Restore Seletivo (Apenas Algumas Tabelas)

**Quando usar:**
- Corrupção em tabela específica
- Restore de dados de teste que foram sobrescritos

**Procedimento:**

```bash
# 1. Listar conteúdo do backup
pg_restore --list backup-julia-20260201.dump | grep "TABLE DATA"

# 2. Restore apenas tabelas específicas
pg_restore --verbose \
  --table=clientes \
  --table=conversations \
  --dbname="$DEST_URL" \
  backup-julia-20260201.dump

# 3. Ou usando SQL dump
psql "$DEST_URL" < schema-julia-20260201.sql
```

### 2. Restaurar Railway Services

#### Cenário A: Rollback para Deploy Anterior

**Quando usar:**
- Deploy recente introduziu bug crítico
- Performance degradou após deploy
- /health/deep retorna CRITICAL

**Procedimento (via Dashboard - Recomendado):**

```
[ ] 1. IDENTIFICAR ÚLTIMO DEPLOY ESTÁVEL
      - Railway Dashboard → Service → Deployments
      - Listar deployments recentes
      - Identificar último com status "SUCCESS" antes do problema

[ ] 2. ROLLBACK
      - Click no deployment estável
      - Click "Redeploy" (ou ícone de três pontos → Redeploy)
      - Confirmar

[ ] 3. AGUARDAR REDEPLOY (2-5 minutos)
      - Railway mostra progresso
      - Aguardar status "Active"

[ ] 4. VALIDAR HEALTH
      - curl https://whats-agents-production.up.railway.app/health/deep
      - Verificar HTTP 200

[ ] 5. MONITORAR LOGS
      - railway logs -f
      - Verificar se erros anteriores sumiram

[ ] 6. COMUNICAR
      - Notificar equipe que rollback foi feito
      - Criar issue para investigar causa raiz
```

**Procedimento (via CLI):**

```bash
# 1. Ver histórico de deployments
railway logs --deployment

# 2. Não há comando direto de rollback via CLI
# Usar dashboard ou fazer redeploy do commit anterior

# 3. Redeploy de commit específico
git checkout [commit-hash-estável]
railway up
git checkout main
```

#### Cenário B: Recriar Serviço do Zero

**Quando usar:**
- Serviço corrompido/não responde
- Configuração Railway foi alterada incorretamente
- Último recurso quando rollback falha

**Procedimento:**

```
[ ] 1. BACKUP DE VARIÁVEIS
      - Railway Dashboard → Service → Variables
      - Copiar TODAS as variáveis para arquivo local seguro

[ ] 2. BACKUP DE CONFIGURAÇÃO
      - Settings → Anotar:
        - Região (us-west1, etc)
        - Start command
        - Healthcheck path
        - Resource limits (RAM, CPU)

[ ] 3. DELETAR SERVIÇO ANTIGO (CUIDADO!)
      - Service → Settings → "Delete Service"
      - Confirmar nome do serviço

[ ] 4. CRIAR NOVO SERVIÇO
      - Project → "New Service"
      - Conectar ao GitHub repo
      - Selecionar branch "main"
      - Definir RUN_MODE (api | worker | scheduler)

[ ] 5. RESTAURAR VARIÁVEIS
      - Colar todas as variáveis do backup
      - VERIFICAR: APP_ENV, SUPABASE_URL, SUPABASE_PROJECT_REF
      - Salvar

[ ] 6. CONFIGURAR SETTINGS
      - Start command: (deixar auto-detect ou especificar)
      - Healthcheck: /health
      - Resources: (restaurar limites anteriores)

[ ] 7. AGUARDAR PRIMEIRO DEPLOY
      - Railway detecta push e inicia build
      - Aguardar status "Active"

[ ] 8. VALIDAR COMPLETAMENTE
      - /health/deep
      - Testar endpoint principal
      - Verificar logs

[ ] 9. ATUALIZAR DNS/ENDPOINTS (se necessário)
      - Se domínio custom, reconfigurar
      - Se webhook, atualizar URL em Evolution/Chatwoot
```

### 3. Restaurar Redis

**Redis é efêmero - perda é aceitável.**

Se Redis falhar:

```
[ ] 1. VERIFICAR STATUS
      - Railway Dashboard → Redis service → Status

[ ] 2. SE "ERROR" OU "CRASHED"
      - Click "Restart"
      - Aguardar 30-60 segundos

[ ] 3. SE RESTART NÃO FUNCIONA
      - Deletar serviço Redis
      - Criar novo: Dashboard → "New Service" → Redis
      - Copiar nova REDIS_URL
      - Atualizar variável em API/Worker/Scheduler
      - Redeploy services

[ ] 4. VALIDAR
      - curl /health/ready (deve passar)
      - Verificar logs: "Connected to Redis"
```

**Não há necessidade de restore de dados** - cache será reconstruído automaticamente.

### 4. Restaurar Evolution API

#### Cenário A: Instância WhatsApp Desconectada

**Quando usar:**
- QR code expirou
- WhatsApp Web desconectou

**Procedimento:**

```bash
# 1. Verificar status da instância
curl -X GET "http://localhost:8080/instance/connectionState/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY"

# 2. Se retornar "close" ou "disconnected"
# Gerar novo QR code
curl -X GET "http://localhost:8080/instance/qrcode/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY"

# 3. Escanear com WhatsApp no celular
# WhatsApp → Aparelhos conectados → Conectar um aparelho

# 4. Validar reconexão
curl -X GET "http://localhost:8080/instance/connectionState/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY"
# Deve retornar "open"
```

#### Cenário B: Evolution API Não Responde

```bash
# 1. Se self-hosted (Docker)
docker compose logs evolution-api

# 2. Se container está travado
docker compose restart evolution-api

# 3. Se restart não funciona
docker compose down evolution-api
docker compose up -d evolution-api

# 4. Reconfigurar webhook (após restart)
curl -X POST "http://localhost:8080/webhook/set/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://whats-agents-production.up.railway.app/webhook/evolution",
    "webhook_by_events": false,
    "events": ["messages.upsert"]
  }'
```

#### Cenário C: Perda Total (Recriar Instância)

```bash
# 1. Deletar instância antiga
curl -X DELETE "http://localhost:8080/instance/delete/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY"

# 2. Criar nova instância
curl -X POST "http://localhost:8080/instance/create" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instanceName": "Revoluna",
    "qrcode": true
  }'

# 3. Conectar WhatsApp (escanear QR)
curl -X GET "http://localhost:8080/instance/qrcode/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY"

# 4. Configurar webhook
curl -X POST "http://localhost:8080/webhook/set/Revoluna" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://whats-agents-production.up.railway.app/webhook/evolution",
    "webhook_by_events": false,
    "events": ["messages.upsert"]
  }'

# 5. Atualizar tabela whatsapp_instances em Supabase
UPDATE whatsapp_instances
SET instance_name = 'Revoluna',
    status = 'ativa',
    updated_at = NOW()
WHERE id = '[instance-id]';
```

### 5. Restaurar Chatwoot

**Se self-hosted:**

```bash
# 1. Restore do PostgreSQL
docker compose exec chatwoot-postgres psql -U chatwoot chatwoot < chatwoot-backup-20260201.sql

# 2. Restart Chatwoot
docker compose restart chatwoot

# 3. Validar
curl http://localhost:3000/
# Deve retornar página de login
```

**Se Chatwoot Cloud (SaaS):**
- Contatar suporte Chatwoot
- Perda de dados aceitável (não é sistema crítico)

---

## Degraded Mode Operations

Modos de operação quando dependências falham.

### 1. Supabase Database Down

**Impacto:**
- Julia não pode processar novas mensagens
- Nenhum dado pode ser lido/escrito
- API retorna 503 em /health/deep

**Modo degradado:**

```
SERVIÇO TOTALMENTE INDISPONÍVEL

Não há modo degradado viável - Supabase é dependência crítica.

Ações:
1. Verificar status.supabase.com
2. Se incidente Supabase: aguardar resolução
3. Se problema local: restaurar de backup imediatamente
4. Comunicar downtime para stakeholders
5. Pausar Julia para evitar perda de mensagens
```

**Comunicação:**

```markdown
INCIDENT: Julia temporariamente indisponível

Status: Investigating
Component: Database (Supabase)
Impact: Nenhuma mensagem sendo processada
ETA: [atualizar a cada 15 minutos]

Ações:
- Mensagens recebidas via WhatsApp serão enfileiradas
- Processamento retomará automaticamente após resolução
- Nenhum dado será perdido

Próxima atualização: [timestamp]
```

### 2. Redis Down

**Impacto:**
- Rate limiting não funciona (risco de enviar muito rápido)
- Cache de contexto perdido (mais chamadas ao Supabase)
- Sessões Slack expiram

**Modo degradado:**

```python
# Código tem fallback automático

# Rate limiter (app/services/rate_limiter.py)
try:
    await redis.incr(key)
except RedisError:
    logger.warning("Redis down, rate limiting disabled")
    return True  # Allow all (temporary)

# Cache (app/services/cache.py)
try:
    cached = await redis.get(key)
except RedisError:
    logger.warning("Redis down, fetching from database")
    return await fetch_from_db()
```

**Ações:**

```
[ ] 1. MONITORAR RATE LIMITING
      - Verificar se mensagens não estão sendo enviadas rápido demais
      - railway logs -f | grep "rate_limit"

[ ] 2. RESTAURAR REDIS
      - Railway Dashboard → Redis → Restart
      - Ou criar novo serviço Redis

[ ] 3. ACEITÁVEL CONTINUAR SEM REDIS POR ATÉ 1 HORA
      - Performance degradada mas funcional
      - Não há perda de dados críticos
```

### 3. Evolution API Down

**Impacto:**
- Não é possível enviar mensagens
- Não é possível receber mensagens
- Julia efetivamente offline para médicos

**Modo degradado:**

```
ENVIO: Mensagens enfileiradas em fila_mensagens
RECEBIMENTO: Mensagens perdidas (WhatsApp não guarda)

Ações:
1. Mensagens para envio ficam em fila
2. Serão processadas quando Evolution voltar
3. Mensagens RECEBIDAS durante downtime são PERDIDAS
4. Comunicar médicos que Julia está temporariamente offline
```

**Procedimento:**

```
[ ] 1. PAUSAR WORKER (evitar tentar processar fila)
      - Railway Dashboard → julia-worker → Pause

[ ] 2. RESTAURAR EVOLUTION API
      - Ver "Restore Procedures" → Evolution API acima
      - Reconectar WhatsApp
      - Reconfigurar webhook

[ ] 3. VALIDAR RECONEXÃO
      - Enviar mensagem teste para número de teste
      - Verificar se chegou no webhook

[ ] 4. RETOMAR WORKER
      - Railway Dashboard → julia-worker → Resume
      - Fila será processada automaticamente

[ ] 5. COMUNICAR RESOLUÇÃO
      - Notificar equipe que Julia voltou
```

### 4. Anthropic API Down / Rate Limited

**Impacto:**
- Julia não consegue gerar respostas
- Conversas ficam pendentes

**Modo degradado:**

```python
# Código tem circuit breaker automático

# Se Anthropic está down (429, 503, timeout)
# Circuit abre após 5 falhas consecutivas
# Novas requisições retornam erro imediatamente

# Fallback: Enfileirar para retry
await fila_mensagens.insert({
    "mensagem": mensagem,
    "retry_count": 0,
    "processar_em": NOW() + INTERVAL '15 minutes'
})
```

**Ações:**

```
[ ] 1. VERIFICAR STATUS ANTHROPIC
      - https://status.anthropic.com
      - Se incidente global: aguardar

[ ] 2. VERIFICAR USAGE LIMITS
      - https://console.anthropic.com/settings/usage
      - Se rate limit: aguardar reset (geralmente 1 hora)
      - Se quota excedida: aumentar plano ou aguardar billing cycle

[ ] 3. MODO FALLBACK (OPCIONAL)
      - Habilitar respostas pré-programadas para casos comuns
      - Exemplo: "Estou processando muitas conversas agora, vou responder em alguns minutos"

[ ] 4. MONITORAR CIRCUIT BREAKER
      - curl /health/circuit
      - Aguardar circuit fechar automaticamente (após 30 segundos de sucesso)

[ ] 5. REPROCESSAR FILA
      - Worker automaticamente retenta mensagens após intervalo
      - Monitorar: railway logs -f | grep "retry"
```

### 5. Múltiplas Dependências Down

**Cenário catastrófico:**

```
CRITICAL INCIDENT: Multiple component failure

Se 2+ componentes críticos estão down simultaneamente:

[ ] 1. DECLARAR INCIDENT LEVEL 3
      - Escalar para CTO imediatamente
      - #incidents Slack: "@channel CRITICAL: Multiple failures"

[ ] 2. PAUSAR JULIA COMPLETAMENTE
      - INSERT INTO julia_status (status, motivo) VALUES ('pausado', 'Incident L3 - multiple failures');

[ ] 3. PRESERVAR ESTADO
      - NÃO fazer mudanças precipitadas
      - NÃO deletar dados
      - NÃO aplicar migrations
      - Fazer snapshot do estado atual para forensics

[ ] 4. INVESTIGAR CAUSA RAIZ
      - É um incidente regional (AWS, Supabase, etc)?
      - É um problema de configuração nossa?
      - É um ataque?

[ ] 5. RECOVERY COORDENADO
      - Restaurar dependências em ordem de criticidade:
        1. Supabase
        2. Evolution API
        3. Redis
        4. Anthropic
      - Validar cada componente antes de prosseguir

[ ] 6. COMUNICAÇÃO CONTÍNUA
      - Update a cada 10 minutos
      - Transparência com stakeholders
      - ETA realista (under-promise, over-deliver)
```

---

## Emergency Pause Procedure

Procedimento para pausar Julia completamente em caso de emergência.

### Quando Usar

- Detecção de spam acidental (Julia enviando msgs incorretas)
- Bug crítico descoberto em produção
- Médicos reportando comportamento inadequado
- Custo de API disparou inesperadamente
- Incidente de segurança ou compliance

### Procedimento

```sql
-- 1. PAUSAR JULIA IMEDIATAMENTE
INSERT INTO julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'EMERGÊNCIA: [descrever motivo]', 'manual');

-- Verificar
SELECT status, motivo, created_at FROM julia_status
ORDER BY created_at DESC LIMIT 1;
-- Deve retornar: pausado
```

```bash
# 2. PAUSAR SERVIÇOS RAILWAY (OPCIONAL)
# Se bug é grave e precisa impedir qualquer processamento:

# Via Dashboard:
# - Railway → julia-api → Settings → Pause
# - Railway → julia-worker → Settings → Pause
# - Railway → julia-scheduler → Settings → Pause

# Ou via CLI:
railway service pause julia-api
railway service pause julia-worker
railway service pause julia-scheduler
```

```
[ ] 3. COMUNICAR
      - Slack #incidents: "EMERGENCY PAUSE: Julia stopped - [reason]"
      - Notificar stakeholders: "Julia offline temporariamente"
      - Status page (se houver): "Degraded"

[ ] 4. INVESTIGAR
      - Logs: railway logs -n 500
      - Database: queries recentes, dados corrompidos?
      - Métricas: custo, volume, erros?

[ ] 5. CORRIGIR
      - Aplicar hotfix se possível
      - Rollback se necessário
      - Restaurar dados se corrompidos

[ ] 6. VALIDAR EM STAGING (se disponível)
      - Testar correção em ambiente não-produção
      - Simular fluxo end-to-end
      - Confirmar que problema foi resolvido

[ ] 7. RETOMAR GRADUALMENTE
      - Retomar 1 serviço por vez
      - Monitorar logs ativamente
      - Enviar mensagem teste para número controlado

[ ] 8. RETOMAR JULIA
      INSERT INTO julia_status (status, motivo, alterado_via)
      VALUES ('ativo', 'Incidente resolvido, retomando operação', 'manual');

[ ] 9. MONITORAR POR 2 HORAS
      - Logs em tempo real
      - Métricas de custo
      - Feedback de médicos
      - Pronto para pausar novamente se necessário

[ ] 10. POST-MORTEM (OBRIGATÓRIO)
      - Documentar cronologia do incidente
      - Root cause analysis
      - Ações preventivas
      - Atualizar runbook/DR com aprendizados
```

---

## Communication During Incidents

### Templates de Comunicação

#### Início de Incidente

```markdown
INCIDENT DECLARED: [Título curto]

Severity: [P0 - Critical | P1 - High | P2 - Medium]
Status: Investigating
Started: [timestamp]

Impact:
- [Descrever o que está afetado]
- [Quantos usuários impactados]
- [Funcionalidades degradadas/offline]

Actions taken:
- [O que já foi feito]

Next update: [timestamp - máx 15 min]

Incident Commander: [Nome]
```

#### Update Durante Incidente

```markdown
INCIDENT UPDATE: [Título]

Status: [Investigating | Identified | Monitoring | Resolved]
Duration: [tempo desde início]

Latest findings:
- [O que descobrimos]

Actions in progress:
- [O que está sendo feito agora]

ETA: [estimativa de resolução - sempre conservadora]

Next update: [timestamp - máx 15 min]
```

#### Resolução de Incidente

```markdown
INCIDENT RESOLVED: [Título]

Duration: [tempo total]
Status: Resolved

Root cause:
- [Causa raiz identificada]

Resolution:
- [O que foi feito para resolver]

Preventive measures:
- [O que será feito para evitar recorrência]

Post-mortem: [link ou "será publicado em 24h"]

Thank you for your patience.
```

### Canais de Comunicação

| Stakeholder | Canal | Frequência |
|-------------|-------|------------|
| Equipe técnica | Slack #incidents | Real-time (cada ação) |
| Management | Email + Slack | A cada 30 min |
| Clientes (médicos) | WhatsApp broadcast | Apenas se downtime > 1 hora |
| Status page | Público | A cada update |

### Escalation Matrix

```
Severity P0 (Critical - Total outage):
→ Notificar: CTO, CEO, Product Lead
→ Frequência: Update a cada 10 minutos
→ War room: Criar Slack channel dedicado

Severity P1 (High - Degraded service):
→ Notificar: Engineering Lead, Product Lead
→ Frequência: Update a cada 30 minutos
→ Channel: #incidents

Severity P2 (Medium - Minor issues):
→ Notificar: Engineering team
→ Frequência: Update quando houver progresso
→ Channel: #eng
```

---

## Post-Incident Review Process

Obrigatório após qualquer incidente P0 ou P1.

### Timeline

```
Dentro de 24 horas: Draft inicial do post-mortem
Dentro de 48 horas: Revisão com equipe
Dentro de 1 semana: Ações preventivas implementadas
```

### Template de Post-Mortem

```markdown
# Post-Mortem: [Título do Incidente]

**Data:** [YYYY-MM-DD]
**Autor:** [Nome]
**Revisores:** [Nomes]

## Sumário Executivo

[1-2 parágrafos: O que aconteceu, impacto, resolução]

## Timeline

| Timestamp | Event |
|-----------|-------|
| 14:23 | Incidente detectado - /health/deep retornou 503 |
| 14:25 | Equipe notificada via PagerDuty |
| 14:27 | Identificado problema: Supabase connection timeout |
| 14:30 | Rollback iniciado |
| 14:35 | Serviço restaurado |
| 14:40 | Monitoramento confirmou estabilidade |
| 14:45 | Incidente resolvido |

**Total duration:** 22 minutos

## Impacto

- **Usuários afetados:** ~50 médicos tentaram enviar mensagens
- **Mensagens perdidas:** 0 (enfileiradas com sucesso)
- **Revenue impact:** Negligível (< R$ 10)
- **Reputacional:** Baixo (downtime curto)

## Root Cause

[Análise detalhada da causa raiz - seja técnico]

Exemplo:
- Migration X aplicada às 14:20
- Migration criou índice sem CONCURRENTLY
- Índice bloqueou tabela `conversations` por 3 minutos
- Queries timeout após 30 segundos
- /health/deep falhou, Railway marcou service como unhealthy

## Resolution

[Como foi resolvido]

Exemplo:
- Rollback para deployment anterior (14:30)
- Aplicação de migration corrigida (usando CONCURRENTLY)
- Redeploy do código (14:35)

## Lessons Learned

**O que funcionou bem:**
- Detecção rápida (2 minutos após início)
- Comunicação clara
- Rollback executado em < 5 minutos

**O que poderia ter sido melhor:**
- Migration deveria ter sido testada em staging
- Checklist de migration não foi seguido completamente
- Healthcheck poderia ter timeout maior para tolerar migrations curtas

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| Adicionar CI check para detectar migrations sem CONCURRENTLY | [Nome] | 2026-02-15 | Todo |
| Atualizar runbook com checklist obrigatório pre-deploy | [Nome] | 2026-02-12 | Done |
| Aumentar healthcheck timeout para 120s | [Nome] | 2026-02-11 | Done |
| Criar ambiente staging para testar migrations | [Nome] | 2026-03-01 | In Progress |

## Appendix

- Logs relevantes: [link]
- Dashboards: [link]
- Slack thread: [link]
```

### Distribuição

1. Publicar no wiki interno
2. Apresentar em weekly retrospective
3. Compartilhar aprendizados com time produto
4. Arquivar em `docs/auditorias/post-mortems/`

---

## Backup Verification Schedule

Verificar regularmente que backups funcionam.

### Checklist Mensal

```
[ ] Verificar que backups automáticos Supabase estão rodando
    - Dashboard → Backups → Ver última data

[ ] Testar restore de backup manual (pg_dump)
    - Download backup do mês anterior
    - Restore em projeto staging
    - Validar dados

[ ] Exportar variáveis Railway
    - railway variables > backup-vars-$(date +%Y%m).txt
    - Armazenar em 1Password/Vault

[ ] Backup de configuração Evolution API
    - Exportar instâncias
    - Exportar webhooks
    - Armazenar com data

[ ] Documentar no tracking sheet
    - Data da verificação
    - Resultado (Pass/Fail)
    - Observações
```

### Drill de Disaster Recovery (Trimestral)

Simular incidente completo para validar procedimentos.

```
Cenário: "Supabase database corrompida, necessário restore"

[ ] 1. Criar backup manual de produção
[ ] 2. Criar novo projeto Supabase (staging)
[ ] 3. Restaurar backup em staging
[ ] 4. Apontar services Railway para staging
[ ] 5. Validar /health/deep
[ ] 6. Testar fluxo end-to-end
[ ] 7. Cronometrar tempo total (meta: < 30 min)
[ ] 8. Documentar problemas encontrados
[ ] 9. Atualizar DR procedures baseado em aprendizados
[ ] 10. Deletar staging e reverter para produção
```

---

## Contact and Escalation

### Disaster Recovery Team

| Role | Primary | Backup |
|------|---------|--------|
| Incident Commander | [Nome] | [Nome] |
| Database Lead | [Nome] | [Nome] |
| Infrastructure Lead | [Nome] | [Nome] |
| Communications Lead | [Nome] | [Nome] |

### External Support Contacts

| Vendor | Support Type | Contact | SLA |
|--------|--------------|---------|-----|
| Supabase | Pro Support | support@supabase.com | < 4 hours |
| Railway | Email | team@railway.app | < 24 hours |
| Anthropic | API Support | api-support@anthropic.com | < 12 hours |
| Evolution API | Community | GitHub Issues | Best effort |

### Escalation Triggers

**Escalate to Incident Commander if:**
- RTO will be exceeded (> 30 minutes para DB, > 1 hour para outros)
- Data loss > RPO (> 15 minutes para DB)
- Multiple attempts to restore failed
- Root cause unknown após 30 minutos de investigação

**Escalate to CTO if:**
- Incident duration > 2 horas
- Data corruption suspected
- Security breach suspected
- Potential compliance violation

---

## Appendix: Quick Reference

### Critical Commands

```bash
# Health checks
curl https://whats-agents-production.up.railway.app/health/deep

# Pause Julia
psql $SUPABASE_URL -c "INSERT INTO julia_status (status, motivo) VALUES ('pausado', 'Emergency');"

# Railway rollback (via Dashboard)
# Service → Deployments → Select stable → Redeploy

# Backup Supabase manual
pg_dump "$SUPABASE_URL" --format=custom --file="backup-$(date +%Y%m%d).dump"

# Restore Supabase manual
pg_restore --clean --no-owner --dbname="$SUPABASE_URL" backup.dump

# View logs
railway logs -n 100

# Check circuit breaker status
curl https://whats-agents-production.up.railway.app/health/circuit
```

### Recovery Time Estimates

| Scenario | Estimated Time |
|----------|----------------|
| Rollback deployment | 5 minutes |
| Restart Redis | 2 minutes |
| Restore Supabase (auto backup) | 15-30 minutes |
| Restore Supabase (manual) | 30-60 minutes |
| Recreate Railway service | 10-15 minutes |
| Reconnect Evolution WhatsApp | 5 minutes |
| Full disaster recovery (all components) | 1-2 hours |

---

**Última atualização:** 2026-02-10
**Responsável:** Engineering Lead
**Próxima revisão:** 2026-03-10
**Próximo DR Drill:** 2026-05-10
