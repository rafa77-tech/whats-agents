-- =====================================================
-- Sprint 25: MIGRATION COMPLETA
-- Execute este arquivo no Supabase SQL Editor
-- URL: https://supabase.com/dashboard/project/jyqgbzhqavgpxqacduoi/sql
-- =====================================================

-- =====================================================
-- PARTE 1: TABELA CENTRAL chips
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

-- Indices para chips
CREATE INDEX IF NOT EXISTS idx_chips_status ON chips(status);
CREATE INDEX IF NOT EXISTS idx_chips_trust ON chips(trust_score DESC) WHERE status IN ('warming', 'ready', 'active');
CREATE INDEX IF NOT EXISTS idx_chips_ready ON chips(trust_score DESC, warming_started_at ASC) WHERE status = 'ready';


-- =====================================================
-- PARTE 2: TRANSICOES DE ESTADO (auditoria)
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    from_status TEXT,
    to_status TEXT NOT NULL,
    from_trust_score INT,
    to_trust_score INT,

    reason TEXT,
    triggered_by TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_transitions_chip ON chip_transitions(chip_id, created_at DESC);


-- =====================================================
-- PARTE 3: HISTORICO DE TRUST SCORE
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
-- PARTE 4: ALERTAS DE CHIP
-- =====================================================
CREATE TABLE IF NOT EXISTS chip_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    tipo TEXT NOT NULL,
    message TEXT NOT NULL,

    acao_tomada TEXT,

    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,

    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chip_alerts_unresolved ON chip_alerts(chip_id, severity) WHERE resolved = false;


-- =====================================================
-- PARTE 5: PAREAMENTOS PARA WARM-UP
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
-- PARTE 6: AFFINITY MEDICO-CHIP
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
-- PARTE 7: CONVERSAS DE WARM-UP
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
-- PARTE 8: INTERACOES GRANULARES
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
-- PARTE 9: RAG - POLITICAS META
-- =====================================================
CREATE TABLE IF NOT EXISTS meta_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL,
    fonte_url TEXT,
    fonte_nome TEXT,

    embedding vector(1024),

    versao INT DEFAULT 1,
    valido_desde DATE DEFAULT CURRENT_DATE,
    valido_ate DATE,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_meta_policies_categoria ON meta_policies(categoria);


-- =====================================================
-- PARTE 10: CONFIGURACAO DO POOL
-- =====================================================
CREATE TABLE IF NOT EXISTS pool_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    producao_min INT DEFAULT 5,
    producao_max INT DEFAULT 10,
    warmup_buffer INT DEFAULT 10,
    warmup_days INT DEFAULT 21,
    ready_min INT DEFAULT 3,

    trust_min_for_ready INT DEFAULT 85,
    trust_degraded_threshold INT DEFAULT 60,
    trust_critical_threshold INT DEFAULT 20,

    auto_provision BOOLEAN DEFAULT true,
    default_ddd INT DEFAULT 11,

    limite_prospeccao_hora INT DEFAULT 10,
    limite_followup_hora INT DEFAULT 20,
    limite_resposta_hora INT DEFAULT 50,

    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT
);

INSERT INTO pool_config DEFAULT VALUES ON CONFLICT DO NOTHING;


-- =====================================================
-- PARTE 11: TRIGGERS
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_chips_updated_at ON chips;
CREATE TRIGGER trigger_chips_updated_at
    BEFORE UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trigger_pool_config_updated_at ON pool_config;
CREATE TRIGGER trigger_pool_config_updated_at
    BEFORE UPDATE ON pool_config FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

DROP TRIGGER IF EXISTS trigger_meta_policies_updated_at ON meta_policies;
CREATE TRIGGER trigger_meta_policies_updated_at
    BEFORE UPDATE ON meta_policies FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();


-- =====================================================
-- PARTE 12: FUNCAO DE TRANSICAO
-- =====================================================
CREATE OR REPLACE FUNCTION registrar_transicao()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status OR OLD.trust_score IS DISTINCT FROM NEW.trust_score THEN
        INSERT INTO chip_transitions (
            chip_id, from_status, to_status,
            from_trust_score, to_trust_score,
            triggered_by
        ) VALUES (
            NEW.id, OLD.status, NEW.status,
            OLD.trust_score, NEW.trust_score,
            COALESCE(current_setting('app.triggered_by', true), 'system')
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_chip_transition ON chips;
CREATE TRIGGER trigger_chip_transition
    AFTER UPDATE ON chips FOR EACH ROW
    EXECUTE FUNCTION registrar_transicao();


-- =====================================================
-- PARTE 13: FUNCAO RESET DIARIO
-- =====================================================
CREATE OR REPLACE FUNCTION reset_chip_daily_counters()
RETURNS void AS $$
BEGIN
    UPDATE chips SET
        msgs_enviadas_hoje = 0,
        msgs_recebidas_hoje = 0
    WHERE msgs_enviadas_hoje > 0 OR msgs_recebidas_hoje > 0;
END;
$$ LANGUAGE plpgsql;


-- =====================================================
-- PARTE 14: FUNCAO RAG
-- =====================================================
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
        AND mp.embedding IS NOT NULL
        AND 1 - (mp.embedding <=> query_embedding) > match_threshold
    ORDER BY mp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- =====================================================
-- PARTE 15: VIEWS
-- =====================================================
CREATE OR REPLACE VIEW chips_ready_for_production AS
SELECT
    c.*,
    CASE
        WHEN c.trust_score >= 85 THEN 'excellent'
        WHEN c.trust_score >= 70 THEN 'good'
        WHEN c.trust_score >= 50 THEN 'acceptable'
        ELSE 'needs_improvement'
    END as readiness_level
FROM chips c
WHERE c.status = 'ready'
  AND c.trust_score >= (SELECT trust_min_for_ready FROM pool_config LIMIT 1)
ORDER BY c.trust_score DESC, c.warming_started_at ASC;


CREATE OR REPLACE VIEW pool_status AS
SELECT
    COUNT(*) FILTER (WHERE status = 'active') as chips_ativos,
    COUNT(*) FILTER (WHERE status = 'ready') as chips_ready,
    COUNT(*) FILTER (WHERE status = 'warming') as chips_warming,
    COUNT(*) FILTER (WHERE status = 'degraded') as chips_degraded,
    COUNT(*) FILTER (WHERE status = 'banned') as chips_banned,
    COUNT(*) FILTER (WHERE status = 'paused') as chips_paused,
    COUNT(*) as total_chips,
    AVG(trust_score) FILTER (WHERE status IN ('active', 'ready', 'warming')) as avg_trust_score,
    SUM(msgs_enviadas_hoje) as total_msgs_hoje
FROM chips;


CREATE OR REPLACE VIEW chips_needing_attention AS
SELECT
    c.*,
    CASE
        WHEN c.trust_level = 'critico' THEN 'CRITICAL: Trust score critico'
        WHEN c.trust_level = 'vermelho' THEN 'WARNING: Trust score vermelho'
        WHEN c.erros_ultimas_24h > 5 THEN 'WARNING: Muitos erros recentes'
        WHEN c.cooldown_until > now() THEN 'INFO: Em cooldown'
        ELSE 'INFO: Monitoramento'
    END as attention_reason
FROM chips c
WHERE c.trust_level IN ('vermelho', 'critico')
   OR c.erros_ultimas_24h > 5
   OR (c.status = 'warming' AND c.warming_day > 25);


-- =====================================================
-- FIM DA MIGRATION SPRINT 25
-- =====================================================
