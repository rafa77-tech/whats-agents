-- =====================================================
-- Sprint 25: Triggers e Functions (E01)
-- =====================================================

-- =====================================================
-- TRIGGER: updated_at automatico
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
-- FUNCAO: Registrar transicao de estado
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
-- FUNCAO: Reset contadores diarios (rodar via cron)
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
-- FUNCAO: Busca de politicas por similaridade (RAG)
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
-- VIEW: Chips disponiveis para producao
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


-- =====================================================
-- VIEW: Status do pool
-- =====================================================
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


-- =====================================================
-- VIEW: Chips que precisam de atencao
-- =====================================================
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
