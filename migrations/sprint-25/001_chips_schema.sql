-- =====================================================
-- Sprint 25: Modelo de Dados Unificado (E01)
-- Chips + Trust Score + Warming
-- =====================================================

-- =====================================================
-- TABELA CENTRAL: chips
-- Unifica todo ciclo de vida do chip
-- =====================================================
CREATE TABLE IF NOT EXISTS chips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telefone TEXT UNIQUE NOT NULL,

    -- SALVY
    salvy_id TEXT UNIQUE,
    salvy_status TEXT CHECK (salvy_status IN ('active', 'blocked', 'canceled')),
    salvy_created_at TIMESTAMPTZ,

    -- EVOLUTION
    instance_name TEXT UNIQUE NOT NULL,
    evolution_connected BOOLEAN DEFAULT false,
    evolution_qr_code TEXT,

    -- ESTADO NO SISTEMA
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

    -- WARMING
    fase_warmup TEXT DEFAULT 'repouso'
        CHECK (fase_warmup IN (
            'repouso',            -- Dia 0: 24-48h sem atividade
            'setup',              -- Dias 1-3: apenas config
            'primeiros_contatos', -- Dias 4-7: max 10 msgs/dia
            'expansao',           -- Dias 8-14: max 30 msgs/dia
            'pre_operacao',       -- Dias 15-21: max 50 msgs/dia
            'teste_graduacao',    -- Dia 22: teste formal
            'operacao'            -- Dia 22+: pronto
        )),
    fase_iniciada_em TIMESTAMPTZ DEFAULT now(),
    warming_started_at TIMESTAMPTZ,
    warming_day INT DEFAULT 0,

    -- TRUST SCORE
    trust_score INT DEFAULT 50 CHECK (trust_score >= 0 AND trust_score <= 100),
    trust_level TEXT DEFAULT 'amarelo'
        CHECK (trust_level IN ('verde', 'amarelo', 'laranja', 'vermelho', 'critico')),
    ultimo_calculo_trust TIMESTAMPTZ,
    trust_factors JSONB DEFAULT '{}',

    -- METRICAS
    msgs_enviadas_total INT DEFAULT 0,
    msgs_recebidas_total INT DEFAULT 0,
    msgs_enviadas_hoje INT DEFAULT 0,
    msgs_recebidas_hoje INT DEFAULT 0,
    taxa_resposta DECIMAL(5,4) DEFAULT 0,
    taxa_delivery DECIMAL(5,4) DEFAULT 1,
    taxa_block DECIMAL(5,4) DEFAULT 0,
    conversas_bidirecionais INT DEFAULT 0,
    grupos_count INT DEFAULT 0,
    tipos_midia_usados TEXT[] DEFAULT '{}',
    erros_ultimas_24h INT DEFAULT 0,
    dias_sem_erro INT DEFAULT 0,

    -- PERMISSOES (calculadas do Trust Score)
    pode_prospectar BOOLEAN DEFAULT false,
    pode_followup BOOLEAN DEFAULT false,
    pode_responder BOOLEAN DEFAULT true,
    limite_hora INT DEFAULT 5,
    limite_dia INT DEFAULT 30,
    delay_minimo_segundos INT DEFAULT 120,

    -- COOLDOWN
    last_activity_start TIMESTAMPTZ,
    cooldown_until TIMESTAMPTZ,

    -- PRODUCAO
    promoted_to_active_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    dias_em_producao INT DEFAULT 0,

    -- AUDITORIA
    banned_at TIMESTAMPTZ,
    ban_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_chips_status ON chips(status);
CREATE INDEX IF NOT EXISTS idx_chips_trust ON chips(trust_score DESC) WHERE status IN ('warming', 'ready', 'active');
CREATE INDEX IF NOT EXISTS idx_chips_ready ON chips(trust_score DESC, warming_started_at ASC) WHERE status = 'ready';


-- =====================================================
-- TRANSICOES DE ESTADO (auditoria)
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    from_status TEXT,
    to_status TEXT NOT NULL,
    from_trust_score INT,
    to_trust_score INT,

    reason TEXT,
    triggered_by TEXT NOT NULL, -- 'system', 'api', 'orchestrator', 'early_warning'
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_transitions_chip ON chip_transitions(chip_id, created_at DESC);


-- =====================================================
-- HISTORICO DE TRUST SCORE
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_trust_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    score INT NOT NULL,
    level TEXT NOT NULL,
    factors JSONB NOT NULL,
    permissoes JSONB NOT NULL,

    recorded_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_trust_history ON chip_trust_history(chip_id, recorded_at DESC);


-- =====================================================
-- ALERTAS DE CHIP
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    tipo TEXT NOT NULL,
    message TEXT NOT NULL,

    acao_tomada TEXT,  -- 'paused', 'reduced_speed', 'none'

    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_alerts_unresolved ON chip_alerts(chip_id, severity) WHERE resolved = false;


-- =====================================================
-- PAREAMENTOS PARA WARM-UP
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_a_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    chip_b_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    active BOOLEAN DEFAULT true,
    messages_exchanged INT DEFAULT 0,
    conversations_count INT DEFAULT 0,
    last_interaction TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_pair UNIQUE (chip_a_id, chip_b_id),
    CONSTRAINT different_chips CHECK (chip_a_id != chip_b_id)
);

CREATE INDEX IF NOT EXISTS idx_chip_pairs_active ON chip_pairs(active) WHERE active = true;


-- =====================================================
-- AFFINITY MEDICO-CHIP
-- Medico prefere continuar no mesmo chip
-- =====================================================
CREATE TABLE IF NOT EXISTS medico_chip_affinity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medico_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    msgs_trocadas INT DEFAULT 1,
    ultima_interacao TIMESTAMPTZ DEFAULT now(),

    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(medico_id, chip_id)
);

CREATE INDEX IF NOT EXISTS idx_affinity_medico ON medico_chip_affinity(medico_id, ultima_interacao DESC);
CREATE INDEX IF NOT EXISTS idx_affinity_chip ON medico_chip_affinity(chip_id) WHERE msgs_trocadas > 0;


-- =====================================================
-- CONVERSAS DE WARM-UP
-- =====================================================
CREATE TABLE IF NOT EXISTS warmup_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id UUID NOT NULL REFERENCES chip_pairs(id) ON DELETE CASCADE,

    tema TEXT NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]',
    turnos INT DEFAULT 0,

    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_warmup_conversations_pair ON warmup_conversations(pair_id, started_at DESC);


-- =====================================================
-- INTERACOES GRANULARES
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    tipo TEXT NOT NULL CHECK (tipo IN (
        'msg_enviada', 'msg_recebida', 'chamada',
        'status_criado', 'grupo_entrada', 'grupo_saida', 'midia_enviada'
    )),

    destinatario TEXT,
    midia_tipo TEXT CHECK (midia_tipo IN ('text', 'audio', 'image', 'video', 'document', 'sticker')),

    obteve_resposta BOOLEAN,
    tempo_resposta_segundos INT,

    erro_codigo TEXT,
    erro_mensagem TEXT,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_interactions_chip_time ON chip_interactions(chip_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_chip_interactions_erros ON chip_interactions(chip_id, erro_codigo) WHERE erro_codigo IS NOT NULL;


-- =====================================================
-- RAG: POLITICAS META
-- =====================================================
CREATE TABLE IF NOT EXISTS meta_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    categoria TEXT NOT NULL,  -- 'limites', 'proibicoes', 'boas_praticas', 'motivos_ban', 'quality_rating'
    titulo TEXT NOT NULL,

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

CREATE INDEX IF NOT EXISTS idx_meta_policies_categoria ON meta_policies(categoria);
-- Note: ivfflat index requires data, will create after seeding


-- =====================================================
-- CONFIGURACAO DO POOL
-- =====================================================
CREATE TABLE IF NOT EXISTS pool_config (
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
    trust_degraded_threshold INT DEFAULT 60,
    trust_critical_threshold INT DEFAULT 20,

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

-- Inserir config padrao se nao existir
INSERT INTO pool_config DEFAULT VALUES
ON CONFLICT DO NOTHING;
