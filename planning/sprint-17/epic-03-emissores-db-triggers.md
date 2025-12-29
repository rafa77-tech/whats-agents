# Epic 03: Emissores DB (Triggers)

## Objetivo

Criar triggers no PostgreSQL para emitir eventos de negócio automaticamente quando o status de vagas muda.

## Contexto

### Por que triggers?

| Fonte | Vantagem | Desvantagem |
|-------|----------|-------------|
| Backend | Fácil debug | Pode esquecer de chamar |
| Trigger | Impossível esquecer | Debug mais difícil |

**Escolha:** Triggers para eventos críticos (aceite, conclusão) porque:
- Garantia de 100% captura
- Independente de qual código alterou a vaga
- Transacional (rollback inclui evento)

### Eventos via Trigger

| Evento | Transição de Status |
|--------|---------------------|
| `offer_accepted` | qualquer → `reservada` |
| `shift_completed` | `reservada` → `realizada` |

---

## Story 3.1: Trigger offer_accepted

### Objetivo
Emitir `offer_accepted` quando vaga transiciona para `reservada`.

### Tarefas

1. **Criar função trigger** `emit_offer_accepted`:

```sql
-- Migration: create_trigger_offer_accepted
-- Sprint 17 - E03

CREATE OR REPLACE FUNCTION emit_offer_accepted()
RETURNS TRIGGER AS $$
BEGIN
    -- Só emite se transicionou PARA reservada (não se já era)
    IF NEW.status = 'reservada' AND (OLD.status IS NULL OR OLD.status != 'reservada') THEN
        INSERT INTO business_events (
            cliente_id,
            vaga_id,
            hospital_id,
            event_type,
            event_props,
            source
        ) VALUES (
            NEW.cliente_id,
            NEW.id,
            NEW.hospital_id,
            'offer_accepted',
            jsonb_build_object(
                'status_anterior', COALESCE(OLD.status, 'novo'),
                'data_plantao', NEW.data,
                'valor', NEW.valor_total
            ),
            'trigger'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger
CREATE TRIGGER trg_offer_accepted
AFTER INSERT OR UPDATE OF status ON vagas
FOR EACH ROW
EXECUTE FUNCTION emit_offer_accepted();

-- Comentário
COMMENT ON FUNCTION emit_offer_accepted() IS 'Sprint 17: Emite business_event offer_accepted quando vaga vai para reservada';
```

### DoD

- [ ] Função `emit_offer_accepted()` criada
- [ ] Trigger `trg_offer_accepted` ativo
- [ ] Evento emitido ao inserir vaga com status=reservada
- [ ] Evento emitido ao atualizar vaga para status=reservada
- [ ] Evento NÃO emitido se já era reservada
- [ ] `event_props` contém status_anterior, data, valor

### Testes Manuais

```sql
-- 1. Criar vaga direto como reservada
INSERT INTO vagas (hospital_id, data, status, cliente_id)
VALUES ('hospital-uuid', '2025-01-15', 'reservada', 'cliente-uuid');

-- Verificar evento
SELECT * FROM business_events WHERE event_type = 'offer_accepted' ORDER BY ts DESC LIMIT 1;

-- 2. Atualizar vaga aberta para reservada
UPDATE vagas SET status = 'reservada' WHERE id = 'vaga-uuid';

-- Verificar evento
SELECT * FROM business_events WHERE event_type = 'offer_accepted' ORDER BY ts DESC LIMIT 1;

-- 3. Atualizar vaga já reservada (não deve gerar evento)
UPDATE vagas SET valor_total = 2000 WHERE id = 'vaga-uuid' AND status = 'reservada';

-- Verificar que NÃO gerou novo evento
SELECT COUNT(*) FROM business_events WHERE vaga_id = 'vaga-uuid' AND event_type = 'offer_accepted';
-- Deve retornar 1 (só o anterior)
```

---

## Story 3.2: Trigger shift_completed

### Objetivo
Emitir `shift_completed` quando vaga transiciona para `realizada`.

### Tarefas

1. **Criar função trigger** `emit_shift_completed`:

```sql
-- Migration: create_trigger_shift_completed
-- Sprint 17 - E03

CREATE OR REPLACE FUNCTION emit_shift_completed()
RETURNS TRIGGER AS $$
BEGIN
    -- Só emite se transicionou de reservada PARA realizada
    IF NEW.status = 'realizada' AND OLD.status = 'reservada' THEN
        INSERT INTO business_events (
            cliente_id,
            vaga_id,
            hospital_id,
            event_type,
            event_props,
            source
        ) VALUES (
            NEW.cliente_id,
            NEW.id,
            NEW.hospital_id,
            'shift_completed',
            jsonb_build_object(
                'data_plantao', NEW.data,
                'realizada_em', NEW.realizada_em,
                'realizada_por', NEW.realizada_por,
                'valor', NEW.valor_total
            ),
            'trigger'
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Criar trigger
CREATE TRIGGER trg_shift_completed
AFTER UPDATE OF status ON vagas
FOR EACH ROW
EXECUTE FUNCTION emit_shift_completed();

-- Comentário
COMMENT ON FUNCTION emit_shift_completed() IS 'Sprint 17: Emite business_event shift_completed quando vaga vai de reservada para realizada';
```

### DoD

- [ ] Função `emit_shift_completed()` criada
- [ ] Trigger `trg_shift_completed` ativo
- [ ] Evento emitido APENAS em reservada → realizada
- [ ] Evento NÃO emitido de aberta → realizada (transição inválida)
- [ ] `event_props` contém data, realizada_em, realizada_por, valor

### Testes Manuais

```sql
-- 1. Marcar vaga reservada como realizada
UPDATE vagas
SET status = 'realizada',
    realizada_em = NOW(),
    realizada_por = 'ops'
WHERE id = 'vaga-uuid' AND status = 'reservada';

-- Verificar evento
SELECT * FROM business_events WHERE event_type = 'shift_completed' ORDER BY ts DESC LIMIT 1;

-- 2. Tentar marcar vaga aberta como realizada (deve falhar no app, mas testar trigger)
-- O trigger NÃO deve emitir evento porque OLD.status != 'reservada'
```

---

## Story 3.3: Validação de Integridade

### Objetivo
Garantir que os triggers estão funcionando corretamente em produção.

### Tarefas

1. **Criar query de validação**:

```sql
-- Verificar consistência: toda vaga reservada tem offer_accepted?
SELECT v.id, v.status, v.updated_at, be.event_id
FROM vagas v
LEFT JOIN business_events be ON be.vaga_id = v.id AND be.event_type = 'offer_accepted'
WHERE v.status IN ('reservada', 'realizada')
  AND be.event_id IS NULL;
-- Deve retornar 0 rows (exceto vagas antigas pré-sprint)

-- Verificar consistência: toda vaga realizada tem shift_completed?
SELECT v.id, v.status, v.realizada_em, be.event_id
FROM vagas v
LEFT JOIN business_events be ON be.vaga_id = v.id AND be.event_type = 'shift_completed'
WHERE v.status = 'realizada'
  AND be.event_id IS NULL;
-- Deve retornar 0 rows (exceto vagas antigas pré-sprint)
```

2. **Criar função de backfill** (para vagas existentes):

```sql
-- OPCIONAL: Backfill para vagas reservadas sem evento
-- Executar apenas uma vez após deploy

INSERT INTO business_events (cliente_id, vaga_id, hospital_id, event_type, event_props, source)
SELECT
    v.cliente_id,
    v.id,
    v.hospital_id,
    'offer_accepted',
    jsonb_build_object(
        'status_anterior', 'unknown',
        'data_plantao', v.data,
        'valor', v.valor_total,
        'backfill', true
    ),
    'backfill'
FROM vagas v
LEFT JOIN business_events be ON be.vaga_id = v.id AND be.event_type = 'offer_accepted'
WHERE v.status IN ('reservada', 'realizada')
  AND v.deleted_at IS NULL
  AND be.event_id IS NULL;
```

### DoD

- [ ] Query de validação criada
- [ ] Script de backfill preparado (não executar automaticamente)
- [ ] Documentação de quando usar backfill

---

## Checklist do Épico

- [ ] **S17.E03.1** - Trigger offer_accepted
- [ ] **S17.E03.2** - Trigger shift_completed
- [ ] **S17.E03.3** - Validação de integridade
- [ ] Triggers testados manualmente
- [ ] Eventos aparecem corretamente em business_events
- [ ] Sem eventos duplicados
- [ ] Performance do trigger < 10ms
