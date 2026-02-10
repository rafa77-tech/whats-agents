# ÉPICO 3: Índices em Foreign Keys

## Contexto

PostgreSQL **NÃO cria índices automaticamente em colunas FK**. O Database Review identificou **31 FKs sem índice**, causando:

1. **JOINs lentos**: Sem índice, o banco faz Seq Scan
2. **CASCADE DELETE lento**: Precisa varrer tabela inteira
3. **Locks prolongados**: Operações demoram mais

As tabelas mais críticas são `vagas_grupo` (64k rows) e `vagas_grupo_fontes` (36k rows).

**Severidade:** MÉDIA - impacto em performance, não em segurança

## Escopo

- **Incluído:**
  - Criar índices em FKs de tabelas com >1k rows (prioridade alta)
  - Criar índices em FKs de tabelas menores (prioridade média)
  - Usar CREATE INDEX CONCURRENTLY para não bloquear

- **Excluído:**
  - Criar índices compostos (avaliar em sprint futura)
  - Refatorar queries (fora do escopo)

---

## Tarefa 3.1: Índices em Tabelas Grandes (>10k rows)

### Objetivo
Criar índices nas FKs das maiores tabelas para impacto imediato em performance.

### FKs Prioritárias

| Tabela | Coluna FK | Rows | Índice a criar |
|--------|-----------|------|----------------|
| `vagas_grupo` | `contato_responsavel_id` | 64k | idx_vagas_grupo_contato_resp |
| `vagas_grupo` | `duplicada_de` | 64k | idx_vagas_grupo_duplicada |
| `vagas_grupo` | `forma_recebimento_id` | 64k | idx_vagas_grupo_forma_receb |
| `vagas_grupo` | `setor_id` | 64k | idx_vagas_grupo_setor |
| `vagas_grupo` | `tipos_vaga_id` | 64k | idx_vagas_grupo_tipo |
| `vagas_grupo` | `vaga_importada_id` | 64k | idx_vagas_grupo_importada |
| `vagas_grupo_fontes` | `contato_id` | 36k | idx_vgf_contato |

### Implementação

```sql
-- Migration: 20260210_create_fk_indexes_large_tables.sql

-- vagas_grupo (64k rows) - 6 índices
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_contato_resp
ON vagas_grupo(contato_responsavel_id)
WHERE contato_responsavel_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_duplicada
ON vagas_grupo(duplicada_de)
WHERE duplicada_de IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_forma_receb
ON vagas_grupo(forma_recebimento_id)
WHERE forma_recebimento_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_setor
ON vagas_grupo(setor_id)
WHERE setor_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_tipo
ON vagas_grupo(tipos_vaga_id)
WHERE tipos_vaga_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_grupo_importada
ON vagas_grupo(vaga_importada_id)
WHERE vaga_importada_id IS NOT NULL;

-- vagas_grupo_fontes (36k rows) - 1 índice
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vgf_contato
ON vagas_grupo_fontes(contato_id)
WHERE contato_id IS NOT NULL;
```

### Notas sobre CONCURRENTLY

- **Não bloqueia writes** na tabela
- **Mais lento** que índice normal
- **Não pode rodar em transação** (cada comando separado)
- **Pode falhar** se houver problema - verificar com `\d tabela`

### Verificação Pós-Criação

```sql
-- Verificar índices criados
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'vagas_grupo'
AND indexname LIKE 'idx_vagas_grupo_%';

-- Verificar tamanho dos índices
SELECT
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE relname = 'vagas_grupo';
```

### Rollback

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_contato_resp;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_duplicada;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_forma_receb;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_setor;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_tipo;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_grupo_importada;
DROP INDEX CONCURRENTLY IF EXISTS idx_vgf_contato;
```

### Testes Obrigatórios

**Performance:**
```sql
-- Antes: anotar tempo
EXPLAIN ANALYZE
SELECT vg.*, f.nome as forma_recebimento
FROM vagas_grupo vg
JOIN formas_recebimento f ON f.id = vg.forma_recebimento_id
WHERE vg.created_at > NOW() - INTERVAL '7 days';

-- Depois: comparar tempo (deve usar Index Scan)
```

**Integração:**
- [ ] Pipeline de grupos funcionando
- [ ] Dashboard de vagas carregando

### Definition of Done
- [ ] 7 índices criados
- [ ] EXPLAIN mostra Index Scan (não Seq Scan)
- [ ] Pipeline testado

### Estimativa
45 minutos

---

## Tarefa 3.2: Índices em Tabelas Médias (1k-10k rows)

### Objetivo
Criar índices nas FKs de tabelas médias.

### FKs Identificadas

| Tabela | Coluna FK | Rows | Índice |
|--------|-----------|------|--------|
| `vagas` | `periodo_id` | 7.6k | idx_vagas_periodo |
| `vagas` | `setor_id` | 7.6k | idx_vagas_setor |
| `vagas` | `tipos_vaga_id` | 7.6k | idx_vagas_tipos |
| `vagas` | `forma_recebimento_id` | 7.6k | idx_vagas_forma_receb |
| `contatos_grupo` | - | 2.7k | (já indexado) |

### Implementação

```sql
-- Migration: 20260210_create_fk_indexes_medium_tables.sql

-- vagas (7.6k rows)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_periodo
ON vagas(periodo_id)
WHERE periodo_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_setor
ON vagas(setor_id)
WHERE setor_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_tipos
ON vagas(tipos_vaga_id)
WHERE tipos_vaga_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vagas_forma_receb
ON vagas(forma_recebimento_id)
WHERE forma_recebimento_id IS NOT NULL;
```

### Rollback

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_periodo;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_setor;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_tipos;
DROP INDEX CONCURRENTLY IF EXISTS idx_vagas_forma_receb;
```

### Testes Obrigatórios

- [ ] Busca de vagas usa índices
- [ ] Dashboard de vagas performando

### Definition of Done
- [ ] 4 índices criados
- [ ] EXPLAIN confirma uso

### Estimativa
30 minutos

---

## Tarefa 3.3: Índices em Tabelas Pequenas (<1k rows)

### Objetivo
Criar índices nas FKs restantes. Impacto menor, mas mantém consistência.

### FKs Identificadas

| Tabela | Coluna FK |
|--------|-----------|
| `conversations` | `execucao_campanha_id` |
| `grupos_whatsapp` | `hospital_id` |
| `diretrizes` | `vaga_id` |
| `diretrizes_contextuais` | `especialidade_id`, `hospital_id` |
| `doctor_context` | `memoria_substituta_id` |
| `feedbacks_gestor` | `conversa_id`, `interacao_id` |
| `group_entry_queue` | `link_id` |
| `group_links` | `chip_id` |
| `mensagens_fora_horario` | `conversa_id` |
| `migracao_agendada` | `chip_antigo_id`, `chip_novo_id` |
| `orchestrator_operations` | `chip_destino_id` |
| `prompts_historico` | `prompt_id` |
| `sugestoes_prompt` | `avaliacao_id` |
| `conhecimento_hospitais` | `pedido_ajuda_id` |
| `conversation_chips` | `migrated_from` |
| `conversation_insights` | `interaction_id` |

### Implementação

```sql
-- Migration: 20260210_create_fk_indexes_small_tables.sql

-- conversations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_execucao
ON conversations(execucao_campanha_id)
WHERE execucao_campanha_id IS NOT NULL;

-- grupos_whatsapp
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_grupos_hospital
ON grupos_whatsapp(hospital_id)
WHERE hospital_id IS NOT NULL;

-- diretrizes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_diretrizes_vaga
ON diretrizes(vaga_id)
WHERE vaga_id IS NOT NULL;

-- diretrizes_contextuais
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dir_ctx_especialidade
ON diretrizes_contextuais(especialidade_id)
WHERE especialidade_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dir_ctx_hospital
ON diretrizes_contextuais(hospital_id)
WHERE hospital_id IS NOT NULL;

-- doctor_context
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_doc_ctx_memoria
ON doctor_context(memoria_substituta_id)
WHERE memoria_substituta_id IS NOT NULL;

-- feedbacks_gestor
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feedbacks_conversa
ON feedbacks_gestor(conversa_id)
WHERE conversa_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feedbacks_interacao
ON feedbacks_gestor(interacao_id)
WHERE interacao_id IS NOT NULL;

-- group_entry_queue
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_geq_link
ON group_entry_queue(link_id);

-- group_links
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_group_links_chip
ON group_links(chip_id)
WHERE chip_id IS NOT NULL;

-- mensagens_fora_horario
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_msg_fora_conversa
ON mensagens_fora_horario(conversa_id)
WHERE conversa_id IS NOT NULL;

-- migracao_agendada
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_migracao_chip_antigo
ON migracao_agendada(chip_antigo_id)
WHERE chip_antigo_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_migracao_chip_novo
ON migracao_agendada(chip_novo_id);

-- orchestrator_operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_orch_chip_destino
ON orchestrator_operations(chip_destino_id)
WHERE chip_destino_id IS NOT NULL;

-- prompts_historico
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_prompts_hist_prompt
ON prompts_historico(prompt_id)
WHERE prompt_id IS NOT NULL;

-- sugestoes_prompt
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sug_avaliacao
ON sugestoes_prompt(avaliacao_id)
WHERE avaliacao_id IS NOT NULL;

-- conhecimento_hospitais
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conh_hosp_pedido
ON conhecimento_hospitais(pedido_ajuda_id)
WHERE pedido_ajuda_id IS NOT NULL;

-- conversation_chips
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conv_chips_migrated
ON conversation_chips(migrated_from)
WHERE migrated_from IS NOT NULL;

-- conversation_insights
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conv_insights_interaction
ON conversation_insights(interaction_id)
WHERE interaction_id IS NOT NULL;
```

### Rollback

```sql
-- Lista de DROP para cada índice criado
DROP INDEX CONCURRENTLY IF EXISTS idx_conversations_execucao;
DROP INDEX CONCURRENTLY IF EXISTS idx_grupos_hospital;
-- ... etc
```

### Testes Obrigatórios

- [ ] Query de verificação mostra todos índices
- [ ] Nenhum erro nos logs

### Definition of Done
- [ ] 20 índices criados
- [ ] Query de verificação confirma

### Estimativa
45 minutos

---

## Resumo do Épico

| Tarefa | Índices | Estimativa |
|--------|---------|------------|
| 3.1 Tabelas grandes | 7 | 45min |
| 3.2 Tabelas médias | 4 | 30min |
| 3.3 Tabelas pequenas | 20 | 45min |
| **Total** | **31** | **2h** |

## Validação Final do Épico

```sql
-- Verificar que TODAS as FKs têm índice
WITH fk_columns AS (
    SELECT tc.table_name, kcu.column_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
),
indexed_columns AS (
    SELECT t.relname as table_name, a.attname as column_name
    FROM pg_class t
    JOIN pg_index ix ON t.oid = ix.indrelid
    JOIN pg_attribute a ON t.oid = a.attrelid AND a.attnum = ANY(ix.indkey)
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE n.nspname = 'public'
)
SELECT fk.table_name, fk.column_name
FROM fk_columns fk
LEFT JOIN indexed_columns ic
    ON fk.table_name = ic.table_name
    AND fk.column_name = ic.column_name
WHERE ic.column_name IS NULL;

-- Deve retornar vazio
```
