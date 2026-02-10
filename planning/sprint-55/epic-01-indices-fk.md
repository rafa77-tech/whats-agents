# ÉPICO 01: Índices em Foreign Keys

## Contexto

PostgreSQL **não cria índices automaticamente** em Foreign Keys. O NFR Assessment identificou 39 FKs sem índice, causando:
- JOINs lentos
- DELETE cascading lento
- Locks prolongados em tabelas pai

Este épico cria índices nas FKs de **alto impacto** (hot paths do sistema).

## Escopo

- **Incluído**: Criar índices nas 9 FKs de alto impacto identificadas
- **Excluído**: FKs de baixo impacto (tabelas de lookup, config) - backlog futuro

---

## Tarefa T01.1: Migration de Índices Críticos

### Objetivo

Criar migration que adiciona índices nas FKs mais utilizadas pelo sistema.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | Migration via MCP Supabase |

### Implementação

```sql
-- Migration: add_indexes_to_critical_fks
-- Descrição: Adiciona índices em FKs de alto impacto para melhorar performance

-- FKs de ALTO impacto (hot paths)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_events_conversation_id
    ON business_events(conversation_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_events_interaction_id
    ON business_events(interaction_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interacoes_parent_id
    ON interacoes(parent_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fila_mensagens_conversa_id
    ON fila_mensagens(conversa_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policy_events_conversation_id
    ON policy_events(conversation_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_policy_events_interaction_id
    ON policy_events(interaction_id);

-- FKs de MÉDIO impacto (queries frequentes)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_cliente_id
    ON vagas(cliente_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_campanha_id
    ON conversations(campanha_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_contatos_grupo_cliente_id
    ON contatos_grupo(cliente_id);
```

**Nota:** `CREATE INDEX CONCURRENTLY` não bloqueia writes, seguro para produção.

### Testes Obrigatórios

**Verificação pós-migration:**
- [ ] Todos os índices existem: `SELECT indexname FROM pg_indexes WHERE indexname LIKE 'idx_%'`
- [ ] Queries com JOIN nas tabelas afetadas usam os índices: `EXPLAIN ANALYZE`
- [ ] Nenhum erro no log do Supabase

**Rollback (se necessário):**
```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_business_events_conversation_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_business_events_interaction_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_interacoes_parent_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_fila_mensagens_conversa_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_policy_events_conversation_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_policy_events_interaction_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_cliente_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_conversations_campanha_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_contatos_grupo_cliente_id;
```

### Definition of Done

- [ ] Migration aplicada via `mcp__supabase__apply_migration`
- [ ] Todos os 9 índices existem no banco
- [ ] Query de verificação retorna índices esperados
- [ ] Nenhum erro no dashboard de logs do Supabase

### Estimativa

1 hora

---

## Tarefa T01.2: Validação de Performance

### Objetivo

Verificar que os índices estão sendo utilizados e melhoraram a performance.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `docs/auditorias/validacao-indices-sprint55.md` |

### Implementação

Executar queries de diagnóstico e documentar resultados:

```sql
-- 1. Verificar que índices existem
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname LIKE 'idx_%'
    AND schemaname = 'public'
ORDER BY tablename;

-- 2. Verificar uso dos índices (rodar após algumas horas/dias)
SELECT
    relname as table_name,
    indexrelname as index_name,
    idx_scan as times_used,
    idx_tup_read as rows_read
FROM pg_stat_user_indexes
WHERE indexname LIKE 'idx_business_events%'
   OR indexname LIKE 'idx_interacoes%'
   OR indexname LIKE 'idx_fila_mensagens%'
   OR indexname LIKE 'idx_policy_events%'
   OR indexname LIKE 'idx_vagas%'
   OR indexname LIKE 'idx_conversations%'
   OR indexname LIKE 'idx_contatos_grupo%'
ORDER BY idx_scan DESC;

-- 3. Exemplo de EXPLAIN em query comum
EXPLAIN ANALYZE
SELECT * FROM business_events
WHERE conversation_id = 'uuid-exemplo'
ORDER BY created_at DESC
LIMIT 10;
```

### Testes Obrigatórios

- [ ] Query 1 retorna todos os 9 índices criados
- [ ] Query 2 mostra `idx_scan > 0` após uso em produção
- [ ] Query 3 mostra "Index Scan" ao invés de "Seq Scan"

### Definition of Done

- [ ] Documento de validação criado
- [ ] Queries executadas e resultados documentados
- [ ] Evidência de que índices estão sendo utilizados

### Estimativa

1 hora

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| T01.1: Migration de índices | 1h | Baixo (CONCURRENTLY) |
| T01.2: Validação de performance | 1h | Baixo |
| **Total** | **2h** | |

## Ordem de Execução

1. T01.1 - Criar e aplicar migration
2. T01.2 - Validar após algumas horas de uso

## Paralelizável

- Nenhuma tarefa paralelizável neste épico (sequencial)
