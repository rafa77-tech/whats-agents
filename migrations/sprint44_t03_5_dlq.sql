-- Sprint 44 T03.5: Dead Letter Queue para mensagens falhadas
-- Tabela para armazenar mensagens que excederam tentativas para análise posterior
-- EXECUTAR MANUALMENTE: Como o MCP Supabase está offline, executar via dashboard

CREATE TABLE IF NOT EXISTS fila_mensagens_dlq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Referência à mensagem original
    mensagem_original_id UUID NOT NULL,

    -- Dados copiados da mensagem original
    cliente_id UUID REFERENCES clientes(id),
    conversa_id UUID,
    conteudo TEXT NOT NULL,
    tipo VARCHAR(50),
    prioridade INTEGER DEFAULT 5,

    -- Informações de falha
    tentativas INTEGER NOT NULL DEFAULT 0,
    ultimo_erro TEXT,
    outcome VARCHAR(50),
    outcome_reason_code VARCHAR(255),

    -- Metadata original
    metadata JSONB DEFAULT '{}',

    -- Rastreamento
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    original_created_at TIMESTAMP WITH TIME ZONE,
    movido_para_dlq_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Para reprocessamento
    reprocessado BOOLEAN DEFAULT FALSE,
    reprocessado_em TIMESTAMP WITH TIME ZONE,
    reprocessado_por VARCHAR(100)
);

-- Índices para consulta
CREATE INDEX IF NOT EXISTS idx_fila_dlq_cliente_id ON fila_mensagens_dlq(cliente_id);
CREATE INDEX IF NOT EXISTS idx_fila_dlq_created_at ON fila_mensagens_dlq(movido_para_dlq_em DESC);
CREATE INDEX IF NOT EXISTS idx_fila_dlq_reprocessado ON fila_mensagens_dlq(reprocessado);
CREATE INDEX IF NOT EXISTS idx_fila_dlq_outcome ON fila_mensagens_dlq(outcome);

-- Comentário na tabela
COMMENT ON TABLE fila_mensagens_dlq IS 'Sprint 44 T03.5: Dead Letter Queue para análise de mensagens falhadas';
