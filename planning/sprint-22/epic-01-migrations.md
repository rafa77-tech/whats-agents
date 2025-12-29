# E01: Migrations

**Epico:** Estrutura de Dados para Responsividade
**Estimativa:** 2h
**Dependencias:** Nenhuma

---

## Objetivo

Criar estrutura de dados para suportar modos operacionais, delay por contexto e mensagens fora do horario.

---

## Escopo

### Incluido

- [x] Tabela `julia_estado` (singleton de estado)
- [x] Tabela `mensagens_fora_horario`
- [x] Alteracao em `fila_mensagens` (tipo_contexto, prioridade)
- [x] Indices para performance

### Excluido

- [ ] Logica de negocio (outros epicos)
- [ ] Jobs de processamento

---

## Tarefas

### T01: Migration julia_estado

**Arquivo:** `migrations/YYYYMMDDHHMMSS_create_julia_estado.sql`

```sql
-- Migration: create_julia_estado
-- Descricao: Tabela singleton para estado em tempo real da Julia

CREATE TABLE julia_estado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Estado atual
    modo TEXT NOT NULL DEFAULT 'atendimento'
        CHECK (modo IN ('atendimento', 'comercial', 'batch', 'pausada')),

    -- Metricas em tempo real
    conversas_ativas INT DEFAULT 0,
    replies_pendentes INT DEFAULT 0,
    handoffs_abertos INT DEFAULT 0,

    -- Ultima atividade
    ultima_acao TEXT,
    ultima_acao_at TIMESTAMPTZ,

    -- Proxima acao agendada
    proxima_acao TEXT,
    proxima_acao_at TIMESTAMPTZ,

    -- Controle
    atualizado_em TIMESTAMPTZ DEFAULT now(),

    -- Singleton (apenas 1 registro)
    CONSTRAINT julia_estado_singleton CHECK (id = '00000000-0000-0000-0000-000000000001'::uuid)
);

-- Comentarios
COMMENT ON TABLE julia_estado IS 'Estado em tempo real da Julia (singleton)';
COMMENT ON COLUMN julia_estado.modo IS 'Modo operacional atual: atendimento, comercial, batch, pausada';
COMMENT ON COLUMN julia_estado.conversas_ativas IS 'Numero de conversas ativas na ultima hora';
COMMENT ON COLUMN julia_estado.replies_pendentes IS 'Mensagens aguardando resposta';
COMMENT ON COLUMN julia_estado.handoffs_abertos IS 'Handoffs pendentes de confirmacao';

-- Inserir registro inicial
INSERT INTO julia_estado (id, modo)
VALUES ('00000000-0000-0000-0000-000000000001', 'atendimento')
ON CONFLICT DO NOTHING;

-- Trigger para atualizar atualizado_em
CREATE OR REPLACE FUNCTION update_julia_estado_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_julia_estado_updated
    BEFORE UPDATE ON julia_estado
    FOR EACH ROW
    EXECUTE FUNCTION update_julia_estado_timestamp();
```

**DoD:**
- [ ] Migration aplicada sem erro
- [ ] Registro singleton existe
- [ ] Trigger de timestamp funciona
- [ ] Query `SELECT * FROM julia_estado` retorna 1 registro

---

### T02: Migration mensagens_fora_horario

**Arquivo:** `migrations/YYYYMMDDHHMMSS_create_mensagens_fora_horario.sql`

```sql
-- Migration: create_mensagens_fora_horario
-- Descricao: Armazena mensagens recebidas fora do horario para processamento posterior

CREATE TABLE mensagens_fora_horario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencia
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    conversa_id UUID REFERENCES conversations(id),

    -- Mensagem original
    mensagem TEXT NOT NULL,
    recebida_em TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Ack
    ack_enviado BOOLEAN DEFAULT FALSE,
    ack_enviado_em TIMESTAMPTZ,
    ack_mensagem_id TEXT,  -- ID da mensagem no WhatsApp

    -- Processamento
    processada BOOLEAN DEFAULT FALSE,
    processada_em TIMESTAMPTZ,
    processada_resultado TEXT,  -- 'sucesso', 'erro', 'ignorada'

    -- Contexto para retomada
    contexto JSONB DEFAULT '{}',
    -- Exemplo: {"intent": "buscar_vaga", "especialidade": "cardiologia"}

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Comentarios
COMMENT ON TABLE mensagens_fora_horario IS 'Mensagens recebidas fora do horario comercial';
COMMENT ON COLUMN mensagens_fora_horario.ack_enviado IS 'Se o ack imediato foi enviado';
COMMENT ON COLUMN mensagens_fora_horario.processada IS 'Se a mensagem foi processada no horario comercial';
COMMENT ON COLUMN mensagens_fora_horario.contexto IS 'Contexto extraido para retomada da conversa';

-- Indices
CREATE INDEX idx_mfh_pendentes ON mensagens_fora_horario(processada, recebida_em)
    WHERE processada = FALSE;

CREATE INDEX idx_mfh_cliente ON mensagens_fora_horario(cliente_id, recebida_em DESC);

CREATE INDEX idx_mfh_sem_ack ON mensagens_fora_horario(ack_enviado, recebida_em)
    WHERE ack_enviado = FALSE;

-- Trigger para updated_at
CREATE TRIGGER trigger_mfh_updated
    BEFORE UPDATE ON mensagens_fora_horario
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

**DoD:**
- [ ] Migration aplicada sem erro
- [ ] Indices criados
- [ ] INSERT funciona com cliente_id valido
- [ ] Query de pendentes funciona

---

### T03: Migration alterar_fila_mensagens

**Arquivo:** `migrations/YYYYMMDDHHMMSS_alter_fila_mensagens_contexto.sql`

```sql
-- Migration: alter_fila_mensagens_contexto
-- Descricao: Adiciona tipo_contexto e prioridade para delay inteligente

-- Adicionar tipo de contexto
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS tipo_contexto TEXT
    DEFAULT 'campanha_fria';

-- Constraint de valores validos
ALTER TABLE fila_mensagens DROP CONSTRAINT IF EXISTS fila_mensagens_tipo_contexto_check;
ALTER TABLE fila_mensagens ADD CONSTRAINT fila_mensagens_tipo_contexto_check
    CHECK (tipo_contexto IN (
        'reply_direta',
        'aceite_vaga',
        'confirmacao',
        'oferta_ativa',
        'followup',
        'campanha_fria'
    ));

-- Adicionar prioridade explicita (1 = maxima, 5 = minima)
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS prioridade INT DEFAULT 5;

ALTER TABLE fila_mensagens DROP CONSTRAINT IF EXISTS fila_mensagens_prioridade_check;
ALTER TABLE fila_mensagens ADD CONSTRAINT fila_mensagens_prioridade_check
    CHECK (prioridade BETWEEN 1 AND 5);

-- Adicionar delay calculado (em ms)
ALTER TABLE fila_mensagens ADD COLUMN IF NOT EXISTS delay_calculado_ms INT;

-- Comentarios
COMMENT ON COLUMN fila_mensagens.tipo_contexto IS 'Tipo de contexto para calculo de delay';
COMMENT ON COLUMN fila_mensagens.prioridade IS 'Prioridade: 1=maxima (reply), 5=minima (campanha)';
COMMENT ON COLUMN fila_mensagens.delay_calculado_ms IS 'Delay em ms calculado pelo Delay Engine';

-- Indice para processamento por prioridade
CREATE INDEX IF NOT EXISTS idx_fila_prioridade
    ON fila_mensagens(prioridade, criado_em)
    WHERE status = 'pendente';
```

**DoD:**
- [ ] Migration aplicada sem erro
- [ ] Colunas tipo_contexto, prioridade, delay_calculado_ms existem
- [ ] Constraints funcionam (rejeita valores invalidos)
- [ ] Indice de prioridade criado

---

## Validacao

### Queries de Teste

```sql
-- Verificar julia_estado
SELECT * FROM julia_estado;
-- Esperado: 1 registro com modo='atendimento'

-- Verificar estrutura mensagens_fora_horario
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'mensagens_fora_horario'
ORDER BY ordinal_position;

-- Verificar colunas novas em fila_mensagens
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'fila_mensagens'
AND column_name IN ('tipo_contexto', 'prioridade', 'delay_calculado_ms');

-- Testar constraint tipo_contexto
INSERT INTO fila_mensagens (telefone, tipo_contexto)
VALUES ('5511999999999', 'invalido');
-- Esperado: ERRO de constraint

-- Testar constraint prioridade
INSERT INTO fila_mensagens (telefone, prioridade)
VALUES ('5511999999999', 10);
-- Esperado: ERRO de constraint
```

---

## Definition of Done (DoD)

### Obrigatorio

- [ ] Todas as 3 migrations aplicadas com sucesso
- [ ] Zero erros no apply
- [ ] Tabela julia_estado com singleton
- [ ] Tabela mensagens_fora_horario com indices
- [ ] fila_mensagens com novas colunas e constraints
- [ ] Rollback testado (migrations reversible)

### Qualidade

- [ ] Comentarios em todas as tabelas/colunas
- [ ] Indices para queries frequentes
- [ ] Constraints validando dominio

### Documentacao

- [ ] Migration names seguem padrao
- [ ] Comentarios explicam proposito

---

## Rollback

```sql
-- Rollback T03
ALTER TABLE fila_mensagens DROP COLUMN IF EXISTS tipo_contexto;
ALTER TABLE fila_mensagens DROP COLUMN IF EXISTS prioridade;
ALTER TABLE fila_mensagens DROP COLUMN IF EXISTS delay_calculado_ms;

-- Rollback T02
DROP TABLE IF EXISTS mensagens_fora_horario;

-- Rollback T01
DROP TABLE IF EXISTS julia_estado;
DROP FUNCTION IF EXISTS update_julia_estado_timestamp();
```

---

*Epico criado em 29/12/2025*
