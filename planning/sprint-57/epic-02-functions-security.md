# ÉPICO 2: Functions & Search Path Security

## Contexto

O Database Review identificou **37 functions sem search_path fixo**, incluindo várias com **SECURITY DEFINER**. Isso cria vulnerabilidade de SQL injection via manipulação do search_path.

A function `execute_readonly_query` é especialmente crítica pois:
1. É SECURITY DEFINER (executa com privilégios do owner)
2. Aceita SQL dinâmico como parâmetro
3. Não tem search_path fixo

**Severidade:** ALTA - potencial escalação de privilégios

## Escopo

- **Incluído:**
  - Corrigir `execute_readonly_query` (crítico)
  - Adicionar search_path em 37 functions
  - Documentar functions SECURITY DEFINER

- **Excluído:**
  - Refatorar lógica das functions
  - Remover functions não utilizadas (avaliar em sprint futura)

---

## Tarefa 2.1: Corrigir execute_readonly_query (CRÍTICO)

### Objetivo
Corrigir a function mais crítica que aceita SQL dinâmico com SECURITY DEFINER.

### Análise da Function Atual

```sql
-- Versão atual (VULNERÁVEL)
CREATE OR REPLACE FUNCTION execute_readonly_query(sql_query text)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
...
$$;
```

**Problemas:**
1. Sem search_path - atacante pode criar tabela maliciosa em outro schema
2. SECURITY DEFINER sem validação adequada
3. Aceita qualquer SELECT (deveria ter whitelist)

### Implementação

```sql
-- Migration: 20260210_fix_execute_readonly_query.sql

CREATE OR REPLACE FUNCTION execute_readonly_query(sql_query text)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    result JSONB;
    normalized_query TEXT;
BEGIN
    -- Normalizar query
    normalized_query := LOWER(TRIM(sql_query));

    -- Validações de segurança
    IF normalized_query !~ '^select\s' THEN
        RAISE EXCEPTION 'Only SELECT queries are allowed';
    END IF;

    -- Bloquear comandos perigosos
    IF normalized_query ~ '\b(insert|update|delete|drop|truncate|alter|create|grant|revoke)\b' THEN
        RAISE EXCEPTION 'Modification commands are not allowed';
    END IF;

    -- Bloquear acesso a schemas sensíveis
    IF normalized_query ~ '\b(pg_catalog|information_schema|auth|storage)\.' THEN
        RAISE EXCEPTION 'Access to system schemas is not allowed';
    END IF;

    -- Executar com LIMIT forçado
    IF normalized_query !~ '\blimit\s+\d+' THEN
        sql_query := sql_query || ' LIMIT 100';
    END IF;

    -- Executar query
    EXECUTE 'SELECT jsonb_agg(row_to_json(t)) FROM (' || sql_query || ') t'
    INTO result;

    RETURN COALESCE(result, '[]'::jsonb);
END;
$$;

-- Comentário de segurança
COMMENT ON FUNCTION execute_readonly_query(text) IS
'SECURITY DEFINER: Executa queries SELECT dinâmicas para Helena.
Validações: apenas SELECT, sem comandos DML/DDL, sem schemas de sistema, LIMIT 100.
Corrigido em 2026-02-10 com search_path fixo.';
```

### Testes Obrigatórios

**Unitários:**
```sql
-- Deve funcionar
SELECT execute_readonly_query('SELECT id, nome FROM clientes LIMIT 10');

-- Deve falhar
SELECT execute_readonly_query('DELETE FROM clientes'); -- Erro
SELECT execute_readonly_query('SELECT * FROM auth.users'); -- Erro
SELECT execute_readonly_query('INSERT INTO clientes (nome) VALUES (''x'')'); -- Erro
```

**Integração:**
- [ ] Helena consegue executar queries de analytics
- [ ] Queries maliciosas são bloqueadas

### Definition of Done
- [ ] Function atualizada com search_path
- [ ] Validações de segurança funcionando
- [ ] Testes passando
- [ ] Helena testada

### Estimativa
1.5 horas

---

## Tarefa 2.2: Adicionar search_path em Functions Críticas

### Objetivo
Adicionar `SET search_path = public` em todas as functions com SECURITY DEFINER.

### Functions SECURITY DEFINER Identificadas

| Function | Risco | Prioridade |
|----------|-------|------------|
| `audit_outbound_coverage` | Alto | P0 |
| `audit_pipeline_inbound_coverage` | Alto | P0 |
| `audit_status_transition_coverage` | Alto | P0 |
| `buscar_candidatos_touch_reconciliation` | Médio | P1 |
| `chip_*` (12 functions) | Médio | P1 |
| `get_*` (8 functions) | Médio | P1 |
| `reconcile_*` (3 functions) | Médio | P1 |
| Outras (10 functions) | Baixo | P2 |

### Implementação

Script para atualizar todas:

```sql
-- Migration: 20260210_fix_functions_search_path.sql

-- Template para cada function:
-- 1. Obter definição atual
-- 2. Adicionar SET search_path = public
-- 3. Recriar function

-- audit_outbound_coverage
CREATE OR REPLACE FUNCTION audit_outbound_coverage(
    p_start timestamp with time zone,
    p_end timestamp with time zone
)
RETURNS TABLE(...) -- manter assinatura original
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
-- corpo original
$$;

-- chip_calcular_taxa_delivery
CREATE OR REPLACE FUNCTION chip_calcular_taxa_delivery(
    p_chip_id uuid,
    p_dias integer DEFAULT 7
)
RETURNS numeric
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
-- corpo original
$$;

-- ... repetir para todas as 37 functions
```

### Script de Geração

```sql
-- Gerar lista de functions para corrigir
SELECT
    p.proname as function_name,
    pg_get_functiondef(p.oid) as current_def
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
AND p.prosecdef = true  -- SECURITY DEFINER
AND NOT EXISTS (
    SELECT 1 FROM pg_proc_info
    WHERE proconfig @> ARRAY['search_path=public']
)
ORDER BY p.proname;
```

### Testes Obrigatórios

**Unitários:**
```sql
-- Verificar search_path está configurado
SELECT proname, proconfig
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
AND prosecdef = true;
-- Todas devem ter 'search_path=public' em proconfig
```

**Integração:**
- [ ] Jobs de auditoria funcionando
- [ ] Functions de chip funcionando
- [ ] Reconciliation funcionando

### Definition of Done
- [ ] Todas as 37 functions atualizadas
- [ ] Query de verificação confirma search_path
- [ ] Jobs agendados testados

### Estimativa
1.5 horas

---

## Tarefa 2.3: Documentar Functions SECURITY DEFINER

### Objetivo
Criar documentação explicando por que cada function usa SECURITY DEFINER e quais as implicações.

### Implementação

Criar arquivo de documentação:

```markdown
# docs/arquitetura/functions-security.md

## Functions com SECURITY DEFINER

### O que é SECURITY DEFINER?

Functions com SECURITY DEFINER executam com os privilégios do usuário que CRIOU a function (geralmente postgres/supabase_admin), não do usuário que EXECUTA.

### Quando usar?

- Function precisa acessar dados que o caller não tem permissão
- Function precisa bypassar RLS intencionalmente
- Function é chamada apenas pelo backend (service_role)

### Riscos

1. **SQL Injection**: Se a function aceita input dinâmico
2. **Search Path**: Atacante pode criar objetos maliciosos
3. **Privilege Escalation**: Caller ganha privilégios temporários

### Mitigações Obrigatórias

1. `SET search_path = public` em TODA function SECURITY DEFINER
2. Validar inputs antes de usar em SQL dinâmico
3. Usar `quote_ident()` e `quote_literal()` para interpolação
4. Limitar escopo ao mínimo necessário

### Inventário de Functions SECURITY DEFINER

| Function | Propósito | Justificativa | Revisado |
|----------|-----------|---------------|----------|
| execute_readonly_query | Helena SQL | Bypass RLS para analytics | 2026-02-10 |
| chip_* | Métricas chips | Bypass RLS para agregação | 2026-02-10 |
| audit_* | Auditoria | Acesso cross-table | 2026-02-10 |
| reconcile_* | Reconciliação | Acesso cross-table | 2026-02-10 |
```

### Testes Obrigatórios

N/A (documentação)

### Definition of Done
- [ ] Documentação criada
- [ ] Todas as functions SECURITY DEFINER listadas
- [ ] Link no README de arquitetura

### Estimativa
30 minutos (parcialmente feito durante tarefas anteriores)

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| 2.1 execute_readonly_query | 1.5h | Crítico |
| 2.2 search_path em functions | 1.5h | Alto |
| 2.3 Documentação | 0.5h | Baixo |
| **Total** | **3.5h** | |

## Validação Final do Épico

```sql
-- Verificar que todas as SECURITY DEFINER têm search_path
SELECT proname
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
AND prosecdef = true
AND NOT (proconfig @> ARRAY['search_path=public']);
-- Deve retornar vazio

-- Verificar Supabase Advisor
-- mcp__supabase__get_advisors(type='security')
-- Deve ter 0 findings de "function_search_path_mutable"
```
