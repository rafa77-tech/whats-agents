-- Sprint 36: Tabela para histórico de transições do Circuit Breaker
-- Permite diagnóstico e análise de incidentes

-- =====================================================
-- Tabela: circuit_transitions
-- =====================================================
CREATE TABLE IF NOT EXISTS circuit_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação do circuit
    circuit_name TEXT NOT NULL,

    -- Transição
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason TEXT,

    -- Métricas no momento da transição
    falhas_consecutivas INTEGER DEFAULT 0,
    tentativas_half_open INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- Índices para consultas comuns
-- =====================================================

-- Buscar transições por circuit
CREATE INDEX IF NOT EXISTS idx_circuit_transitions_name_date
ON circuit_transitions(circuit_name, created_at DESC);

-- Buscar transições recentes
CREATE INDEX IF NOT EXISTS idx_circuit_transitions_date
ON circuit_transitions(created_at DESC);

-- =====================================================
-- Comentários
-- =====================================================
COMMENT ON TABLE circuit_transitions IS 'Histórico de transições do circuit breaker para diagnóstico';
COMMENT ON COLUMN circuit_transitions.circuit_name IS 'Nome do circuit (evolution, claude, supabase)';
COMMENT ON COLUMN circuit_transitions.from_state IS 'Estado anterior (closed, open, half_open)';
COMMENT ON COLUMN circuit_transitions.to_state IS 'Novo estado';
COMMENT ON COLUMN circuit_transitions.reason IS 'Motivo da transição';

-- =====================================================
-- Política de retenção (opcional - limpar dados antigos)
-- =====================================================

-- Função para limpar transições antigas (manter 30 dias)
CREATE OR REPLACE FUNCTION limpar_circuit_transitions_antigas()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_deleted INTEGER;
BEGIN
    DELETE FROM circuit_transitions
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RETURN v_deleted;
END;
$$;

-- Grant permissions
GRANT SELECT, INSERT ON circuit_transitions TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION limpar_circuit_transitions_antigas() TO service_role;
