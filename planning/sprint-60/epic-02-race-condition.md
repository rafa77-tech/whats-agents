# EPICO 2: Race Condition com Lock Atomico

## Contexto

Workers paralelos do pipeline de grupos WhatsApp processam mensagens simultaneamente. Quando dois workers encontram o mesmo hospital em mensagens diferentes, ambos fazem:

1. `SELECT` em `hospitais_alias` — nao encontram
2. `INSERT` em `hospitais` — ambos criam
3. Resultado: 2 registros para o mesmo hospital

Isso acontece em milissegundos, tornando checks no Python insuficientes. A solucao requer atomicidade no banco via `pg_advisory_xact_lock`.

**Objetivo:** Garantir que o mesmo hospital nunca seja criado em duplicata por concorrencia.

## Escopo

- **Incluido:**
  - Funcao SQL atomica `buscar_ou_criar_hospital()`
  - Refatorar `criar_hospital()` e `criar_hospital_minimo()` para usar RPC
  - Testes de concorrencia

- **Excluido:**
  - Deduplicar registros existentes (Epico 3)
  - Alterar logica de alias/matching (fora do escopo)
  - UNIQUE constraint em alias_normalizado (Epico 6)

---

## Tarefa 2.1: Criar funcao SQL `buscar_ou_criar_hospital()`

### Objetivo

Funcao PostgreSQL que serializa criacao por alias normalizado usando advisory lock, eliminando race conditions.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MIGRATION | Via `mcp__supabase__apply_migration` |

### Implementacao

```sql
CREATE OR REPLACE FUNCTION buscar_ou_criar_hospital(
    p_nome TEXT,
    p_alias_normalizado TEXT,
    p_cidade TEXT DEFAULT 'Nao informada',
    p_estado TEXT DEFAULT 'SP',
    p_confianca FLOAT DEFAULT 0.3,
    p_criado_por TEXT DEFAULT 'fallback'
) RETURNS TABLE(hospital_id UUID, nome TEXT, foi_criado BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_hospital_id UUID;
    v_nome TEXT;
    v_foi_criado BOOLEAN := false;
BEGIN
    -- 1. Serializar por alias (lock no escopo da transacao)
    PERFORM pg_advisory_xact_lock(hashtext(p_alias_normalizado));

    -- 2. Buscar alias existente
    SELECT ha.hospital_id, h.nome
    INTO v_hospital_id, v_nome
    FROM hospitais_alias ha
    JOIN hospitais h ON h.id = ha.hospital_id
    WHERE ha.alias_normalizado = p_alias_normalizado
    LIMIT 1;

    -- 3. Se encontrou, retornar existente
    IF v_hospital_id IS NOT NULL THEN
        RETURN QUERY SELECT v_hospital_id, v_nome, false;
        RETURN;
    END IF;

    -- 4. Se nao encontrou, criar hospital
    INSERT INTO hospitais (nome, cidade, estado, ativo, precisa_revisao, criado_automaticamente)
    VALUES (p_nome, p_cidade, p_estado, true, true, true)
    RETURNING id INTO v_hospital_id;

    -- 5. Criar alias
    INSERT INTO hospitais_alias (hospital_id, alias_original, alias_normalizado, confianca, criado_por)
    VALUES (v_hospital_id, p_nome, p_alias_normalizado, p_confianca, p_criado_por)
    ON CONFLICT (alias_normalizado) DO NOTHING;

    v_foi_criado := true;

    RETURN QUERY SELECT v_hospital_id, p_nome, v_foi_criado;
END;
$$;
```

**Detalhes:**
- `pg_advisory_xact_lock(hashtext(alias))` — lock por alias, liberado automaticamente no commit
- `SECURITY DEFINER` + `SET search_path = public` — seguranca (Sprint 57 pattern)
- `ON CONFLICT` no alias — belt-and-suspenders caso constraint exista
- Retorna `foi_criado` para log/metricas

### Testes Obrigatorios

**Unitarios (SQL):**
- [ ] Criar hospital novo retorna `foi_criado = true`
- [ ] Buscar hospital existente retorna `foi_criado = false`
- [ ] Alias criado junto com hospital
- [ ] Hospital e alias na mesma transacao (rollback conjunto)

### Definition of Done

- [ ] Funcao criada via migration
- [ ] Retorna `(hospital_id, nome, foi_criado)`
- [ ] Advisory lock por alias_normalizado
- [ ] `SECURITY DEFINER` com search_path fixo
- [ ] Testada com dados reais (SELECT apos INSERT)

---

## Tarefa 2.2: Refatorar `criar_hospital()` e `criar_hospital_minimo()`

### Objetivo

Substituir INSERT direto pelo RPC atomico em ambas as funcoes de criacao.

### Arquivos

| Acao | Arquivo |
|------|---------|
| MODIFICAR | `app/services/grupos/hospital_web.py` (447 linhas) |

### Implementacao

```python
async def criar_hospital(info: InfoHospitalWeb, alias_original: str) -> Optional[str]:
    """Cria hospital usando RPC atomica (race-condition safe)."""
    alias_normalizado = normalizar_texto(alias_original)

    result = supabase.rpc("buscar_ou_criar_hospital", {
        "p_nome": info.nome,
        "p_alias_normalizado": alias_normalizado,
        "p_cidade": info.cidade or "Nao informada",
        "p_estado": info.estado or "SP",
        "p_confianca": 0.7,
        "p_criado_por": "web_search",
    }).execute()

    if not result.data:
        return None

    row = result.data[0]
    if row["foi_criado"]:
        logger.info("Hospital criado via RPC", extra={
            "hospital_id": row["hospital_id"],
            "nome": row["nome"],
        })
    else:
        logger.info("Hospital reutilizado via RPC", extra={
            "hospital_id": row["hospital_id"],
            "nome": row["nome"],
            "alias_buscado": alias_original,
        })

    return row["hospital_id"]


async def criar_hospital_minimo(nome: str, regiao_grupo: str = "") -> Optional[str]:
    """Cria hospital minimo usando RPC atomica (race-condition safe)."""
    alias_normalizado = normalizar_texto(nome)

    result = supabase.rpc("buscar_ou_criar_hospital", {
        "p_nome": nome,
        "p_alias_normalizado": alias_normalizado,
        "p_cidade": regiao_grupo or "Nao informada",
        "p_estado": "SP",
        "p_confianca": 0.3,
        "p_criado_por": "fallback",
    }).execute()

    if not result.data:
        return None

    row = result.data[0]
    if not row["foi_criado"]:
        logger.info("Hospital reutilizado (fallback)", extra={
            "hospital_id": row["hospital_id"],
            "nome": row["nome"],
        })

    return row["hospital_id"]
```

**Mudancas:**
- Remove INSERT direto em `hospitais` e `hospitais_alias`
- Usa `supabase.rpc("buscar_ou_criar_hospital", {...})`
- Log diferencia criacao vs reuso
- Mantém assinatura publica identica (backward compatible)

### Testes Obrigatorios

**Unitarios:**
- [ ] `criar_hospital()` chama RPC com parametros corretos
- [ ] `criar_hospital_minimo()` chama RPC com parametros corretos
- [ ] Quando `foi_criado=false`, log de reuso emitido
- [ ] Quando `foi_criado=true`, log de criacao emitido
- [ ] Retorno e o `hospital_id` do RPC

**Integracao:**
- [ ] Duas chamadas com mesmo alias retornam mesmo hospital_id

### Definition of Done

- [ ] Ambas funcoes refatoradas para usar RPC
- [ ] Zero INSERT direto em `hospitais` nas funcoes de criacao
- [ ] Assinatura publica preservada (backward compatible)
- [ ] Logs de reuso/criacao
- [ ] Testes passando

---

## Tarefa 2.3: Criar testes de concorrencia

### Objetivo

Verificar que a race condition foi eliminada.

### Arquivos

| Acao | Arquivo |
|------|---------|
| CRIAR | `tests/grupos/test_hospital_race_condition.py` |

### Implementacao

```python
import asyncio

async def test_criacao_concorrente_retorna_mesmo_hospital():
    """Duas chamadas simultaneas para mesmo alias retornam mesmo ID."""
    # Simular 2 workers chamando criar_hospital_minimo em paralelo
    results = await asyncio.gather(
        criar_hospital_minimo("Hospital Teste Race"),
        criar_hospital_minimo("Hospital Teste Race"),
    )
    assert results[0] == results[1]  # Mesmo hospital_id

async def test_criacao_concorrente_cria_apenas_um():
    """Apenas 1 registro criado quando 2 workers tentam simultaneamente."""
    # Verificar count antes e depois
    ...
```

**Nota:** Testes de concorrencia real dependem de acesso ao banco. Com mocks, testar que o RPC e chamado corretamente e que o `foi_criado` flag e respeitado.

### Definition of Done

- [ ] Teste de concorrencia simulada (asyncio.gather)
- [ ] Teste de RPC mock (parametros corretos)
- [ ] Teste de idempotencia (mesma chamada 2x = mesmo resultado)
- [ ] `uv run pytest tests/grupos/test_hospital_race_condition.py` passando

---

## Dependencias

**Epico 1 (Validacao)** deve estar ativo — validacao impede que advisory lock seja usado para nomes lixo.

## Risco: MEDIO

Advisory locks adicionam latencia minima (~1ms). Escopo do lock e estreito (por alias normalizado). Rollback simples: reverter para INSERT direto.
