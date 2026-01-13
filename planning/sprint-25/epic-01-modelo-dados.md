# Epic 01: Modelo de Dados Unificado

**Status:** ⚠️ Migrations criadas, pendente aplicar no Supabase

**Arquivos criados:**
- `migrations/sprint-25/001_chips_schema.sql`
- `migrations/sprint-25/002_chips_triggers.sql`

**Ação necessária:** Executar migrations manualmente via Supabase SQL Editor

---

## Objetivo

Criar estrutura de banco unificada que suporta **todo o ciclo de vida do chip**:
- Provisioning (Salvy)
- Warmup (21 dias)
- Trust Score multiparametrico
- Producao (Julia)
- RAG de politicas Meta

## Contexto

**Mudanca de Paradigma:**

| Antes | Agora |
|-------|-------|
| `warmup_chips` isolado | `chips` unificado |
| `health_score` binario | `trust_score` multiparametrico |
| Sem Salvy | Com Salvy integration |
| Sem politicas Meta | RAG de politicas |
| Triggers fixos | Permissoes dinamicas |

---

## Story 1.1: Tabela chips (Central)

### Objetivo
Criar tabela unificada que gerencia todo ciclo de vida.

### Migration

```sql
-- Migration: create_chips_unified
-- Sprint 25 - E01 - Modelo Unificado

-- =====================================================
-- TABELA CENTRAL: chips
-- Unifica todo ciclo de vida do chip
-- =====================================================
CREATE TABLE chips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefone TEXT UNIQUE NOT NULL,

    -- ══════════════════════════════════════════
    -- SALVY (provisioning)
    -- ══════════════════════════════════════════
    salvy_id TEXT UNIQUE,
    salvy_status TEXT CHECK (salvy_status IN ('active', 'blocked', 'canceled')),
    salvy_created_at TIMESTAMPTZ,

    -- ══════════════════════════════════════════
    -- EVOLUTION (WhatsApp)
    -- ══════════════════════════════════════════
    instance_name TEXT UNIQUE NOT NULL,
    evolution_connected BOOLEAN DEFAULT false,
    evolution_qr_code TEXT,

    -- ══════════════════════════════════════════
    -- ESTADO NO SISTEMA
    -- ══════════════════════════════════════════
    status TEXT NOT NULL DEFAULT 'provisioned'
        CHECK (status IN (
            'provisioned',  -- Comprado na Salvy, aguardando setup
            'pending',      -- Aguardando conexao Evolution
            'warming',      -- Em aquecimento (21 dias)
            'ready',        -- Pronto, aguardando slot producao
            'active',       -- Em producao na Julia
            'degraded',     -- Trust baixo, modo restrito
            'paused',       -- Pausado manualmente
            'banned',       -- Banido pelo WhatsApp
            'cancelled'     -- Cancelado na Salvy
        )),

    -- ══════════════════════════════════════════
    -- TIPO DE CHIP (separação de pools)
    -- ══════════════════════════════════════════
    tipo TEXT NOT NULL DEFAULT 'julia'
        CHECK (tipo IN (
            'julia',     -- Conversa 1:1 com médicos
            'listener'   -- Entra em grupos, apenas recebe msgs
        )),

    -- ══════════════════════════════════════════
    -- WARMING (21 dias)
    -- ══════════════════════════════════════════
    fase_warmup TEXT DEFAULT 'setup'
        CHECK (fase_warmup IN (
            'setup',              -- Dias 1-3: apenas config
            'primeiros_contatos', -- Dias 4-7: max 10 msgs/dia
            'expansao',           -- Dias 8-14: max 30 msgs/dia
            'pre_operacao',       -- Dias 15-21: max 50 msgs/dia
            'operacao'            -- Dia 21+: pronto
        )),
    fase_iniciada_em TIMESTAMPTZ DEFAULT now(),
    warming_started_at TIMESTAMPTZ,
    warming_day INT DEFAULT 0,

    -- ══════════════════════════════════════════
    -- TRUST SCORE (multiparametrico)
    -- ══════════════════════════════════════════
    trust_score INT DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    trust_level TEXT DEFAULT 'amarelo'
        CHECK (trust_level IN ('verde', 'amarelo', 'laranja', 'vermelho', 'critico')),
    ultimo_calculo_trust TIMESTAMPTZ,

    -- Fatores do Trust Score (cache para performance)
    trust_factors JSONB DEFAULT '{}',

    -- ══════════════════════════════════════════
    -- METRICAS
    -- ══════════════════════════════════════════
    msgs_enviadas_total INT DEFAULT 0,
    msgs_recebidas_total INT DEFAULT 0,
    msgs_enviadas_hoje INT DEFAULT 0,
    msgs_recebidas_hoje INT DEFAULT 0,

    taxa_resposta DECIMAL(5,4) DEFAULT 0,      -- 0.0000 a 1.0000
    taxa_delivery DECIMAL(5,4) DEFAULT 1,
    taxa_block DECIMAL(5,4) DEFAULT 0,

    conversas_bidirecionais INT DEFAULT 0,
    grupos_count INT DEFAULT 0,
    tipos_midia_usados TEXT[] DEFAULT '{}',

    erros_ultimas_24h INT DEFAULT 0,
    dias_sem_erro INT DEFAULT 0,

    -- ══════════════════════════════════════════
    -- PERMISSOES (calculadas do Trust Score)
    -- ══════════════════════════════════════════
    pode_prospectar BOOLEAN DEFAULT false,
    pode_followup BOOLEAN DEFAULT false,
    pode_responder BOOLEAN DEFAULT true,
    limite_hora INT DEFAULT 5,
    limite_dia INT DEFAULT 30,
    delay_minimo_segundos INT DEFAULT 120,

    -- ══════════════════════════════════════════
    -- PRODUCAO
    -- ══════════════════════════════════════════
    promoted_to_active_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,

    -- ══════════════════════════════════════════
    -- AUDITORIA
    -- ══════════════════════════════════════════
    banned_at TIMESTAMPTZ,
    ban_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices para queries frequentes
CREATE INDEX idx_chips_status ON chips(status);
CREATE INDEX idx_chips_trust ON chips(trust_score DESC) WHERE status IN ('warming', 'ready', 'active');
CREATE INDEX idx_chips_ready ON chips(trust_score DESC, warming_started_at ASC) WHERE status = 'ready';
CREATE INDEX idx_chips_active ON chips(trust_score DESC) WHERE status = 'active';
CREATE INDEX idx_chips_telefone ON chips(telefone);

-- Comentarios
COMMENT ON TABLE chips IS 'Tabela unificada de chips - Sprint 25';
COMMENT ON COLUMN chips.trust_score IS 'Score 0-100: verde(80+), amarelo(60-79), laranja(40-59), vermelho(20-39), critico(<20)';
COMMENT ON COLUMN chips.trust_level IS 'Nivel calculado do Trust Score';
COMMENT ON COLUMN chips.trust_factors IS 'Cache dos fatores: {idade_dias, taxa_resposta, msgs_ratio, ...}';
```

### DoD

- [ ] Tabela `chips` criada
- [ ] Campos Salvy presentes
- [ ] Campos Evolution presentes
- [ ] Trust Score e level funcionando
- [ ] Permissoes dinamicas presentes
- [ ] Indices otimizados

---

## Story 1.2: Tabela chip_transitions (Auditoria)

### Objetivo
Registrar todas as transicoes de estado para auditoria completa.

### Migration

```sql
-- Migration: create_chip_transitions
-- Sprint 25 - E01 - Auditoria de transicoes

CREATE TABLE chip_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Transicao
    from_status TEXT,
    to_status TEXT NOT NULL,
    from_trust_score INT,
    to_trust_score INT,
    from_trust_level TEXT,
    to_trust_level TEXT,

    -- Contexto
    reason TEXT,
    triggered_by TEXT NOT NULL, -- 'system', 'api', 'orchestrator', 'early_warning', 'manual'
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX idx_chip_transitions_chip ON chip_transitions(chip_id, created_at DESC);
CREATE INDEX idx_chip_transitions_trigger ON chip_transitions(triggered_by, created_at DESC);

-- Trigger automatico
CREATE OR REPLACE FUNCTION registrar_transicao_chip()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status OR OLD.trust_level IS DISTINCT FROM NEW.trust_level THEN
        INSERT INTO chip_transitions (
            chip_id,
            from_status, to_status,
            from_trust_score, to_trust_score,
            from_trust_level, to_trust_level,
            triggered_by
        ) VALUES (
            NEW.id,
            OLD.status, NEW.status,
            OLD.trust_score, NEW.trust_score,
            OLD.trust_level, NEW.trust_level,
            COALESCE(current_setting('app.triggered_by', true), 'system')
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_chip_transition
    AFTER UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION registrar_transicao_chip();

COMMENT ON TABLE chip_transitions IS 'Auditoria completa de transicoes de estado';
```

### DoD

- [ ] Tabela `chip_transitions` criada
- [ ] Trigger automatico funcionando
- [ ] Indices criados

---

## Story 1.3: Tabela chip_trust_history (Historico Trust Score)

### Objetivo
Armazenar historico de Trust Score para analise de tendencias.

### Migration

```sql
-- Migration: create_chip_trust_history
-- Sprint 25 - E01 - Historico de Trust Score

CREATE TABLE chip_trust_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Score e level
    score INT NOT NULL,
    level TEXT NOT NULL,

    -- Fatores detalhados (snapshot)
    factors JSONB NOT NULL,

    -- Permissoes no momento (snapshot)
    permissoes JSONB NOT NULL,

    recorded_at TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX idx_chip_trust_history ON chip_trust_history(chip_id, recorded_at DESC);

-- Particao por tempo (para escala)
-- Manter apenas ultimos 30 dias via job

COMMENT ON TABLE chip_trust_history IS 'Historico de Trust Score para tendencias';
COMMENT ON COLUMN chip_trust_history.factors IS 'Snapshot: {idade_dias, taxa_resposta, msgs_ratio, erros_24h, ...}';
COMMENT ON COLUMN chip_trust_history.permissoes IS 'Snapshot: {pode_prospectar, pode_followup, limite_hora, ...}';
```

### DoD

- [ ] Tabela criada
- [ ] Indices otimizados
- [ ] Suporta analise de tendencias

---

## Story 1.4: Tabela chip_alerts (Alertas)

### Objetivo
Registrar alertas e incidentes para monitoramento.

### Migration

```sql
-- Migration: create_chip_alerts
-- Sprint 25 - E01 - Alertas

CREATE TABLE chip_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Classificacao
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    tipo TEXT NOT NULL CHECK (tipo IN (
        'trust_drop',           -- Queda significativa de Trust
        'trust_critical',       -- Trust em nivel critico
        'spam_detected',        -- Possivel spam detectado
        'rate_limit',           -- Limite atingido
        'connection_lost',      -- Desconectado
        'high_block_rate',      -- Taxa de bloqueio alta
        'low_response_rate',    -- Taxa de resposta baixa
        'banned',               -- Banido
        'auto_paused',          -- Pausado automaticamente
        'provision_failed',     -- Falha no provisioning
        'meta_policy_violation' -- Violacao de politica Meta
    )),

    -- Descricao
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',

    -- Acao tomada
    acao_tomada TEXT CHECK (acao_tomada IN (
        'none', 'paused', 'reduced_speed', 'blocked_prospeccao',
        'notified_slack', 'auto_replaced'
    )),

    -- Resolucao
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX idx_chip_alerts_unresolved ON chip_alerts(chip_id, severity) WHERE resolved = false;
CREATE INDEX idx_chip_alerts_tipo ON chip_alerts(tipo, created_at DESC);

COMMENT ON TABLE chip_alerts IS 'Alertas e incidentes dos chips';
```

### DoD

- [ ] Tabela criada
- [ ] Tipos de alerta definidos
- [ ] Acoes possiveis listadas

---

## Story 1.5: Tabela chip_pairs (Pareamentos Warmup)

### Objetivo
Gerenciar pareamentos entre chips para warmup cruzado.

### Migration

```sql
-- Migration: create_chip_pairs
-- Sprint 25 - E01 - Pareamentos

CREATE TABLE chip_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_a_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    chip_b_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Estado
    active BOOLEAN DEFAULT true,

    -- Metricas
    messages_exchanged INT DEFAULT 0,
    conversations_count INT DEFAULT 0,
    last_interaction TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),

    -- Constraints
    CONSTRAINT unique_pair UNIQUE (chip_a_id, chip_b_id),
    CONSTRAINT different_chips CHECK (chip_a_id != chip_b_id)
);

-- Indices
CREATE INDEX idx_chip_pairs_active ON chip_pairs(active) WHERE active = true;
CREATE INDEX idx_chip_pairs_chip_a ON chip_pairs(chip_a_id) WHERE active = true;
CREATE INDEX idx_chip_pairs_chip_b ON chip_pairs(chip_b_id) WHERE active = true;

COMMENT ON TABLE chip_pairs IS 'Pareamentos para warmup cruzado';
```

### DoD

- [ ] Tabela criada
- [ ] Constraint unique funcionando
- [ ] Indices para busca rapida

---

## Story 1.6: Tabela warmup_conversations (Conversas Warmup)

### Objetivo
Armazenar historico de conversas de warmup.

### Migration

```sql
-- Migration: create_warmup_conversations
-- Sprint 25 - E01 - Conversas

CREATE TABLE warmup_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id UUID NOT NULL REFERENCES chip_pairs(id) ON DELETE CASCADE,

    -- Conteudo
    tema TEXT NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]',
    turnos INT DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Indices
CREATE INDEX idx_warmup_conversations_pair ON warmup_conversations(pair_id, started_at DESC);

COMMENT ON TABLE warmup_conversations IS 'Historico de conversas de warmup';
COMMENT ON COLUMN warmup_conversations.messages IS 'Array JSON: [{from: "A", text: "...", sent_at: "...", media_type: "..."}]';
```

### DoD

- [ ] Tabela criada
- [ ] Suporta diferentes tipos de midia

---

## Story 1.7: Tabela chip_interactions (Tracking Granular)

### Objetivo
Tracking granular de todas as interacoes para calculo de metricas.

### Migration

```sql
-- Migration: create_chip_interactions
-- Sprint 25 - E01 - Tracking

CREATE TABLE chip_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Tipo
    tipo TEXT NOT NULL CHECK (tipo IN (
        'msg_enviada', 'msg_recebida', 'chamada',
        'status_criado', 'grupo_entrada', 'grupo_saida', 'midia_enviada'
    )),

    -- Contexto
    destinatario TEXT,
    midia_tipo TEXT CHECK (midia_tipo IN ('text', 'audio', 'image', 'video', 'document', 'sticker')),

    -- Para mensagens enviadas
    obteve_resposta BOOLEAN,
    tempo_resposta_segundos INT,

    -- Erros
    erro_codigo TEXT,
    erro_mensagem TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indices otimizados
CREATE INDEX idx_chip_interactions_chip_time ON chip_interactions(chip_id, created_at DESC);
CREATE INDEX idx_chip_interactions_erros ON chip_interactions(chip_id, erro_codigo) WHERE erro_codigo IS NOT NULL;
CREATE INDEX idx_chip_interactions_resposta ON chip_interactions(chip_id, obteve_resposta) WHERE tipo = 'msg_enviada';

COMMENT ON TABLE chip_interactions IS 'Tracking granular de interacoes';
```

### DoD

- [ ] Tabela criada
- [ ] Tipos de interacao definidos
- [ ] Indices para queries de metricas

---

## Story 1.8: Tabela meta_policies (RAG)

### Objetivo
Armazenar politicas Meta com embeddings para consulta RAG.

### Migration

```sql
-- Migration: create_meta_policies
-- Sprint 25 - E01 - RAG

-- Habilitar pgvector se nao estiver
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE meta_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    categoria TEXT NOT NULL CHECK (categoria IN (
        'limites', 'proibicoes', 'boas_praticas', 'motivos_ban', 'quality_rating'
    )),
    titulo TEXT NOT NULL UNIQUE,

    -- Conteudo
    conteudo TEXT NOT NULL,
    fonte_url TEXT,
    fonte_nome TEXT,

    -- Embedding para RAG
    embedding vector(1024),  -- Voyage AI

    -- Versionamento
    versao INT DEFAULT 1,
    valido_desde DATE DEFAULT CURRENT_DATE,
    valido_ate DATE,

    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX idx_meta_policies_categoria ON meta_policies(categoria);
CREATE INDEX idx_meta_policies_embedding ON meta_policies USING ivfflat (embedding vector_cosine_ops);

-- Trigger updated_at
CREATE TRIGGER trigger_meta_policies_updated_at
    BEFORE UPDATE ON meta_policies FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Funcao de busca por similaridade
CREATE OR REPLACE FUNCTION match_meta_policies(
    query_embedding vector(1024),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    filter_categoria text DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    categoria text,
    titulo text,
    conteudo text,
    fonte_url text,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        mp.id,
        mp.categoria,
        mp.titulo,
        mp.conteudo,
        mp.fonte_url,
        1 - (mp.embedding <=> query_embedding) as similarity
    FROM meta_policies mp
    WHERE
        (filter_categoria IS NULL OR mp.categoria = filter_categoria)
        AND (mp.valido_ate IS NULL OR mp.valido_ate >= CURRENT_DATE)
        AND 1 - (mp.embedding <=> query_embedding) > match_threshold
    ORDER BY mp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON TABLE meta_policies IS 'RAG de politicas Meta para consulta';
```

### DoD

- [ ] pgvector habilitado
- [ ] Tabela criada
- [ ] Funcao de busca funcionando

---

## Story 1.9: Tabela pool_config (Configuracao)

### Objetivo
Configuracao central do pool de chips.

### Migration

```sql
-- Migration: create_pool_config
-- Sprint 25 - E01 - Config

CREATE TABLE pool_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Producao
    producao_min INT DEFAULT 5,
    producao_max INT DEFAULT 10,

    -- Warming buffer
    warmup_buffer INT DEFAULT 10,
    warmup_days INT DEFAULT 21,

    -- Ready (reserva quente)
    ready_min INT DEFAULT 3,

    -- Trust thresholds
    trust_min_for_ready INT DEFAULT 85,
    trust_degraded_threshold INT DEFAULT 40,
    trust_critical_threshold INT DEFAULT 20,

    -- Trust level thresholds
    trust_verde_min INT DEFAULT 80,
    trust_amarelo_min INT DEFAULT 60,
    trust_laranja_min INT DEFAULT 40,
    trust_vermelho_min INT DEFAULT 20,

    -- Auto-provisioning
    auto_provision BOOLEAN DEFAULT true,
    default_ddd INT DEFAULT 11,

    -- Limites por tipo de msg
    limite_prospeccao_hora INT DEFAULT 10,
    limite_followup_hora INT DEFAULT 20,
    limite_resposta_hora INT DEFAULT 50,

    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT
);

-- Inserir config padrao
INSERT INTO pool_config DEFAULT VALUES;

-- Trigger updated_at
CREATE TRIGGER trigger_pool_config_updated_at
    BEFORE UPDATE ON pool_config FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

COMMENT ON TABLE pool_config IS 'Configuracao central do pool de chips';
```

### DoD

- [ ] Tabela criada
- [ ] Config padrao inserida

---

## Story 1.10: Funcao update_updated_at

### Migration

```sql
-- Migration: create_update_updated_at_function
-- Sprint 25 - E01 - Funcao auxiliar

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar em chips
CREATE TRIGGER trigger_chips_updated_at
    BEFORE UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

---

## Checklist do Epico

- [ ] **E01.1** - Tabela `chips` criada
- [ ] **E01.2** - Tabela `chip_transitions` criada
- [ ] **E01.3** - Tabela `chip_trust_history` criada
- [ ] **E01.4** - Tabela `chip_alerts` criada
- [ ] **E01.5** - Tabela `chip_pairs` criada
- [ ] **E01.6** - Tabela `warmup_conversations` criada
- [ ] **E01.7** - Tabela `chip_interactions` criada
- [ ] **E01.8** - Tabela `meta_policies` criada (RAG)
- [ ] **E01.9** - Tabela `pool_config` criada
- [ ] **E01.10** - Triggers funcionando
- [ ] Tipos TypeScript gerados

---

## Dependências Cruzadas

**Tabelas adicionais definidas em outros épicos:**

| Épico | Tabelas | Descrição |
|-------|---------|-----------|
| E12 (Group Entry Engine) | `group_sources`, `group_links`, `group_entry_queue`, `group_entry_history` | Entrada segura em grupos WhatsApp |

> **Nota:** As tabelas de E12 dependem da tabela `chips` (FK). Executar E01 antes de E12.

---

## Diagrama ER

```
chips (central)
├── id (PK)
├── telefone (UNIQUE)
├── salvy_id (FK Salvy)
├── instance_name (FK Evolution)
├── status
├── tipo (julia/listener)  ← SEPARAÇÃO DE POOLS
├── fase_warmup
├── trust_score (0-100)
├── trust_level (verde/amarelo/laranja/vermelho/critico)
├── trust_factors (JSONB)
├── pode_prospectar
├── pode_followup
├── pode_responder
├── limite_hora
├── limite_dia
└── ... metricas

chip_transitions
├── id (PK)
├── chip_id (FK → chips)
├── from_status → to_status
├── from_trust → to_trust
└── triggered_by

chip_trust_history
├── id (PK)
├── chip_id (FK → chips)
├── score, level
├── factors (JSONB)
└── permissoes (JSONB)

chip_alerts
├── id (PK)
├── chip_id (FK → chips)
├── severity, tipo
├── acao_tomada
└── resolved

chip_pairs
├── id (PK)
├── chip_a_id (FK → chips)
├── chip_b_id (FK → chips)
└── active

warmup_conversations
├── id (PK)
├── pair_id (FK → chip_pairs)
├── tema
└── messages (JSONB)

chip_interactions
├── id (PK)
├── chip_id (FK → chips)
├── tipo
├── destinatario
└── obteve_resposta

meta_policies (RAG)
├── id (PK)
├── categoria
├── titulo
├── conteudo
└── embedding (vector)

pool_config
├── producao_min/max
├── warmup_buffer
├── ready_min
└── trust thresholds
```
