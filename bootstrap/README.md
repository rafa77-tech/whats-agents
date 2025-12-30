# Bootstrap do Supabase PROD

## Stack
- **Supabase CLI**: v2.67.1
- **Migrations locais**: Não (todas via MCP/Dashboard)
- **Estratégia**: Exportar schema do staging → Aplicar no PROD

---

## Passo 1: Exportar Schema do Staging

```bash
# Fazer login (abre browser)
supabase login

# Linkar ao projeto staging/dev
supabase link --project-ref SEU_PROJECT_REF_STAGING

# Exportar schema completo (sem dados)
supabase db dump -f bootstrap/01-schema.sql

# O arquivo contém:
# ✅ Extensions (vector, pg_trgm, unaccent)
# ✅ Tables + indexes
# ✅ Functions / RPCs
# ✅ Views
# ✅ RLS + policies
# ✅ Triggers
```

---

## Passo 2: Criar Seeds Mínimos

O arquivo `02-seeds.sql` já está pronto com:
- app_settings (environment marker, project_ref)
- feature_flags essenciais

**IMPORTANTE**: Editar `02-seeds.sql` antes de aplicar no PROD:
- Trocar `environment` de 'staging' para 'production'
- Trocar `supabase_project_ref` para o ref do PROD

---

## Passo 3: Aplicar no PROD

### Opção A: Via Supabase CLI

```bash
# Linkar ao projeto PROD
supabase link --project-ref SEU_PROJECT_REF_PROD

# Aplicar schema
supabase db push

# Aplicar seeds manualmente via SQL Editor
# (seeds precisam ser revisados antes de aplicar)
```

### Opção B: Via Dashboard

1. Supabase Dashboard → SQL Editor
2. Colar conteúdo de `01-schema.sql`
3. Executar
4. Colar conteúdo de `02-seeds.sql` (já editado para PROD)
5. Executar

---

## Passo 4: Verificar Pós-Bootstrap

```sql
-- 1. Verificar markers
SELECT * FROM app_settings;

-- 2. Verificar feature flags
SELECT * FROM feature_flags;

-- 3. Verificar tabelas críticas
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'clientes', 'conversations', 'fila_mensagens', 
    'doctor_state', 'app_settings', 'intent_log',
    'touch_reconciliation_log', 'business_events'
);

-- 4. Verificar views críticas
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public'
AND table_name IN ('campaign_sends', 'campaign_metrics');

-- 5. Verificar extensions
SELECT extname FROM pg_extension 
WHERE extname IN ('vector', 'pg_trgm', 'unaccent', 'pgcrypto');

-- 6. Verificar RLS está ativo
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' AND rowsecurity = true;
```

---

## Passo 5: Smoke Test via API

Após deploy no Railway:

```bash
# 1. Health check deep
curl https://SEU-APP.railway.app/health/deep | jq .

# Esperado: status=healthy, todos checks=ok

# 2. Schema info
curl https://SEU-APP.railway.app/health/schema | jq .

# Esperado: schema_up_to_date=true
```

---

## Checklist Final

```
[ ] Schema exportado do staging
[ ] 02-seeds.sql editado para PROD (environment='production')
[ ] Schema aplicado no PROD
[ ] Seeds aplicados no PROD
[ ] Verificações SQL passaram
[ ] /health/deep retorna 200
[ ] /health/schema confirma versão
```
