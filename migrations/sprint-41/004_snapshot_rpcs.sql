-- Sprint 41: RPCs para criar snapshots diários e resetar contadores dos chips

-- RPC para criar snapshot de um chip específico
CREATE OR REPLACE FUNCTION chip_criar_snapshot_diario(
    p_chip_id UUID,
    p_data DATE DEFAULT CURRENT_DATE - INTERVAL '1 day'
)
RETURNS TABLE (
    snapshot_id UUID,
    criado BOOLEAN,
    mensagem TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_chip RECORD;
    v_snapshot_id UUID;
    v_msgs_enviadas INTEGER;
    v_msgs_recebidas INTEGER;
    v_msgs_entregues INTEGER;
    v_msgs_lidas INTEGER;
    v_msgs_erro INTEGER;
    v_taxa_delivery NUMERIC(5,2);
    v_taxa_resposta NUMERIC(5,2);
BEGIN
    -- Buscar dados do chip
    SELECT * INTO v_chip FROM chips WHERE id = p_chip_id;

    IF v_chip IS NULL THEN
        RETURN QUERY SELECT NULL::UUID, FALSE, 'Chip não encontrado'::TEXT;
        RETURN;
    END IF;

    -- Verificar se já existe snapshot para esta data
    SELECT id INTO v_snapshot_id
    FROM chip_daily_snapshots
    WHERE chip_id = p_chip_id AND data = p_data;

    IF v_snapshot_id IS NOT NULL THEN
        RETURN QUERY SELECT v_snapshot_id, FALSE, 'Snapshot já existe'::TEXT;
        RETURN;
    END IF;

    -- Calcular métricas do período a partir das interações
    SELECT
        COUNT(*) FILTER (WHERE tipo = 'saida') AS enviadas,
        COUNT(*) FILTER (WHERE tipo = 'entrada') AS recebidas,
        COUNT(*) FILTER (WHERE tipo = 'saida' AND delivery_status = 'delivered') AS entregues,
        COUNT(*) FILTER (WHERE tipo = 'saida' AND delivery_status = 'read') AS lidas,
        COUNT(*) FILTER (WHERE tipo = 'saida' AND delivery_status = 'failed') AS erro
    INTO v_msgs_enviadas, v_msgs_recebidas, v_msgs_entregues, v_msgs_lidas, v_msgs_erro
    FROM interacoes
    WHERE chip_id = p_chip_id
      AND created_at::DATE = p_data;

    -- Calcular taxas
    IF v_msgs_enviadas > 0 THEN
        v_taxa_delivery := ((v_msgs_entregues + v_msgs_lidas)::NUMERIC / v_msgs_enviadas * 100);
    ELSE
        v_taxa_delivery := NULL;
    END IF;

    -- Taxa de resposta: usar contadores do chip se disponíveis, senão calcular
    IF v_chip.msgs_enviadas_total > 0 AND v_chip.msgs_recebidas_total > 0 THEN
        v_taxa_resposta := (v_msgs_recebidas::NUMERIC / NULLIF(v_msgs_enviadas, 0) * 100);
    ELSE
        v_taxa_resposta := NULL;
    END IF;

    -- Criar snapshot
    INSERT INTO chip_daily_snapshots (
        chip_id,
        data,
        msgs_enviadas,
        msgs_recebidas,
        msgs_entregues,
        msgs_lidas,
        msgs_erro,
        taxa_delivery,
        taxa_resposta,
        trust_score,
        status
    ) VALUES (
        p_chip_id,
        p_data,
        COALESCE(v_msgs_enviadas, 0),
        COALESCE(v_msgs_recebidas, 0),
        COALESCE(v_msgs_entregues, 0),
        COALESCE(v_msgs_lidas, 0),
        COALESCE(v_msgs_erro, 0),
        v_taxa_delivery,
        v_taxa_resposta,
        v_chip.trust_score,
        v_chip.status
    )
    RETURNING id INTO v_snapshot_id;

    RETURN QUERY SELECT v_snapshot_id, TRUE, 'Snapshot criado com sucesso'::TEXT;
END;
$$;

-- RPC para criar snapshots de todos os chips ativos
CREATE OR REPLACE FUNCTION chip_criar_snapshots_todos(
    p_data DATE DEFAULT CURRENT_DATE - INTERVAL '1 day'
)
RETURNS TABLE (
    total_chips INTEGER,
    snapshots_criados INTEGER,
    snapshots_existentes INTEGER,
    erros INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_chip RECORD;
    v_result RECORD;
    v_total INTEGER := 0;
    v_criados INTEGER := 0;
    v_existentes INTEGER := 0;
    v_erros INTEGER := 0;
BEGIN
    FOR v_chip IN
        SELECT id FROM chips
        WHERE status IN ('active', 'warming', 'ready', 'cooldown')
    LOOP
        v_total := v_total + 1;

        BEGIN
            SELECT * INTO v_result
            FROM chip_criar_snapshot_diario(v_chip.id, p_data);

            IF v_result.criado THEN
                v_criados := v_criados + 1;
            ELSE
                v_existentes := v_existentes + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            v_erros := v_erros + 1;
        END;
    END LOOP;

    RETURN QUERY SELECT v_total, v_criados, v_existentes, v_erros;
END;
$$;

-- RPC para resetar contadores diários dos chips (após criar snapshot)
CREATE OR REPLACE FUNCTION chip_resetar_contadores_diarios()
RETURNS TABLE (
    chips_resetados INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Resetar contadores diários mantendo os totais
    UPDATE chips
    SET
        msgs_enviadas_hoje = 0,
        msgs_recebidas_hoje = 0,
        updated_at = NOW()
    WHERE status IN ('active', 'warming', 'ready', 'cooldown');

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN QUERY SELECT v_count;
END;
$$;

COMMENT ON FUNCTION chip_criar_snapshot_diario IS
    'Cria snapshot das métricas de um chip para uma data específica';
COMMENT ON FUNCTION chip_criar_snapshots_todos IS
    'Cria snapshots de todos os chips ativos para uma data específica';
COMMENT ON FUNCTION chip_resetar_contadores_diarios IS
    'Reseta contadores diários dos chips (executar após criar snapshots)';
