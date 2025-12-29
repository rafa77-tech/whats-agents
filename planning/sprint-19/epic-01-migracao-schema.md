# E01: Migracao de Schema - Valor Flexivel

## Objetivo

Adicionar suporte a valores flexiveis (fixo, a combinar, faixa) nas tabelas `vagas_grupo` e `vagas`.

## Escopo

### Incluido
- Adicionar colunas `valor_minimo`, `valor_maximo`, `valor_tipo`
- Migrar dados existentes para novo modelo
- Criar constraint de validacao

### Excluido
- Alteracao de codigo (proximo epico)
- Migracao de dados historicos pre-existentes

---

## Tarefas

### T01: Criar migracao para tabela `vagas_grupo`

**Arquivo:** `supabase/migrations/YYYYMMDD_add_valor_flexivel_vagas_grupo.sql`

**SQL:**
```sql
-- Adicionar novos campos de valor flexivel
ALTER TABLE vagas_grupo
ADD COLUMN IF NOT EXISTS valor_minimo INTEGER,
ADD COLUMN IF NOT EXISTS valor_maximo INTEGER,
ADD COLUMN IF NOT EXISTS valor_tipo TEXT DEFAULT 'fixo';

-- Constraint para valores validos de valor_tipo
ALTER TABLE vagas_grupo
ADD CONSTRAINT chk_valor_tipo
CHECK (valor_tipo IN ('fixo', 'a_combinar', 'faixa'));

-- Indice para queries por tipo de valor
CREATE INDEX IF NOT EXISTS idx_vagas_grupo_valor_tipo
ON vagas_grupo(valor_tipo);

-- Comentarios
COMMENT ON COLUMN vagas_grupo.valor_minimo IS 'Valor minimo da faixa (quando valor_tipo = faixa)';
COMMENT ON COLUMN vagas_grupo.valor_maximo IS 'Valor maximo da faixa (quando valor_tipo = faixa)';
COMMENT ON COLUMN vagas_grupo.valor_tipo IS 'Tipo de valor: fixo, a_combinar, faixa';
```

**DoD (Definition of Done):**
- [ ] Migracao criada e testada localmente
- [ ] Migracao aplicada no Supabase via MCP
- [ ] Colunas visiveis no schema
- [ ] Constraint funcionando (testar insert invalido)
- [ ] Indice criado

**Criterios de Aceite:**
1. `INSERT INTO vagas_grupo (valor_tipo) VALUES ('invalido')` deve falhar
2. `SELECT * FROM vagas_grupo WHERE valor_tipo = 'a_combinar'` deve funcionar
3. Dados existentes nao devem ser afetados

---

### T02: Migrar dados existentes em `vagas_grupo`

**Arquivo:** `supabase/migrations/YYYYMMDD_migrate_valor_existente_vagas_grupo.sql`

**SQL:**
```sql
-- Migrar vagas existentes para novo modelo
-- Regra: se tem valor, e fixo; se nao tem, assumir a_combinar

UPDATE vagas_grupo
SET valor_tipo = CASE
    WHEN valor IS NOT NULL AND valor > 0 THEN 'fixo'
    ELSE 'a_combinar'
END
WHERE valor_tipo IS NULL OR valor_tipo = 'fixo';

-- Estatisticas pos-migracao
SELECT
    valor_tipo,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentual
FROM vagas_grupo
GROUP BY valor_tipo;
```

**DoD:**
- [ ] Migracao aplicada
- [ ] Estatisticas conferidas
- [ ] Nenhum registro com valor_tipo NULL

**Criterios de Aceite:**
1. Todas as vagas com `valor > 0` devem ter `valor_tipo = 'fixo'`
2. Todas as vagas com `valor IS NULL` devem ter `valor_tipo = 'a_combinar'`
3. Query `SELECT COUNT(*) FROM vagas_grupo WHERE valor_tipo IS NULL` retorna 0

---

### T03: Criar migracao para tabela `vagas`

**Arquivo:** `supabase/migrations/YYYYMMDD_add_valor_flexivel_vagas.sql`

**SQL:**
```sql
-- Adicionar novos campos de valor flexivel na tabela principal
ALTER TABLE vagas
ADD COLUMN IF NOT EXISTS valor_minimo INTEGER,
ADD COLUMN IF NOT EXISTS valor_maximo INTEGER,
ADD COLUMN IF NOT EXISTS valor_tipo TEXT DEFAULT 'fixo';

-- Constraint
ALTER TABLE vagas
ADD CONSTRAINT chk_vagas_valor_tipo
CHECK (valor_tipo IN ('fixo', 'a_combinar', 'faixa'));

-- Indice
CREATE INDEX IF NOT EXISTS idx_vagas_valor_tipo
ON vagas(valor_tipo);

-- Comentarios
COMMENT ON COLUMN vagas.valor_minimo IS 'Valor minimo da faixa (quando valor_tipo = faixa)';
COMMENT ON COLUMN vagas.valor_maximo IS 'Valor maximo da faixa (quando valor_tipo = faixa)';
COMMENT ON COLUMN vagas.valor_tipo IS 'Tipo de valor: fixo, a_combinar, faixa';
```

**DoD:**
- [ ] Migracao criada e aplicada
- [ ] Colunas visiveis no schema
- [ ] Constraint funcionando

---

### T04: Migrar dados existentes em `vagas`

**Arquivo:** `supabase/migrations/YYYYMMDD_migrate_valor_existente_vagas.sql`

**SQL:**
```sql
-- Migrar vagas existentes
UPDATE vagas
SET valor_tipo = CASE
    WHEN valor IS NOT NULL AND valor > 0 THEN 'fixo'
    ELSE 'a_combinar'
END
WHERE valor_tipo IS NULL OR valor_tipo = 'fixo';
```

**DoD:**
- [ ] Migracao aplicada
- [ ] Dados consistentes

---

### T05: Criar funcao de validacao

**Arquivo:** `supabase/migrations/YYYYMMDD_fn_validar_valor_vaga.sql`

**SQL:**
```sql
-- Funcao para validar consistencia de valor
CREATE OR REPLACE FUNCTION validar_valor_vaga()
RETURNS TRIGGER AS $$
BEGIN
    -- Se tipo e fixo, valor deve existir
    IF NEW.valor_tipo = 'fixo' AND (NEW.valor IS NULL OR NEW.valor <= 0) THEN
        RAISE EXCEPTION 'valor_tipo fixo requer valor > 0';
    END IF;

    -- Se tipo e faixa, pelo menos minimo ou maximo deve existir
    IF NEW.valor_tipo = 'faixa' AND NEW.valor_minimo IS NULL AND NEW.valor_maximo IS NULL THEN
        RAISE EXCEPTION 'valor_tipo faixa requer valor_minimo ou valor_maximo';
    END IF;

    -- Se tipo e a_combinar, valor deve ser null
    IF NEW.valor_tipo = 'a_combinar' AND NEW.valor IS NOT NULL AND NEW.valor > 0 THEN
        -- Nao bloquear, apenas ajustar para consistencia
        NEW.valor_tipo := 'fixo';
    END IF;

    -- Validar faixa coerente
    IF NEW.valor_minimo IS NOT NULL AND NEW.valor_maximo IS NOT NULL THEN
        IF NEW.valor_minimo > NEW.valor_maximo THEN
            RAISE EXCEPTION 'valor_minimo nao pode ser maior que valor_maximo';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar trigger em vagas_grupo
DROP TRIGGER IF EXISTS trg_validar_valor_vagas_grupo ON vagas_grupo;
CREATE TRIGGER trg_validar_valor_vagas_grupo
BEFORE INSERT OR UPDATE ON vagas_grupo
FOR EACH ROW EXECUTE FUNCTION validar_valor_vaga();

-- Aplicar trigger em vagas
DROP TRIGGER IF EXISTS trg_validar_valor_vagas ON vagas;
CREATE TRIGGER trg_validar_valor_vagas
BEFORE INSERT OR UPDATE ON vagas
FOR EACH ROW EXECUTE FUNCTION validar_valor_vaga();
```

**DoD:**
- [ ] Funcao criada
- [ ] Triggers aplicados
- [ ] Testes de validacao passando

**Criterios de Aceite:**
1. Insert com `valor_tipo='fixo', valor=NULL` deve falhar
2. Insert com `valor_tipo='faixa', valor_minimo=NULL, valor_maximo=NULL` deve falhar
3. Insert com `valor_tipo='faixa', valor_minimo=2000, valor_maximo=1000` deve falhar
4. Insert com `valor_tipo='a_combinar', valor=1800` deve ajustar para `valor_tipo='fixo'`

---

## Arquivos Modificados

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `migrations/YYYYMMDD_add_valor_flexivel_vagas_grupo.sql` | Criar | Adiciona colunas |
| `migrations/YYYYMMDD_migrate_valor_existente_vagas_grupo.sql` | Criar | Migra dados |
| `migrations/YYYYMMDD_add_valor_flexivel_vagas.sql` | Criar | Adiciona colunas |
| `migrations/YYYYMMDD_migrate_valor_existente_vagas.sql` | Criar | Migra dados |
| `migrations/YYYYMMDD_fn_validar_valor_vaga.sql` | Criar | Funcao + triggers |

---

## Rollback

Em caso de problemas, executar:

```sql
-- Remover triggers
DROP TRIGGER IF EXISTS trg_validar_valor_vagas_grupo ON vagas_grupo;
DROP TRIGGER IF EXISTS trg_validar_valor_vagas ON vagas;
DROP FUNCTION IF EXISTS validar_valor_vaga();

-- Remover constraints
ALTER TABLE vagas_grupo DROP CONSTRAINT IF EXISTS chk_valor_tipo;
ALTER TABLE vagas DROP CONSTRAINT IF EXISTS chk_vagas_valor_tipo;

-- Remover indices
DROP INDEX IF EXISTS idx_vagas_grupo_valor_tipo;
DROP INDEX IF EXISTS idx_vagas_valor_tipo;

-- Remover colunas
ALTER TABLE vagas_grupo
DROP COLUMN IF EXISTS valor_minimo,
DROP COLUMN IF EXISTS valor_maximo,
DROP COLUMN IF EXISTS valor_tipo;

ALTER TABLE vagas
DROP COLUMN IF EXISTS valor_minimo,
DROP COLUMN IF EXISTS valor_maximo,
DROP COLUMN IF EXISTS valor_tipo;
```

---

## DoD do Epico

- [ ] T01 completa - Colunas em vagas_grupo
- [ ] T02 completa - Dados migrados em vagas_grupo
- [ ] T03 completa - Colunas em vagas
- [ ] T04 completa - Dados migrados em vagas
- [ ] T05 completa - Validacao funcionando
- [ ] Nenhum erro em producao
- [ ] Schema documentado

---

## Checklist de Validacao

```sql
-- Verificar estrutura
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name IN ('vagas_grupo', 'vagas')
AND column_name IN ('valor', 'valor_minimo', 'valor_maximo', 'valor_tipo')
ORDER BY table_name, column_name;

-- Verificar distribuicao
SELECT
    'vagas_grupo' as tabela,
    valor_tipo,
    COUNT(*) as total
FROM vagas_grupo
GROUP BY valor_tipo
UNION ALL
SELECT
    'vagas' as tabela,
    valor_tipo,
    COUNT(*) as total
FROM vagas
GROUP BY valor_tipo;

-- Verificar constraints
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname LIKE '%valor_tipo%';
```
