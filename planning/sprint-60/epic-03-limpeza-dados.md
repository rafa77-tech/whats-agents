# EPICO 3: Limpeza de Dados Existentes

## Contexto

Com 2.703 registros de hospital, apenas 851 nomes unicos, e ~200+ registros de lixo, o banco precisa de limpeza estruturada. Este epico cria as ferramentas de merge/delete e executa a limpeza em 3 tiers de risco crescente.

**Objetivo:** Deduplicar, remover lixo e consolidar hospitais existentes sem perder dados.

## Escopo

- **Incluido:**
  - Funcao SQL atomica de merge (`mesclar_hospitais`)
  - Tabela de auditoria (`hospital_merges`)
  - Funcao de delete seguro (zero FKs)
  - Wrappers Python
  - Execucao da limpeza em 3 tiers

- **Excluido:**
  - Interface de merge no dashboard (Epico 5)
  - Merge automatico por similaridade sem supervisao
  - Alterar schema de hospitais

---

## Tarefa 3.1: Criar funcao SQL `mesclar_hospitais()`

### Objetivo

Funcao atomica que transfere todas as referencias de um hospital duplicado para o principal, registra auditoria, e deleta o duplicado.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | Tabela `hospital_merges` + funcao `mesclar_hospitais()` via `apply_migration` |

### Implementacao

```sql
-- Tabela de auditoria
CREATE TABLE hospital_merges (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    principal_id UUID NOT NULL REFERENCES hospitais(id),
    duplicado_id UUID NOT NULL,  -- Sem FK pois sera deletado
    duplicado_nome TEXT NOT NULL,
    duplicado_cidade TEXT,
    vagas_migradas INT DEFAULT 0,
    vagas_grupo_migradas INT DEFAULT 0,
    eventos_migrados INT DEFAULT 0,
    alertas_migrados INT DEFAULT 0,
    grupos_migrados INT DEFAULT 0,
    conhecimento_migrado INT DEFAULT 0,
    diretrizes_migradas INT DEFAULT 0,
    bloqueios_migrados INT DEFAULT 0,
    aliases_migrados INT DEFAULT 0,
    executado_por TEXT NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Funcao de merge
CREATE OR REPLACE FUNCTION mesclar_hospitais(
    p_principal_id UUID,
    p_duplicado_id UUID,
    p_executado_por TEXT DEFAULT 'system'
) RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_principal RECORD;
    v_duplicado RECORD;
    v_counts JSONB;
    v_vagas INT;
    v_vagas_grupo INT;
    v_eventos INT;
    v_alertas INT;
    v_grupos INT;
    v_conhecimento INT;
    v_diretrizes INT;
    v_bloqueios INT;
    v_aliases INT;
BEGIN
    -- 1. Verificar que ambos existem
    SELECT * INTO v_principal FROM hospitais WHERE id = p_principal_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Hospital principal % nao encontrado', p_principal_id;
    END IF;

    SELECT * INTO v_duplicado FROM hospitais WHERE id = p_duplicado_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Hospital duplicado % nao encontrado', p_duplicado_id;
    END IF;

    IF p_principal_id = p_duplicado_id THEN
        RAISE EXCEPTION 'Hospital principal e duplicado sao o mesmo: %', p_principal_id;
    END IF;

    -- 2. Migrar vagas
    UPDATE vagas SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_vagas = ROW_COUNT;

    -- 3. Migrar vagas_grupo
    UPDATE vagas_grupo SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_vagas_grupo = ROW_COUNT;

    -- 4. Migrar business_events
    UPDATE business_events SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_eventos = ROW_COUNT;

    -- 5. Migrar business_alerts
    UPDATE business_alerts SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_alertas = ROW_COUNT;

    -- 6. Migrar grupos_whatsapp
    UPDATE grupos_whatsapp SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_grupos = ROW_COUNT;

    -- 7. Migrar conhecimento_hospitais
    UPDATE conhecimento_hospitais SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_conhecimento = ROW_COUNT;

    -- 8. Migrar diretrizes_contextuais
    UPDATE diretrizes_contextuais SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_diretrizes = ROW_COUNT;

    -- 9. Migrar hospitais_bloqueados
    UPDATE hospitais_bloqueados SET hospital_id = p_principal_id
    WHERE hospital_id = p_duplicado_id;
    GET DIAGNOSTICS v_bloqueios = ROW_COUNT;

    -- 10. Migrar aliases (ON CONFLICT para duplicatas)
    INSERT INTO hospitais_alias (hospital_id, alias_original, alias_normalizado, confianca, criado_por)
    SELECT p_principal_id, alias_original, alias_normalizado, confianca, 'merge'
    FROM hospitais_alias
    WHERE hospital_id = p_duplicado_id
    ON CONFLICT (alias_normalizado) DO NOTHING;
    GET DIAGNOSTICS v_aliases = ROW_COUNT;

    -- 11. Registrar auditoria
    INSERT INTO hospital_merges (
        principal_id, duplicado_id, duplicado_nome, duplicado_cidade,
        vagas_migradas, vagas_grupo_migradas, eventos_migrados,
        alertas_migrados, grupos_migrados, conhecimento_migrado,
        diretrizes_migradas, bloqueios_migrados, aliases_migrados,
        executado_por
    ) VALUES (
        p_principal_id, p_duplicado_id, v_duplicado.nome, v_duplicado.cidade,
        v_vagas, v_vagas_grupo, v_eventos,
        v_alertas, v_grupos, v_conhecimento,
        v_diretrizes, v_bloqueios, v_aliases,
        p_executado_por
    );

    -- 12. Deletar hospital duplicado (aliases em CASCADE)
    DELETE FROM hospitais WHERE id = p_duplicado_id;

    -- 13. Retornar contagens
    v_counts := jsonb_build_object(
        'principal_id', p_principal_id,
        'duplicado_id', p_duplicado_id,
        'duplicado_nome', v_duplicado.nome,
        'vagas_migradas', v_vagas,
        'vagas_grupo_migradas', v_vagas_grupo,
        'eventos_migrados', v_eventos,
        'alertas_migrados', v_alertas,
        'grupos_migrados', v_grupos,
        'conhecimento_migrado', v_conhecimento,
        'diretrizes_migradas', v_diretrizes,
        'bloqueios_migrados', v_bloqueios,
        'aliases_migrados', v_aliases
    );

    RETURN v_counts;
END;
$$;
```

**Garantias:**
- Transacao atomica — all-or-nothing
- Verifica existencia antes de operar
- Impede merge consigo mesmo
- Aliases com `ON CONFLICT` para evitar duplicata
- Auditoria completa com contagens
- Delete do duplicado apos migrar TUDO

### Testes Obrigatorios

**Unitarios (SQL):**
- [ ] Merge transfere vagas do duplicado para principal
- [ ] Merge transfere vagas_grupo
- [ ] Merge transfere business_events
- [ ] Merge transfere business_alerts
- [ ] Merge transfere grupos_whatsapp
- [ ] Merge transfere conhecimento_hospitais
- [ ] Merge transfere diretrizes_contextuais
- [ ] Merge transfere hospitais_bloqueados
- [ ] Merge migra aliases (sem duplicar)
- [ ] Merge registra na tabela hospital_merges
- [ ] Merge deleta hospital duplicado
- [ ] Merge com principal inexistente -> erro
- [ ] Merge com duplicado inexistente -> erro
- [ ] Merge consigo mesmo -> erro
- [ ] Retorno JSONB com contagens corretas

### Definition of Done

- [ ] Tabela `hospital_merges` criada
- [ ] Funcao `mesclar_hospitais()` criada
- [ ] Todas as 9 tabelas FK tratadas
- [ ] Aliases migrados com ON CONFLICT
- [ ] Auditoria com contagens
- [ ] SECURITY DEFINER + search_path fixo
- [ ] Testes passando

---

## Tarefa 3.2: Criar funcao SQL `deletar_hospital_sem_referencias()`

### Objetivo

Funcao segura que so deleta hospital se nao tem NENHUMA referencia em tabelas FK (exceto aliases, que tem CASCADE).

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | Via `apply_migration` (pode ser mesma migration da 3.1) |

### Implementacao

```sql
CREATE OR REPLACE FUNCTION deletar_hospital_sem_referencias(p_hospital_id UUID)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_refs INT := 0;
BEGIN
    -- Verificar cada tabela FK (exceto aliases que tem CASCADE)
    SELECT COUNT(*) INTO v_refs FROM vagas WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM vagas_grupo WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM business_events WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM business_alerts WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM grupos_whatsapp WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM conhecimento_hospitais WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM diretrizes_contextuais WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    SELECT COUNT(*) INTO v_refs FROM hospitais_bloqueados WHERE hospital_id = p_hospital_id;
    IF v_refs > 0 THEN RETURN false; END IF;

    -- Seguro para deletar (aliases deletam em CASCADE)
    DELETE FROM hospitais WHERE id = p_hospital_id;
    RETURN true;
END;
$$;
```

### Testes Obrigatorios

- [ ] Deleta hospital com zero FKs -> retorna `true`
- [ ] Nao deleta hospital com vaga -> retorna `false`
- [ ] Nao deleta hospital com grupo -> retorna `false`
- [ ] Aliases deletados em cascade

### Definition of Done

- [ ] Funcao criada
- [ ] Verifica TODAS as 8 tabelas FK
- [ ] Retorna `false` se qualquer referencia existe
- [ ] Testes passando

---

## Tarefa 3.3: Criar wrappers Python

### Objetivo

Funcoes Python que encapsulam os RPCs do banco para uso no dashboard e workers.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `app/services/grupos/hospital_cleanup.py` |

### Implementacao

```python
from app.services.supabase import supabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)

async def mesclar_hospitais(principal_id: str, duplicado_id: str, executado_por: str = "system") -> Optional[dict]:
    """Merge de hospital duplicado no principal via RPC atomica."""
    result = supabase.rpc("mesclar_hospitais", {
        "p_principal_id": principal_id,
        "p_duplicado_id": duplicado_id,
        "p_executado_por": executado_por,
    }).execute()

    if result.data:
        logger.info("Hospital merge concluido", extra=result.data)
        return result.data
    return None

async def deletar_hospital_seguro(hospital_id: str) -> bool:
    """Deleta hospital somente se nao tem referencias."""
    result = supabase.rpc("deletar_hospital_sem_referencias", {
        "p_hospital_id": hospital_id,
    }).execute()

    return result.data is True

async def listar_candidatos_limpeza_tier1() -> list:
    """Lista hospitais sem FKs + auto-criados para auto-delete."""
    ...

async def listar_candidatos_merge_tier2(threshold: float = 0.85) -> list:
    """Lista pares de hospitais com similaridade >= threshold."""
    ...
```

### Definition of Done

- [ ] Wrappers para `mesclar_hospitais` e `deletar_hospital_sem_referencias`
- [ ] Funcoes de listagem de candidatos por tier
- [ ] Logging estruturado
- [ ] Testes unitarios

---

## Tarefa 3.4: Executar limpeza Tier 1 (Auto-delete)

### Objetivo

Deletar hospitais com zero FKs + `criado_automaticamente = true` + nome no blocklist do validador (Epico 1).

### Criterio

| Condicao | Obrigatoria |
|----------|-------------|
| Zero FKs em todas as 8 tabelas | Sim |
| `criado_automaticamente = true` | Sim |
| Nome no blocklist OR falha validador | Sim |

### Procedimento

1. **Dry-run:** Query para contar registros que seriam afetados
2. **Revisar:** Confirmar que nenhum hospital valido seria deletado
3. **Executar:** Chamar `deletar_hospital_sem_referencias()` para cada candidato
4. **Verificar:** Contar registros antes e depois

### Definition of Done

- [ ] Dry-run executado e revisado
- [ ] Registros deletados: ~500-800 (estimativa)
- [ ] Zero registros com FKs afetados
- [ ] Contagem pre/pos documentada

---

## Tarefa 3.5: Executar limpeza Tier 2 (Auto-merge)

### Objetivo

Merge de hospitais com `similarity(nome_a, nome_b) >= 0.85` na mesma cidade.

### Criterio

| Condicao | Obrigatoria |
|----------|-------------|
| `similarity() >= 0.85` | Sim |
| Mesma cidade | Sim |
| Canonico = mais vagas, ou mais antigo | Sim |

### Procedimento

1. **Habilitar extensao:** `CREATE EXTENSION IF NOT EXISTS pg_trgm`
2. **Query candidatos:** Pares com alta similaridade
3. **Dry-run:** Listar pares com contagens de FKs
4. **Revisar:** Confirmar que pares sao realmente duplicatas
5. **Executar:** Chamar `mesclar_hospitais()` para cada par
6. **Verificar:** Tabela `hospital_merges` com registros

### Query de Candidatos

```sql
SELECT
    h1.id AS id_a, h1.nome AS nome_a,
    h2.id AS id_b, h2.nome AS nome_b,
    similarity(h1.nome, h2.nome) AS sim,
    (SELECT COUNT(*) FROM vagas WHERE hospital_id = h1.id) AS vagas_a,
    (SELECT COUNT(*) FROM vagas WHERE hospital_id = h2.id) AS vagas_b
FROM hospitais h1
JOIN hospitais h2 ON h1.id < h2.id  -- Evitar duplicatas e self-join
WHERE similarity(h1.nome, h2.nome) >= 0.85
  AND (h1.cidade = h2.cidade OR h1.cidade = 'Nao informada' OR h2.cidade = 'Nao informada')
ORDER BY sim DESC;
```

### Definition of Done

- [ ] Extensao pg_trgm habilitada
- [ ] Lista de candidatos revisada
- [ ] Merges executados com sucesso
- [ ] Tabela `hospital_merges` populada
- [ ] Zero vagas orfas (hospital_id apontando para deletado)

---

## Tarefa 3.6: Criar testes

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `tests/grupos/test_hospital_merge.py` |

### Testes

- [ ] Merge transfere todos os 9 tipos de FK
- [ ] Merge registra auditoria
- [ ] Merge deleta duplicado
- [ ] Merge com hospital inexistente -> erro
- [ ] Delete seguro rejeita hospital com FKs
- [ ] Delete seguro aceita hospital sem FKs

### Definition of Done

- [ ] `uv run pytest tests/grupos/test_hospital_merge.py` passando

---

## Dependencias

Epicos 1 e 2 devem estar em producao antes (para parar novos lixos enquanto limpa).

## Risco: ALTO

Modifica dados de producao. Mitigacoes:
- Transacao atomica (all-or-nothing)
- Tabela de auditoria para rastrear e reverter merges
- Tier 1 so deleta registros com ZERO referencias
- Tier 2 precisa dry-run + aprovacao antes de executar
- Executar em horario de baixo trafego
