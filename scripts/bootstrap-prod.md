# Bootstrap do Supabase PROD

## Pré-requisitos

1. Supabase CLI instalado: `brew install supabase/tap/supabase`
2. Login feito: `supabase login`
3. Projeto PROD criado no dashboard

## Passos

### 1. Exportar schema do banco atual (staging/dev)

```bash
# Linkar ao projeto atual (staging/dev)
supabase link --project-ref SEU_PROJECT_REF_STAGING

# Exportar schema completo (sem dados)
supabase db dump -f schema.sql --data-only false

# O arquivo schema.sql contém:
# - Todas as tabelas
# - Views
# - Functions
# - Triggers
# - RLS policies
# - Indexes
```

### 2. Preparar para PROD

Editar o `schema.sql` se necessário:
- Remover dados de teste (se houver INSERTs)
- Verificar extensões (vector, pg_trgm, unaccent)

### 3. Aplicar no PROD

```bash
# Linkar ao projeto PROD
supabase link --project-ref SEU_PROJECT_REF_PROD

# Aplicar schema
supabase db push

# Ou via SQL Editor no dashboard:
# - Copiar conteúdo do schema.sql
# - Colar no SQL Editor
# - Executar
```

### 4. Configurar markers de ambiente

```sql
-- IMPORTANTE: Executar no PROD após aplicar schema
INSERT INTO public.app_settings (key, value, description)
VALUES
    ('environment', 'production', 'Environment marker - NÃO ALTERAR'),
    ('supabase_project_ref', 'SEU_PROJECT_REF_PROD', 'Project reference for hard guard')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

### 5. Verificar

```sql
-- Verificar markers
SELECT * FROM app_settings;

-- Verificar tabelas críticas existem
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('clientes', 'conversations', 'fila_mensagens', 'doctor_state', 'app_settings');

-- Verificar views críticas existem
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public'
AND table_name IN ('campaign_sends', 'campaign_metrics');
```

## Alternativa: Aplicar migrations uma a uma

Se preferir manter histórico completo de migrations:

```bash
# Linkar ao PROD
supabase link --project-ref SEU_PROJECT_REF_PROD

# Ver migrations pendentes
supabase migration list

# Aplicar todas
supabase db push
```

⚠️ **CUIDADO**: 93+ migrations podem ter conflitos históricos. Bootstrap é mais seguro para primeiro deploy.
