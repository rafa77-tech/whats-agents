# ÉPICO 4: Limpeza de Índices Não Utilizados

## Contexto

O Database Review identificou **30 índices com 0 scans**, ocupando aproximadamente **15 MB**. Índices não utilizados:

1. **Ocupam espaço** em disco
2. **Degradam writes** (INSERT/UPDATE/DELETE precisam atualizar índices)
3. **Consomem memória** do buffer pool

Porém, precisamos ter **cuidado**: alguns índices podem ser usados apenas em:
- Reports mensais
- Migrations
- Queries ad-hoc de análise
- Backups/restores

**Severidade:** BAIXA - otimização, não problema

## Escopo

- **Incluído:**
  - Analisar período de uso (30+ dias)
  - Identificar índices seguros para remover
  - Fazer backup do DDL antes de remover
  - Remover candidatos confirmados

- **Excluído:**
  - Remover índices de PKs (nunca)
  - Remover índices de UNIQUE constraints
  - Remover sem backup do DDL

---

## Tarefa 4.1: Análise de Uso de Índices

### Objetivo
Analisar estatísticas de uso dos 30 índices identificados e classificar em: remover, manter, avaliar.

### Índices Identificados (0 scans)

| Índice | Tabela | Tamanho | Classificação |
|--------|--------|---------|---------------|
| `mensagens_grupo_message_id_key` | mensagens_grupo | 2.1 MB | AVALIAR - UNIQUE |
| `vagas_grupo_fontes_pkey` | vagas_grupo_fontes | 1.5 MB | MANTER - PK |
| `idx_clientes_email` | clientes | 1.4 MB | AVALIAR |
| `idx_vagas_grupo_hospital` | vagas_grupo | 1.4 MB | REMOVER |
| `idx_mensagens_grupo_timestamp` | mensagens_grupo | 1.3 MB | AVALIAR |
| `idx_log_cliente_id` | clientes_log | 1.2 MB | REMOVER |
| `idx_log_timestamp` | clientes_log | 1.2 MB | REMOVER |
| `idx_mensagens_grupo_ofertas` | mensagens_grupo | 840 KB | AVALIAR |
| `clientes_log_pkey` | clientes_log | 672 KB | MANTER - PK |
| `idx_mensagens_grupo_contato` | mensagens_grupo | 512 KB | AVALIAR |
| `idx_hospitais_alias_trgm` | hospitais_alias | 480 KB | MANTER - trgm |
| `idx_vagas_grupo_fontes_grupo` | vagas_grupo_fontes | 376 KB | REMOVER |
| `idx_clientes_ultima_abertura` | clientes | 360 KB | AVALIAR |
| `idx_clientes_estado` | clientes | 272 KB | REMOVER |
| `idx_clientes_crm` | clientes | 264 KB | AVALIAR |
| `idx_clientes_opted_out` | clientes | 256 KB | MANTER - usado em campanhas |
| `idx_clientes_status_telefone` | clientes | 224 KB | MANTER - usado em validação |
| Outros (13 índices) | - | <200 KB cada | AVALIAR |

### Implementação - Script de Análise

```sql
-- Salvar estatísticas atuais para comparação futura
CREATE TABLE IF NOT EXISTS _idx_usage_snapshot AS
SELECT
    schemaname,
    relname as table_name,
    indexrelname as index_name,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_relation_size(indexrelid) as size_bytes,
    NOW() as snapshot_at
FROM pg_stat_user_indexes
WHERE schemaname = 'public';

-- Query para decisão
SELECT
    indexrelname,
    relname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size,
    idx_scan,
    CASE
        WHEN indexrelname LIKE '%_pkey' THEN 'MANTER - PK'
        WHEN indexrelname LIKE '%_key' THEN 'AVALIAR - UNIQUE'
        WHEN indexrelname LIKE '%_trgm' THEN 'MANTER - trgm'
        WHEN idx_scan = 0 AND pg_relation_size(indexrelid) > 500000 THEN 'CANDIDATO REMOÇÃO'
        ELSE 'AVALIAR'
    END as recomendacao
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Definition of Done
- [ ] Snapshot de estatísticas criado
- [ ] Classificação de cada índice documentada
- [ ] Lista de remoção aprovada

### Estimativa
30 minutos

---

## Tarefa 4.2: Backup de DDL dos Índices

### Objetivo
Antes de remover qualquer índice, salvar o DDL para possível recriação.

### Implementação

```sql
-- Gerar DDL de todos os índices candidatos
SELECT
    'CREATE INDEX ' || indexname || ' ON ' || tablename ||
    ' USING ' || indexdef || ';' as ddl
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname IN (
    'idx_vagas_grupo_hospital',
    'idx_log_cliente_id',
    'idx_log_timestamp',
    'idx_vagas_grupo_fontes_grupo',
    'idx_clientes_estado'
);
```

Salvar resultado em: `docs/arquitetura/indices-removidos-2026-02-10.sql`

### Definition of Done
- [ ] Arquivo de backup criado
- [ ] DDL validado (pode recriar)

### Estimativa
15 minutos

---

## Tarefa 4.3: Remover Índices Confirmados

### Objetivo
Remover os índices classificados como "REMOVER" após backup.

### Índices para Remover (Confirmados)

| Índice | Tabela | Tamanho | Motivo |
|--------|--------|---------|--------|
| `idx_vagas_grupo_hospital` | vagas_grupo | 1.4 MB | FK já indexada por outro idx |
| `idx_log_cliente_id` | clientes_log | 1.2 MB | Tabela de log, não consultada |
| `idx_log_timestamp` | clientes_log | 1.2 MB | Tabela de log, não consultada |
| `idx_vagas_grupo_fontes_grupo` | vagas_grupo_fontes | 376 KB | FK já indexada |
| `idx_clientes_estado` | clientes | 272 KB | Raramente usado em WHERE |

**Economia estimada:** ~4.5 MB

### Implementação

```sql
-- Migration: 20260210_drop_unused_indexes.sql

-- ATENÇÃO: Só executar após backup do DDL

DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_hospital;
DROP INDEX CONCURRENTLY IF EXISTS idx_log_cliente_id;
DROP INDEX CONCURRENTLY IF EXISTS idx_log_timestamp;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_fontes_grupo;
DROP INDEX CONCURRENTLY IF EXISTS idx_clientes_estado;
```

### Rollback

Usar o arquivo de backup criado na Tarefa 4.2.

### Testes Obrigatórios

**Monitoramento:**
- [ ] Verificar que não houve aumento de Seq Scans após remoção
- [ ] Monitorar performance por 24h

### Definition of Done
- [ ] Índices removidos
- [ ] Nenhuma degradação de performance
- [ ] Documentação atualizada

### Estimativa
30 minutos

---

## Tarefa 4.4: Avaliar Índices Duvidosos

### Objetivo
Decidir sobre índices na categoria "AVALIAR".

### Processo de Avaliação

Para cada índice duvidoso:

1. **Verificar se é UNIQUE**: Se sim, manter (integridade)
2. **Verificar uso em código**: `grep -r "column_name" app/`
3. **Verificar uso em queries manuais**: Perguntar equipe
4. **Decidir**: Manter ou agendar remoção para sprint futura

### Índices para Avaliar

| Índice | Decisão Preliminar | Justificativa |
|--------|-------------------|---------------|
| `mensagens_grupo_message_id_key` | MANTER | UNIQUE - integridade |
| `idx_clientes_email` | MANTER | Usado em busca de médicos |
| `idx_mensagens_grupo_timestamp` | AVALIAR | Pode ser usado em reports |
| `idx_mensagens_grupo_ofertas` | MANTER | Usado no pipeline |
| `idx_mensagens_grupo_contato` | MANTER | JOIN com contatos |
| `idx_clientes_ultima_abertura` | AVALIAR | Pode ser obsoleto |
| `idx_clientes_crm` | MANTER | Busca por CRM |

### Definition of Done
- [ ] Cada índice avaliado
- [ ] Decisão documentada
- [ ] Backlog criado para remoções futuras

### Estimativa
45 minutos

---

## Resumo do Épico

| Tarefa | Estimativa |
|--------|------------|
| 4.1 Análise de uso | 30min |
| 4.2 Backup DDL | 15min |
| 4.3 Remover confirmados | 30min |
| 4.4 Avaliar duvidosos | 45min |
| **Total** | **2h** |

## Validação Final do Épico

```sql
-- Verificar índices removidos
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname IN (
    'idx_vagas_grupo_hospital',
    'idx_log_cliente_id',
    'idx_log_timestamp',
    'idx_vagas_grupo_fontes_grupo',
    'idx_clientes_estado'
);
-- Deve retornar vazio

-- Verificar espaço economizado
SELECT pg_size_pretty(
    (SELECT sum(pg_relation_size(indexrelid))
     FROM pg_stat_user_indexes
     WHERE schemaname = 'public')
) as total_index_size;
-- Comparar com antes (~85 MB -> ~80 MB)
```
