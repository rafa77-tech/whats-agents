# Epic 01: Migrations

## Objetivo

Criar estrutura de banco para suportar o fluxo de ponte automatica entre medico e divulgador.

## Contexto

Precisamos de:
1. Tabela `external_handoffs` para rastrear cada ponte
2. Campos `source` e `source_id` em `vagas` para linkar origem
3. Tabela `handoff_used_tokens` para garantir single-use dos links
4. Novo status `aguardando_confirmacao` em vagas

---

## Story 1.1: Tabela external_handoffs

### Objetivo
Criar tabela principal para rastrear handoffs externos.

### Migration

```sql
-- Migration: create_external_handoffs
-- Sprint 20 - E01 - Ponte Automatica

CREATE TABLE IF NOT EXISTS public.external_handoffs (
    -- Identificacao
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    vaga_id UUID NOT NULL REFERENCES public.vagas(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES public.clientes(id) ON DELETE CASCADE,

    -- Divulgador (snapshot no momento da ponte)
    divulgador_nome TEXT,
    divulgador_telefone TEXT NOT NULL,
    divulgador_empresa TEXT,

    -- Estado
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'contacted', 'confirmed', 'not_confirmed', 'expired')),

    -- Controle de tempo
    reserved_until TIMESTAMPTZ NOT NULL,
    last_followup_at TIMESTAMPTZ,
    followup_count INT DEFAULT 0,

    -- Auditoria de confirmacao
    confirmed_at TIMESTAMPTZ,
    confirmed_by TEXT,  -- 'link' ou 'keyword'
    confirmation_source TEXT,  -- detalhes adicionais

    -- Auditoria de expiracao
    expired_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    -- Previne duplicatas: uma vaga so pode ter um handoff ativo por medico
    UNIQUE (vaga_id, cliente_id)
);

-- Indices para queries frequentes
CREATE INDEX IF NOT EXISTS idx_eh_status
    ON public.external_handoffs(status);

CREATE INDEX IF NOT EXISTS idx_eh_reserved_until
    ON public.external_handoffs(reserved_until)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_eh_divulgador_tel
    ON public.external_handoffs(divulgador_telefone);

CREATE INDEX IF NOT EXISTS idx_eh_vaga
    ON public.external_handoffs(vaga_id);

CREATE INDEX IF NOT EXISTS idx_eh_cliente
    ON public.external_handoffs(cliente_id);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_external_handoffs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_external_handoffs_updated_at
    BEFORE UPDATE ON public.external_handoffs
    FOR EACH ROW
    EXECUTE FUNCTION update_external_handoffs_updated_at();

-- Comentarios
COMMENT ON TABLE public.external_handoffs IS 'Ponte automatica medico-divulgador - Sprint 20';
COMMENT ON COLUMN public.external_handoffs.status IS 'pending=aguardando, contacted=msg enviada, confirmed=fechou, not_confirmed=nao fechou, expired=expirou';
COMMENT ON COLUMN public.external_handoffs.reserved_until IS 'Prazo para confirmacao (48h por padrao)';
COMMENT ON COLUMN public.external_handoffs.confirmed_by IS 'link ou keyword';
```

### DoD

- [ ] Tabela `external_handoffs` criada
- [ ] Indices criados
- [ ] Trigger de updated_at funcionando
- [ ] Constraint UNIQUE funcionando
- [ ] Comentarios adicionados

---

## Story 1.2: Campos source em vagas

### Objetivo
Adicionar rastreabilidade de origem das vagas.

### Migration

```sql
-- Migration: add_source_to_vagas
-- Sprint 20 - E01 - Rastreabilidade de origem

-- Adicionar campos de origem
ALTER TABLE public.vagas
    ADD COLUMN IF NOT EXISTS source TEXT,
    ADD COLUMN IF NOT EXISTS source_id UUID;

-- Indice para buscar por origem
CREATE INDEX IF NOT EXISTS idx_vagas_source
    ON public.vagas(source)
    WHERE source IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vagas_source_id
    ON public.vagas(source_id)
    WHERE source_id IS NOT NULL;

-- Comentarios
COMMENT ON COLUMN public.vagas.source IS 'Origem da vaga: grupo, manual, api';
COMMENT ON COLUMN public.vagas.source_id IS 'ID da origem (ex: vagas_grupo.id)';

-- Atualizar constraint de status para incluir novo status
ALTER TABLE public.vagas DROP CONSTRAINT IF EXISTS vagas_status_check;
ALTER TABLE public.vagas ADD CONSTRAINT vagas_status_check
    CHECK (status IN (
        'aberta',
        'anunciada',
        'reservada',
        'aguardando_confirmacao',  -- NOVO
        'fechada',
        'realizada',
        'cancelada'
    ));
```

### DoD

- [ ] Campos `source` e `source_id` adicionados
- [ ] Indices criados
- [ ] Novo status `aguardando_confirmacao` disponivel
- [ ] Comentarios adicionados

---

## Story 1.3: Tabela handoff_used_tokens

### Objetivo
Garantir que cada token de confirmacao seja usado apenas uma vez.

### Migration

```sql
-- Migration: create_handoff_used_tokens
-- Sprint 20 - E01 - Single-use tokens

CREATE TABLE IF NOT EXISTS public.handoff_used_tokens (
    -- JTI do token (claim padrao JWT para ID unico)
    jti TEXT PRIMARY KEY,

    -- Referencia ao handoff
    handoff_id UUID NOT NULL REFERENCES public.external_handoffs(id) ON DELETE CASCADE,

    -- Acao que foi executada
    action TEXT NOT NULL CHECK (action IN ('confirmed', 'not_confirmed')),

    -- Quando foi usado
    used_at TIMESTAMPTZ DEFAULT now(),

    -- IP de origem (para auditoria)
    ip_address TEXT
);

-- Indice para buscar por handoff
CREATE INDEX IF NOT EXISTS idx_hut_handoff
    ON public.handoff_used_tokens(handoff_id);

-- Comentarios
COMMENT ON TABLE public.handoff_used_tokens IS 'Tokens JWT usados para confirmacao - previne reuso';
COMMENT ON COLUMN public.handoff_used_tokens.jti IS 'JWT ID (claim jti) - identificador unico do token';
```

### DoD

- [ ] Tabela `handoff_used_tokens` criada
- [ ] Constraint de acao funcionando
- [ ] Indice criado
- [ ] Comentarios adicionados

---

## Story 1.4: Backfill source em vagas existentes

### Objetivo
Preencher campo source para vagas que vieram de grupos.

### Migration

```sql
-- Migration: backfill_vagas_source
-- Sprint 20 - E01 - Preencher origem de vagas existentes

-- Atualizar vagas que tem origem em vagas_grupo
UPDATE public.vagas v
SET
    source = 'grupo',
    source_id = vg.id
FROM public.vagas_grupo vg
WHERE vg.vaga_importada_id = v.id
AND v.source IS NULL;

-- Log quantas foram atualizadas (via RAISE NOTICE em funcao)
DO $$
DECLARE
    updated_count INT;
BEGIN
    SELECT COUNT(*) INTO updated_count
    FROM public.vagas
    WHERE source = 'grupo';

    RAISE NOTICE 'Vagas com source=grupo: %', updated_count;
END $$;
```

### DoD

- [ ] Vagas existentes com origem de grupo marcadas
- [ ] Log de quantas foram atualizadas

---

## Checklist do Epico

- [ ] **S20.E01.1** - external_handoffs criada
- [ ] **S20.E01.2** - source/source_id em vagas
- [ ] **S20.E01.3** - handoff_used_tokens criada
- [ ] **S20.E01.4** - Backfill executado
- [ ] Todas as migrations aplicadas com sucesso
- [ ] Indices funcionando
- [ ] Constraints validando

---

## Validacao

```sql
-- Verificar estrutura
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'external_handoffs'
ORDER BY ordinal_position;

-- Verificar indices
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'external_handoffs';

-- Verificar constraint de status
SELECT constraint_name, check_clause
FROM information_schema.check_constraints
WHERE constraint_name LIKE '%vagas_status%';

-- Verificar backfill
SELECT source, COUNT(*) as total
FROM vagas
GROUP BY source;
```
