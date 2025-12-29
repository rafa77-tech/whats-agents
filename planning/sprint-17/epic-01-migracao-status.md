# Epic 01: Migração de Status da Vaga

## Objetivo

Adicionar status `realizada` na tabela `vagas` e congelar a semântica de `fechada` (sem migrar ainda).

## Contexto

Atualmente, `fechada` significa "médico aceitou e está confirmado". Isso é ambíguo porque não distingue:
- Vaga aceita (reservada)
- Plantão executado (realizada)

Sem essa distinção, não conseguimos fechar o funil de negócio.

### Abordagem Conservadora (Recomendação do Professor)

**RISCO:** Migrar `fechada` de uma vez pode quebrar relatórios, automações e código legado.

**Caminho seguro:**
1. Adicionar `realizada` (agora)
2. Parar de USAR `fechada` para conclusão (agora)
3. Manter `fechada` por compatibilidade, mas não gerar mais automaticamente
4. Migração posterior (quando tiver tráfego e métricas estáveis):
   - Com evidência (escala confirmada/financeiro) → converter `fechada` → `realizada`
   - Sem evidência → manter como `fechada` (fora do funil)

### Status Atual vs Novo

| Status | Significado | No Funil? |
|--------|-------------|-----------|
| `aberta` | Disponível | Sim |
| `anunciada` | Em oferta | Sim |
| `reservada` | Médico aceitou | Sim (offer_accepted) |
| `fechada` | Legado ambíguo | **NÃO** (excluir do funil) |
| `cancelada` | Cancelada | Não |
| `realizada` | **NOVO**: Plantão executado | Sim (shift_completed) |

---

## Story 1.1: Adicionar Status `realizada`

### Objetivo
Permitir que vagas tenham status `realizada` para indicar plantão executado.

### Tarefas

1. **Criar migration** `add_status_realizada_vagas`:

```sql
-- Migration: add_status_realizada_vagas
-- Sprint 17 - E01

-- 1. Criar índice para o novo status (otimiza queries de funil)
CREATE INDEX IF NOT EXISTS idx_vagas_status_realizada
ON vagas(status)
WHERE status = 'realizada';

-- 2. Adicionar coluna para timestamp de realização
ALTER TABLE vagas
ADD COLUMN IF NOT EXISTS realizada_em TIMESTAMPTZ;

-- 3. Adicionar coluna para quem marcou como realizada
ALTER TABLE vagas
ADD COLUMN IF NOT EXISTS realizada_por TEXT;

-- 4. Comentário para documentação
COMMENT ON COLUMN vagas.status IS 'Status da vaga: aberta, anunciada, reservada, realizada, cancelada. LEGADO: fechada (não usar para novas vagas, excluir do funil)';
COMMENT ON COLUMN vagas.realizada_em IS 'Timestamp de quando o plantão foi marcado como realizado';
COMMENT ON COLUMN vagas.realizada_por IS 'Quem marcou como realizado (user_id ou "ops")';
```

### DoD

- [ ] Migration aplicada com sucesso
- [ ] Coluna `realizada_em` criada
- [ ] Coluna `realizada_por` criada
- [ ] Índice para status=realizada criado
- [ ] Comentários de documentação adicionados

---

## Story 1.2: Congelar Semântica de `fechada`

### Objetivo
Parar de usar `fechada` em código novo, sem migrar dados existentes.

### Tarefas

1. **Auditar código que GERA status 'fechada'**:

```bash
# Buscar onde código DEFINE status como 'fechada'
grep -r "status.*=.*fechada\|status.*fechada\|'fechada'" app/ --include="*.py" | grep -v "__pycache__"
```

2. **Atualizar código para usar 'reservada' em vez de 'fechada'**:
- Se código definia `status = 'fechada'` ao aceitar, mudar para `status = 'reservada'`
- Adicionar comentário explicando a mudança

3. **Excluir 'fechada' das queries de funil**:

```sql
-- Queries de funil devem filtrar:
WHERE status IN ('aberta', 'anunciada', 'reservada', 'realizada', 'cancelada')
-- OU explicitamente:
WHERE status != 'fechada'
```

4. **NÃO FAZER agora**:
- ❌ Não migrar registros existentes
- ❌ Não renomear 'fechada' para outra coisa
- ❌ Não deletar constraint (se existir)

### DoD

- [ ] Nenhum código novo gera status 'fechada'
- [ ] Queries de funil excluem 'fechada'
- [ ] Registros existentes com 'fechada' permanecem intactos
- [ ] Documentação atualizada sobre status legado

### Validação

```sql
-- Verificar quantos registros têm 'fechada' (para referência futura)
SELECT COUNT(*) as total_fechada FROM vagas WHERE status = 'fechada';

-- Este número deve se manter estável (não aumentar)
-- Salvar em docs para migração futura
```

---

## Story 1.3: Criar Função para Marcar como Realizada

### Objetivo
Criar função no código para marcar vaga como realizada de forma padronizada.

### Tarefas

1. **Criar função SQL** (opcional, para uso direto):

```sql
-- Função para marcar vaga como realizada
CREATE OR REPLACE FUNCTION marcar_vaga_realizada(
    p_vaga_id UUID,
    p_realizada_por TEXT DEFAULT 'ops'
)
RETURNS BOOLEAN
LANGUAGE plpgsql AS $$
DECLARE
    v_status TEXT;
BEGIN
    -- Verificar status atual
    SELECT status INTO v_status FROM vagas WHERE id = p_vaga_id;

    IF v_status IS NULL THEN
        RAISE EXCEPTION 'Vaga não encontrada: %', p_vaga_id;
    END IF;

    -- Aceita tanto 'reservada' quanto 'fechada' (legado)
    IF v_status NOT IN ('reservada', 'fechada') THEN
        RAISE EXCEPTION 'Vaga deve estar reservada para ser realizada. Status atual: %', v_status;
    END IF;

    -- Atualizar status
    UPDATE vagas
    SET status = 'realizada',
        realizada_em = NOW(),
        realizada_por = p_realizada_por,
        updated_at = NOW()
    WHERE id = p_vaga_id;

    RETURN TRUE;
END;
$$;

COMMENT ON FUNCTION marcar_vaga_realizada IS 'Sprint 17: Marca vaga como realizada (aceita reservada ou fechada como origem)';
```

2. **Criar função Python** em `app/services/vagas/service.py`:

```python
async def marcar_vaga_realizada(
    vaga_id: str,
    realizada_por: str = "ops",
) -> bool:
    """
    Marca uma vaga como realizada (plantão executado).

    Aceita vagas com status 'reservada' ou 'fechada' (legado).

    Args:
        vaga_id: UUID da vaga
        realizada_por: Quem está marcando (user_id ou "ops")

    Returns:
        True se sucesso

    Raises:
        ValueError: Se vaga não existe ou status inválido
    """
    # Buscar vaga atual
    response = supabase.table("vagas").select("status").eq("id", vaga_id).single().execute()

    if not response.data:
        raise ValueError(f"Vaga não encontrada: {vaga_id}")

    status_atual = response.data["status"]

    # Aceita 'reservada' (novo) ou 'fechada' (legado)
    if status_atual not in ("reservada", "fechada"):
        raise ValueError(f"Vaga deve estar reservada ou fechada. Status atual: {status_atual}")

    # Atualizar
    supabase.table("vagas").update({
        "status": "realizada",
        "realizada_em": datetime.utcnow().isoformat(),
        "realizada_por": realizada_por,
    }).eq("id", vaga_id).execute()

    logger.info(f"Vaga {vaga_id} marcada como realizada por {realizada_por} (era: {status_atual})")
    return True
```

### DoD

- [ ] Função SQL criada
- [ ] Função Python `marcar_vaga_realizada` implementada
- [ ] Aceita tanto 'reservada' quanto 'fechada' (compatibilidade)
- [ ] Campos `realizada_em` e `realizada_por` preenchidos
- [ ] Log de auditoria gerado

### Testes

```python
# tests/vagas/test_status_realizada.py

@pytest.mark.asyncio
async def test_marcar_vaga_realizada_de_reservada():
    """Marca vaga reservada como realizada."""
    vaga = await criar_vaga_teste(status="reservada")

    result = await marcar_vaga_realizada(vaga["id"], "test_user")

    assert result is True
    vaga_atualizada = await buscar_vaga(vaga["id"])
    assert vaga_atualizada["status"] == "realizada"


@pytest.mark.asyncio
async def test_marcar_vaga_realizada_de_fechada_legado():
    """Marca vaga fechada (legado) como realizada."""
    vaga = await criar_vaga_teste(status="fechada")

    result = await marcar_vaga_realizada(vaga["id"], "test_user")

    assert result is True
    vaga_atualizada = await buscar_vaga(vaga["id"])
    assert vaga_atualizada["status"] == "realizada"


@pytest.mark.asyncio
async def test_marcar_vaga_realizada_status_invalido():
    """Falha ao marcar vaga que não está reservada/fechada."""
    vaga = await criar_vaga_teste(status="aberta")

    with pytest.raises(ValueError) as exc:
        await marcar_vaga_realizada(vaga["id"])

    assert "deve estar reservada" in str(exc.value)
```

---

## Story 1.4: Plano de Migração Futura (Documentação)

### Objetivo
Documentar o plano para migração futura de registros `fechada`.

### Documento: `docs/MIGRACAO_STATUS_FECHADA.md`

```markdown
# Migração de Status 'fechada' para 'realizada'

## Contexto

O status 'fechada' era usado ambiguamente para "médico aceitou".
Na Sprint 17 introduzimos 'realizada' para "plantão executado".

## Estado Atual

- 'fechada' não é mais gerado automaticamente
- Registros antigos permanecem como 'fechada'
- 'fechada' está excluído do funil de métricas

## Critérios para Migração

Só migrar quando:
1. Sistema de business_events estiver 100% rollout
2. Funil estiver estabilizado por 2+ semanas
3. Tiver forma de validar (ex: dados financeiros, escala confirmada)

## Estratégia de Migração

### Com Evidência
```sql
-- Vagas 'fechada' com pagamento confirmado → 'realizada'
UPDATE vagas v
SET status = 'realizada',
    realizada_em = COALESCE(v.updated_at, v.data),
    realizada_por = 'migration_batch'
FROM pagamentos p
WHERE p.vaga_id = v.id
  AND p.status = 'pago'
  AND v.status = 'fechada';
```

### Sem Evidência
```sql
-- Opção A: Manter como 'fechada' (fora do funil)
-- Nada a fazer

-- Opção B: Marcar como 'fechada_legacy' (se quiser distinguir)
-- UPDATE vagas SET status = 'fechada_legacy' WHERE status = 'fechada';
```

## Métricas de Acompanhamento

Antes de migrar, verificar:
- Total de vagas 'fechada': ___
- Com pagamento associado: ___
- Sem pagamento: ___
```

### DoD

- [ ] Documento `MIGRACAO_STATUS_FECHADA.md` criado
- [ ] Critérios de migração definidos
- [ ] Queries de migração documentadas
- [ ] Data estimada: após 2 semanas de funil estável

---

## Checklist do Épico

- [ ] **S17.E01.1** - Status 'realizada' habilitado
- [ ] **S17.E01.2** - Semântica de 'fechada' congelada
- [ ] **S17.E01.3** - Função marcar_vaga_realizada
- [ ] **S17.E01.4** - Plano de migração documentado
- [ ] Todos os testes passando
- [ ] Nenhum código novo gera 'fechada'
- [ ] Funil exclui 'fechada' das métricas
