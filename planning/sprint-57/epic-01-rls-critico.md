# ÉPICO 1: Segurança RLS Crítica

## Contexto

O Database Review de 2026-02-09 identificou **7 tabelas públicas sem RLS habilitado** e **3 views com SECURITY DEFINER** que bypassam políticas de segurança. Isso expõe dados via PostgREST API para qualquer cliente com a anon key.

**Severidade:** CRÍTICA - dados acessíveis sem autenticação

## Escopo

- **Incluído:**
  - Habilitar RLS nas 7 tabelas identificadas
  - Criar policies adequadas (service_role para backend-only)
  - Corrigir ou documentar views SECURITY DEFINER
  - Revisar policies permissivas em tabelas com PII

- **Excluído:**
  - Refatorar código da aplicação
  - Criar policies por usuário (não é multi-tenant)
  - Migrar extensões para outro schema (Épico 5)

---

## Tarefa 1.1: Habilitar RLS em tabelas críticas

### Objetivo
Habilitar Row Level Security nas 7 tabelas que estão expostas via PostgREST sem proteção.

### Tabelas Afetadas

| Tabela | Rows | Classificação | Ação |
|--------|------|---------------|------|
| `helena_sessoes` | ~1 | AUTH | RLS + service_role only |
| `circuit_transitions` | ~274 | OPERACIONAL | RLS + service_role only |
| `warmup_schedule` | ~25 | OPERACIONAL | RLS + service_role only |
| `chip_daily_snapshots` | ~24 | OPERACIONAL | RLS + service_role only |
| `fila_mensagens_dlq` | 0 | OPERACIONAL | RLS + service_role only |
| `market_intelligence_daily` | 0 | OPERACIONAL | RLS + service_role only |
| `campanhas_deprecated` | 15 | DEPRECATED | DROP TABLE (ver Épico 5) |

### Implementação

```sql
-- Migration: 20260210_enable_rls_critical_tables.sql

-- 1. helena_sessoes (dados de sessão - crítico)
ALTER TABLE helena_sessoes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "helena_sessoes_service_role_all"
ON helena_sessoes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Bloquear acesso anon/authenticated
CREATE POLICY "helena_sessoes_deny_anon"
ON helena_sessoes
FOR ALL
TO anon
USING (false);

CREATE POLICY "helena_sessoes_deny_authenticated"
ON helena_sessoes
FOR ALL
TO authenticated
USING (false);

-- 2. circuit_transitions
ALTER TABLE circuit_transitions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "circuit_transitions_service_role_all"
ON circuit_transitions
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Read-only para authenticated (monitoramento)
CREATE POLICY "circuit_transitions_authenticated_read"
ON circuit_transitions
FOR SELECT
TO authenticated
USING (true);

-- 3. warmup_schedule
ALTER TABLE warmup_schedule ENABLE ROW LEVEL SECURITY;

CREATE POLICY "warmup_schedule_service_role_all"
ON warmup_schedule
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 4. chip_daily_snapshots
ALTER TABLE chip_daily_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "chip_daily_snapshots_service_role_all"
ON chip_daily_snapshots
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "chip_daily_snapshots_authenticated_read"
ON chip_daily_snapshots
FOR SELECT
TO authenticated
USING (true);

-- 5. fila_mensagens_dlq
ALTER TABLE fila_mensagens_dlq ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fila_mensagens_dlq_service_role_all"
ON fila_mensagens_dlq
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 6. market_intelligence_daily
ALTER TABLE market_intelligence_daily ENABLE ROW LEVEL SECURITY;

CREATE POLICY "market_intelligence_daily_service_role_all"
ON market_intelligence_daily
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "market_intelligence_daily_authenticated_read"
ON market_intelligence_daily
FOR SELECT
TO authenticated
USING (true);
```

### Rollback

```sql
-- Rollback: remover policies e desabilitar RLS
DROP POLICY IF EXISTS "helena_sessoes_service_role_all" ON helena_sessoes;
DROP POLICY IF EXISTS "helena_sessoes_deny_anon" ON helena_sessoes;
DROP POLICY IF EXISTS "helena_sessoes_deny_authenticated" ON helena_sessoes;
ALTER TABLE helena_sessoes DISABLE ROW LEVEL SECURITY;

-- Repetir para cada tabela...
```

### Testes Obrigatórios

**Unitários (via SQL):**
```sql
-- Testar que anon não consegue ler helena_sessoes
SET ROLE anon;
SELECT count(*) FROM helena_sessoes; -- Deve retornar 0 ou erro

-- Testar que service_role consegue ler/escrever
SET ROLE service_role;
SELECT count(*) FROM helena_sessoes; -- Deve funcionar
```

**Integração:**
- [ ] Backend consegue criar/ler helena_sessoes via service_role
- [ ] Dashboard não quebra ao carregar páginas que usam essas tabelas
- [ ] Webhook de mensagem continua funcionando

### Definition of Done
- [ ] Migration aplicada em branch Supabase
- [ ] Testes SQL passando
- [ ] Fluxo Helena testado manualmente
- [ ] Supabase Advisor: 0 erros de "RLS Disabled in Public"

### Estimativa
1.5 horas

---

## Tarefa 1.2: Corrigir Views SECURITY DEFINER

### Objetivo
Avaliar e corrigir as 3 views que usam SECURITY DEFINER, que bypassa RLS do usuário que consulta.

### Views Afetadas

| View | Uso | Decisão |
|------|-----|---------|
| `chips_needing_attention` | Dashboard ops | Manter DEFINER (intencional) + documentar |
| `chips_ready_for_production` | Dashboard ops | Manter DEFINER (intencional) + documentar |
| `pool_status` | Dashboard ops | Manter DEFINER (intencional) + documentar |

### Análise
Essas views são usadas pelo dashboard para mostrar status agregado de chips. O SECURITY DEFINER é **intencional** porque:
1. O dashboard usa authenticated role
2. As tabelas base (chips) têm RLS
3. A view precisa agregar dados de múltiplos chips

### Implementação

Adicionar comentários documentando a decisão:

```sql
COMMENT ON VIEW chips_needing_attention IS
'SECURITY DEFINER intencional: agrega dados de chips para dashboard.
Acesso controlado via authenticated role. Revisado em 2026-02-10.';

COMMENT ON VIEW chips_ready_for_production IS
'SECURITY DEFINER intencional: lista chips prontos para produção.
Acesso controlado via authenticated role. Revisado em 2026-02-10.';

COMMENT ON VIEW pool_status IS
'SECURITY DEFINER intencional: status agregado do pool de chips.
Acesso controlado via authenticated role. Revisado em 2026-02-10.';
```

### Testes Obrigatórios

**Integração:**
- [ ] Dashboard Chips carrega corretamente
- [ ] View retorna dados esperados para authenticated
- [ ] View não expõe dados para anon

### Definition of Done
- [ ] Comentários adicionados nas views
- [ ] Dashboard testado
- [ ] Decisão documentada em `docs/arquitetura/banco-de-dados.md`

### Estimativa
30 minutos

---

## Tarefa 1.3: Revisar Policies Permissivas em PII

### Objetivo
Avaliar e corrigir policies com `USING (true)` em tabelas que contêm PII (dados pessoais de médicos).

### Tabelas com PII e Policies Permissivas

| Tabela | Policy | Problema | Ação |
|--------|--------|----------|------|
| `doctor_context` | INSERT/UPDATE com true | Médico pode alterar contexto de outro | Avaliar - backend only? |
| `interacoes` | INSERT/UPDATE com true | Médico pode ver interações de outro | Manter - backend only |
| `conversations` | INSERT/UPDATE com true | Backend only | Manter - backend only |

### Análise

Essas tabelas são acessadas apenas pelo backend (service_role), não diretamente pelo cliente. As policies permissivas existem para o role `authenticated`, que é usado apenas internamente.

**Decisão:** Manter as policies atuais, mas:
1. Documentar que `authenticated` é usado apenas pelo backend
2. Considerar criar role `backend` separado no futuro

### Implementação

Adicionar documentação:

```sql
COMMENT ON POLICY "Authenticated users can insert doctor_context" ON doctor_context IS
'Backend-only: authenticated role usado apenas pelo servidor.
Clientes usam anon key e não têm acesso. Revisado em 2026-02-10.';
```

### Testes Obrigatórios

**Integração:**
- [ ] Confirmar que anon não consegue acessar doctor_context
- [ ] Confirmar que o pipeline de mensagens funciona

### Definition of Done
- [ ] Policies documentadas
- [ ] Testes de acesso anon confirmados

### Estimativa
1 hora

---

## Tarefa 1.4: Criar Policies para Tabelas com RLS sem Policy

### Objetivo
Das 52 tabelas com RLS habilitado mas sem policies, priorizar as que precisam de acesso read pelo dashboard.

### Tabelas Prioritárias

| Tabela | Acesso Necessário | Policy |
|--------|-------------------|--------|
| `business_events` | Dashboard read | authenticated SELECT |
| `business_alerts` | Dashboard read | authenticated SELECT |
| `metricas_pipeline_diarias` | Dashboard read | authenticated SELECT |
| `diretrizes` | Dashboard read | authenticated SELECT |

### Implementação

```sql
-- business_events
CREATE POLICY "business_events_authenticated_read"
ON business_events
FOR SELECT
TO authenticated
USING (true);

CREATE POLICY "business_events_service_role_all"
ON business_events
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Repetir padrão para outras tabelas...
```

### Testes Obrigatórios

- [ ] Dashboard de métricas carrega
- [ ] Dashboard de alertas carrega

### Definition of Done
- [ ] Policies criadas para tabelas do dashboard
- [ ] Dashboard testado

### Estimativa
1 hora

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| 1.1 Habilitar RLS | 1.5h | Alto |
| 1.2 Views DEFINER | 0.5h | Baixo |
| 1.3 Policies PII | 1h | Médio |
| 1.4 Policies Dashboard | 1h | Médio |
| **Total** | **4h** | |

## Validação Final do Épico

```sql
-- Verificar que não há tabelas sem RLS
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
AND NOT rowsecurity;
-- Deve retornar vazio ou apenas campanhas_deprecated

-- Verificar policies existem
SELECT tablename, count(*) as policy_count
FROM pg_policies
WHERE schemaname = 'public'
GROUP BY tablename
HAVING count(*) = 0;
-- Deve retornar vazio
```
