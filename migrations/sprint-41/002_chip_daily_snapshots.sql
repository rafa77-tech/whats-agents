-- Sprint 41: Tabela para snapshots diários de métricas dos chips
-- Captura estado dos contadores antes do reset diário para análise histórica

CREATE TABLE IF NOT EXISTS chip_daily_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,
    data DATE NOT NULL,

    -- Contadores de mensagens
    msgs_enviadas INTEGER DEFAULT 0,
    msgs_recebidas INTEGER DEFAULT 0,
    msgs_entregues INTEGER DEFAULT 0,
    msgs_lidas INTEGER DEFAULT 0,
    msgs_erro INTEGER DEFAULT 0,

    -- Taxas calculadas
    taxa_delivery NUMERIC(5,2),  -- % mensagens entregues do total enviado
    taxa_resposta NUMERIC(5,2),  -- % conversas com resposta

    -- Estado do chip no momento do snapshot
    trust_score INTEGER,
    status TEXT,

    -- Metadados
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraint única para evitar duplicatas
    UNIQUE(chip_id, data)
);

-- Índice para queries por chip
CREATE INDEX IF NOT EXISTS idx_chip_snapshots_chip_id
    ON chip_daily_snapshots(chip_id);

-- Índice para queries por data
CREATE INDEX IF NOT EXISTS idx_chip_snapshots_data
    ON chip_daily_snapshots(data DESC);

-- Índice composto para relatórios
CREATE INDEX IF NOT EXISTS idx_chip_snapshots_chip_data
    ON chip_daily_snapshots(chip_id, data DESC);

COMMENT ON TABLE chip_daily_snapshots IS 'Snapshots diários das métricas de cada chip para análise histórica';
COMMENT ON COLUMN chip_daily_snapshots.taxa_delivery IS 'Percentual de mensagens entregues em relação ao total enviado';
COMMENT ON COLUMN chip_daily_snapshots.taxa_resposta IS 'Percentual de conversas que receberam resposta';
