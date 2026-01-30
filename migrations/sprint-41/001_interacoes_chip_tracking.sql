-- Sprint 41: Adicionar chip_id e status de entrega à tabela interacoes
-- Permite rastrear qual chip enviou cada mensagem e o status de entrega

-- Adicionar coluna chip_id referenciando a tabela chips
ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS chip_id UUID REFERENCES chips(id);

-- Adicionar coluna delivery_status com constraint de valores válidos
ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS delivery_status TEXT
    CHECK (delivery_status IN ('pending', 'sent', 'delivered', 'read', 'failed'));

-- Adicionar coluna para timestamp da última atualização de status
ALTER TABLE interacoes ADD COLUMN IF NOT EXISTS delivery_status_at TIMESTAMPTZ;

-- Índice para buscar interações por chip
CREATE INDEX IF NOT EXISTS idx_interacoes_chip_id
    ON interacoes(chip_id)
    WHERE chip_id IS NOT NULL;

-- Índice para buscar interações por provider_message_id (usado para atualizar status)
CREATE INDEX IF NOT EXISTS idx_interacoes_provider_message_id
    ON interacoes(provider_message_id)
    WHERE provider_message_id IS NOT NULL;

-- Índice composto para queries de métricas por chip e data
CREATE INDEX IF NOT EXISTS idx_interacoes_chip_created
    ON interacoes(chip_id, created_at)
    WHERE chip_id IS NOT NULL;

COMMENT ON COLUMN interacoes.chip_id IS 'ID do chip que enviou/recebeu a mensagem';
COMMENT ON COLUMN interacoes.delivery_status IS 'Status de entrega: pending, sent, delivered, read, failed';
COMMENT ON COLUMN interacoes.delivery_status_at IS 'Timestamp da última atualização do status de entrega';
