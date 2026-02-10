# ÉPICO 5: Cleanup & Governança

## Contexto

Este épico finaliza a sprint com limpeza de artefatos obsoletos e estabelece padrões de governança para futuras mudanças no schema.

**Severidade:** BAIXA - housekeeping

## Escopo

- **Incluído:**
  - Remover `campanhas_deprecated`
  - Documentar policies de RLS existentes
  - Criar checklist para novas tabelas
  - Atualizar documentação de arquitetura

- **Excluído:**
  - Mover extensões para outro schema (risco alto, benefício baixo)
  - Refatorar tabelas com muitas colunas (sprint futura)

---

## Tarefa 5.1: Remover campanhas_deprecated

### Objetivo
Remover tabela obsoleta que não tem uso e está sem RLS.

### Análise

```sql
-- Verificar referências
SELECT * FROM campanhas_deprecated LIMIT 5;
-- 15 rows, dados de 2025

-- Verificar FKs para esta tabela
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE ccu.table_name = 'campanhas_deprecated';
-- Deve retornar vazio
```

### Implementação

```sql
-- Migration: 20260210_drop_campanhas_deprecated.sql

-- Backup dos dados antes de remover
CREATE TABLE IF NOT EXISTS _backup_campanhas_deprecated_20260210 AS
SELECT * FROM campanhas_deprecated;

-- Remover tabela
DROP TABLE campanhas_deprecated;
```

### Rollback

```sql
-- Recriar a partir do backup
CREATE TABLE campanhas_deprecated AS
SELECT * FROM _backup_campanhas_deprecated_20260210;
```

### Testes Obrigatórios

- [ ] Confirmar que não há FKs referenciando
- [ ] Grep no código por "campanhas_deprecated" (deve retornar 0)
- [ ] Aplicação funcionando normalmente

### Definition of Done
- [ ] Tabela removida
- [ ] Backup salvo
- [ ] Nenhuma referência no código

### Estimativa
15 minutos

---

## Tarefa 5.2: Documentar Policies RLS

### Objetivo
Criar documentação centralizada das policies de acesso.

### Implementação

Criar arquivo `docs/arquitetura/rls-policies.md`:

```markdown
# Row Level Security - Políticas de Acesso

## Visão Geral

O sistema usa Row Level Security (RLS) para controlar acesso aos dados no PostgreSQL.
Todas as tabelas com dados sensíveis têm RLS habilitado.

## Roles

| Role | Uso | Acesso Típico |
|------|-----|---------------|
| `anon` | Clientes não autenticados | Sem acesso (bloqueado) |
| `authenticated` | Dashboard autenticado | SELECT em tabelas de leitura |
| `service_role` | Backend Python | Full access |

## Padrões de Policy

### Tabelas Backend-Only
```sql
-- Apenas service_role tem acesso
CREATE POLICY "table_service_role_all"
ON table_name FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "table_deny_anon"
ON table_name FOR ALL TO anon
USING (false);
```

### Tabelas Dashboard Read
```sql
-- Service role full + authenticated read
CREATE POLICY "table_service_role_all"
ON table_name FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "table_authenticated_read"
ON table_name FOR SELECT TO authenticated
USING (true);
```

## Inventário de Policies

### Tabelas com PII (Dados Pessoais)

| Tabela | anon | authenticated | service_role | Notas |
|--------|------|---------------|--------------|-------|
| clientes | ❌ | SELECT | ALL | Dados de médicos |
| doctor_context | ❌ | SELECT | ALL | Memórias |
| doctor_state | ❌ | SELECT | ALL | Estado do médico |
| contatos_grupo | ❌ | ❌ | ALL | Telefones |
| clientes_log | ❌ | ❌ | ALL | Histórico |

### Tabelas Operacionais

| Tabela | anon | authenticated | service_role |
|--------|------|---------------|--------------|
| chips | SELECT | SELECT | ALL |
| vagas | ❌ | SELECT | ALL |
| conversations | ❌ | SELECT+INSERT+UPDATE | ALL |
| campanhas | ❌ | SELECT+INSERT+UPDATE | ALL |
| ... | | | |

### Tabelas de Configuração

| Tabela | anon | authenticated | service_role |
|--------|------|---------------|--------------|
| app_settings | ❌ | ❌ | ALL |
| feature_flags | ❌ | ❌ | ALL |
| prompts | ❌ | ❌ | ALL |

## Auditoria Periódica

Executar mensalmente:
```sql
-- Tabelas sem RLS
SELECT tablename FROM pg_tables
WHERE schemaname = 'public' AND NOT rowsecurity;

-- Tabelas sem policies
SELECT t.tablename
FROM pg_tables t
LEFT JOIN pg_policies p ON t.tablename = p.tablename
WHERE t.schemaname = 'public' AND t.rowsecurity = true
GROUP BY t.tablename
HAVING count(p.policyname) = 0;
```
```

### Definition of Done
- [ ] Arquivo criado
- [ ] Inventário completo
- [ ] Link no README de arquitetura

### Estimativa
45 minutos

---

## Tarefa 5.3: Checklist para Novas Tabelas

### Objetivo
Criar checklist padrão que deve ser seguida ao criar novas tabelas.

### Implementação

Adicionar em `docs/arquitetura/banco-de-dados.md`:

```markdown
## Checklist para Novas Tabelas

Ao criar uma nova tabela, verificar:

### 1. Estrutura
- [ ] PK é UUID com `DEFAULT gen_random_uuid()`
- [ ] `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- [ ] Trigger de `updated_at` configurado
- [ ] Constraints CHECK para validação de domínio
- [ ] NOT NULL em colunas obrigatórias

### 2. Foreign Keys
- [ ] Todas as FKs declaradas explicitamente
- [ ] **Índice criado para cada FK** (PostgreSQL não cria automaticamente)
- [ ] ON DELETE apropriado (RESTRICT, CASCADE, SET NULL)

### 3. Segurança (RLS)
- [ ] `ALTER TABLE tabela ENABLE ROW LEVEL SECURITY;`
- [ ] Policy para `service_role` (backend)
- [ ] Policy para `authenticated` (se dashboard precisar)
- [ ] Policy bloqueando `anon` (se dados sensíveis)
- [ ] COMMENT documentando propósito das policies

### 4. Performance
- [ ] Índices em colunas frequentes em WHERE/JOIN
- [ ] Índice GIN em colunas JSONB se queried
- [ ] Considerar índices parciais para queries filtradas

### 5. Documentação
- [ ] `COMMENT ON TABLE` explicando propósito
- [ ] `COMMENT ON COLUMN` em colunas não óbvias
- [ ] Migration versionada

### Exemplo Completo

```sql
-- Migration: 20260210_create_nova_tabela.sql

CREATE TABLE nova_tabela (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('ativo', 'inativo')),
    dados JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE nova_tabela IS 'Descrição da tabela';

-- Índices
CREATE INDEX idx_nova_tabela_cliente ON nova_tabela(cliente_id);
CREATE INDEX idx_nova_tabela_status ON nova_tabela(status);

-- Trigger updated_at
CREATE TRIGGER trigger_nova_tabela_updated_at
    BEFORE UPDATE ON nova_tabela
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE nova_tabela ENABLE ROW LEVEL SECURITY;

CREATE POLICY "nova_tabela_service_role_all"
ON nova_tabela FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "nova_tabela_authenticated_read"
ON nova_tabela FOR SELECT TO authenticated
USING (true);
```
```

### Definition of Done
- [ ] Checklist adicionada à documentação
- [ ] Exemplo completo incluído
- [ ] Comunicado ao time

### Estimativa
30 minutos

---

## Tarefa 5.4: Atualizar Documentação de Arquitetura

### Objetivo
Atualizar `docs/arquitetura/banco-de-dados.md` com informações desta sprint.

### Conteúdo a Adicionar

1. Link para `rls-policies.md`
2. Link para `functions-security.md`
3. Atualizar contagem de tabelas (~108 após remoção)
4. Documentar índices criados/removidos
5. Adicionar seção de "Última Auditoria"

### Definition of Done
- [ ] Documentação atualizada
- [ ] Links funcionando
- [ ] Métricas atualizadas

### Estimativa
30 minutos

---

## Tarefa 5.5: Salvar Relatório de Auditoria

### Objetivo
Salvar o relatório do Database Review para referência futura.

### Implementação

Criar arquivo `docs/auditorias/db-review-2026-02-09.md` com:
- Scorecard
- Findings (críticos, importantes, melhorias)
- Ações tomadas
- Métricas antes/depois

### Definition of Done
- [ ] Relatório salvo
- [ ] Métricas finais documentadas

### Estimativa
15 minutos

---

## Resumo do Épico

| Tarefa | Estimativa |
|--------|------------|
| 5.1 Remover campanhas_deprecated | 15min |
| 5.2 Documentar policies | 45min |
| 5.3 Checklist novas tabelas | 30min |
| 5.4 Atualizar docs arquitetura | 30min |
| 5.5 Salvar relatório auditoria | 15min |
| **Total** | **2h 15min** |

## Validação Final do Épico

- [ ] `campanhas_deprecated` não existe mais
- [ ] `docs/arquitetura/rls-policies.md` existe
- [ ] `docs/arquitetura/functions-security.md` existe
- [ ] Checklist adicionada a `banco-de-dados.md`
- [ ] Relatório de auditoria salvo

---

## Validação Final da Sprint

### Queries de Verificação

```sql
-- 1. Zero tabelas sem RLS
SELECT count(*) FROM pg_tables
WHERE schemaname = 'public' AND NOT rowsecurity;
-- Target: 0

-- 2. Zero FKs sem índice (em tabelas >1k rows)
-- (query do épico 3)
-- Target: 0

-- 3. Functions com search_path
SELECT count(*) FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
AND prosecdef = true
AND NOT (proconfig @> ARRAY['search_path=public']);
-- Target: 0
```

### Métricas Finais

| Métrica | Antes | Depois | Delta |
|---------|-------|--------|-------|
| Tabelas sem RLS | 7 | 0 | -7 |
| FKs sem índice | 31 | 0 | -31 |
| Índices criados | - | 31 | +31 |
| Índices removidos | - | 5 | -5 |
| Functions corrigidas | 37 | 0 | -37 |
| Advisor ERRORs | 10 | 0 | -10 |
| Espaço índices | ~85MB | ~95MB | +10MB (índices FK) |
