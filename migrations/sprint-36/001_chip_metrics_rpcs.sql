-- Sprint 36: RPCs para métricas de chips
-- T08.1: Incrementar contadores após envio de mensagem
-- T08.2: Registrar resposta recebida por chip

-- =====================================================
-- RPC: Registrar envio com sucesso
-- =====================================================
CREATE OR REPLACE FUNCTION chip_registrar_envio_sucesso(p_chip_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSON;
BEGIN
    UPDATE chips
    SET
        msgs_enviadas_total = COALESCE(msgs_enviadas_total, 0) + 1,
        msgs_enviadas_hoje = COALESCE(msgs_enviadas_hoje, 0) + 1,
        ultimo_envio_em = NOW(),
        updated_at = NOW()
    WHERE id = p_chip_id
    RETURNING json_build_object(
        'chip_id', id,
        'msgs_enviadas_total', msgs_enviadas_total,
        'msgs_enviadas_hoje', msgs_enviadas_hoje
    ) INTO v_result;

    -- Registrar interação para histórico
    INSERT INTO chip_interactions (
        chip_id,
        tipo,
        sucesso,
        created_at
    ) VALUES (
        p_chip_id,
        'msg_enviada',
        true,
        NOW()
    );

    RETURN v_result;
END;
$$;

-- =====================================================
-- RPC: Registrar envio com erro
-- =====================================================
CREATE OR REPLACE FUNCTION chip_registrar_envio_erro(
    p_chip_id UUID,
    p_error_code INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSON;
BEGIN
    UPDATE chips
    SET
        msgs_enviadas_total = COALESCE(msgs_enviadas_total, 0) + 1,
        msgs_enviadas_hoje = COALESCE(msgs_enviadas_hoje, 0) + 1,
        erros_ultimas_24h = COALESCE(erros_ultimas_24h, 0) + 1,
        ultimo_erro_em = NOW(),
        ultimo_erro_codigo = p_error_code,
        ultimo_erro_msg = p_error_message,
        updated_at = NOW()
    WHERE id = p_chip_id
    RETURNING json_build_object(
        'chip_id', id,
        'msgs_enviadas_total', msgs_enviadas_total,
        'erros_ultimas_24h', erros_ultimas_24h
    ) INTO v_result;

    -- Registrar interação para histórico
    INSERT INTO chip_interactions (
        chip_id,
        tipo,
        sucesso,
        error_code,
        error_message,
        created_at
    ) VALUES (
        p_chip_id,
        'msg_enviada',
        false,
        p_error_code,
        p_error_message,
        NOW()
    );

    RETURN v_result;
END;
$$;

-- =====================================================
-- RPC: Registrar resposta recebida
-- =====================================================
CREATE OR REPLACE FUNCTION chip_registrar_resposta(
    p_chip_id UUID,
    p_telefone_remetente TEXT
)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_result JSON;
    v_tinha_envio_anterior BOOLEAN := false;
    v_conversa_bidirecional BOOLEAN := false;
BEGIN
    -- Verificar se enviamos para esse número nas últimas 24h
    SELECT EXISTS(
        SELECT 1 FROM chip_interactions
        WHERE chip_id = p_chip_id
        AND destinatario = p_telefone_remetente
        AND tipo = 'msg_enviada'
        AND created_at > NOW() - INTERVAL '24 hours'
        AND obteve_resposta IS NOT TRUE
    ) INTO v_tinha_envio_anterior;

    -- Se tinha envio anterior, marcar como obteve resposta
    IF v_tinha_envio_anterior THEN
        UPDATE chip_interactions
        SET obteve_resposta = true
        WHERE chip_id = p_chip_id
        AND destinatario = p_telefone_remetente
        AND tipo = 'msg_enviada'
        AND created_at > NOW() - INTERVAL '24 hours'
        AND obteve_resposta IS NOT TRUE;

        v_conversa_bidirecional := true;
    END IF;

    -- Atualizar contadores do chip
    UPDATE chips
    SET
        msgs_recebidas_total = COALESCE(msgs_recebidas_total, 0) + 1,
        conversas_bidirecionais = CASE
            WHEN v_conversa_bidirecional THEN COALESCE(conversas_bidirecionais, 0) + 1
            ELSE conversas_bidirecionais
        END,
        ultima_resposta_em = NOW(),
        updated_at = NOW()
    WHERE id = p_chip_id
    RETURNING json_build_object(
        'chip_id', id,
        'msgs_recebidas_total', msgs_recebidas_total,
        'conversas_bidirecionais', conversas_bidirecionais,
        'foi_bidirecional', v_conversa_bidirecional
    ) INTO v_result;

    -- Registrar interação
    INSERT INTO chip_interactions (
        chip_id,
        tipo,
        remetente,
        sucesso,
        created_at
    ) VALUES (
        p_chip_id,
        'msg_recebida',
        p_telefone_remetente,
        true,
        NOW()
    );

    RETURN v_result;
END;
$$;

-- =====================================================
-- RPC: Calcular taxa de resposta do chip
-- =====================================================
CREATE OR REPLACE FUNCTION chip_calcular_taxa_resposta(p_chip_id UUID)
RETURNS NUMERIC
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_enviadas INTEGER;
    v_com_resposta INTEGER;
    v_taxa NUMERIC;
BEGIN
    -- Contar mensagens enviadas nos últimos 7 dias
    SELECT COUNT(*) INTO v_enviadas
    FROM chip_interactions
    WHERE chip_id = p_chip_id
    AND tipo = 'msg_enviada'
    AND created_at > NOW() - INTERVAL '7 days';

    -- Contar mensagens que obtiveram resposta
    SELECT COUNT(*) INTO v_com_resposta
    FROM chip_interactions
    WHERE chip_id = p_chip_id
    AND tipo = 'msg_enviada'
    AND obteve_resposta = true
    AND created_at > NOW() - INTERVAL '7 days';

    -- Calcular taxa
    IF v_enviadas > 0 THEN
        v_taxa := (v_com_resposta::NUMERIC / v_enviadas::NUMERIC) * 100;
    ELSE
        v_taxa := 0;
    END IF;

    -- Atualizar chip
    UPDATE chips
    SET taxa_resposta = v_taxa
    WHERE id = p_chip_id;

    RETURN v_taxa;
END;
$$;

-- =====================================================
-- RPC: Calcular taxa de delivery do chip
-- =====================================================
CREATE OR REPLACE FUNCTION chip_calcular_taxa_delivery(
    p_chip_id UUID,
    p_dias INTEGER DEFAULT 7
)
RETURNS NUMERIC
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_enviadas INTEGER;
    v_sucesso INTEGER;
    v_taxa NUMERIC;
BEGIN
    -- Contar todas as tentativas de envio
    SELECT COUNT(*) INTO v_enviadas
    FROM chip_interactions
    WHERE chip_id = p_chip_id
    AND tipo = 'msg_enviada'
    AND created_at > NOW() - (p_dias || ' days')::INTERVAL;

    -- Contar envios com sucesso
    SELECT COUNT(*) INTO v_sucesso
    FROM chip_interactions
    WHERE chip_id = p_chip_id
    AND tipo = 'msg_enviada'
    AND sucesso = true
    AND created_at > NOW() - (p_dias || ' days')::INTERVAL;

    -- Calcular taxa
    IF v_enviadas > 0 THEN
        v_taxa := (v_sucesso::NUMERIC / v_enviadas::NUMERIC) * 100;
    ELSE
        v_taxa := 100; -- Default 100% se sem dados
    END IF;

    -- Atualizar chip
    UPDATE chips
    SET taxa_delivery = v_taxa
    WHERE id = p_chip_id;

    RETURN v_taxa;
END;
$$;

-- =====================================================
-- RPC: Resetar contadores diários de erros
-- =====================================================
CREATE OR REPLACE FUNCTION chip_resetar_erros_24h()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Recalcular erros das últimas 24h reais para cada chip
    WITH erros_por_chip AS (
        SELECT
            chip_id,
            COUNT(*) as erros
        FROM chip_interactions
        WHERE tipo = 'msg_enviada'
        AND sucesso = false
        AND created_at > NOW() - INTERVAL '24 hours'
        GROUP BY chip_id
    )
    UPDATE chips c
    SET
        erros_ultimas_24h = COALESCE(e.erros, 0),
        dias_sem_erro = CASE
            WHEN COALESCE(e.erros, 0) = 0 THEN COALESCE(dias_sem_erro, 0) + 1
            ELSE 0
        END,
        updated_at = NOW()
    FROM (SELECT id FROM chips WHERE status IN ('active', 'warming', 'ready')) AS all_chips
    LEFT JOIN erros_por_chip e ON e.chip_id = all_chips.id
    WHERE c.id = all_chips.id;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN v_count;
END;
$$;

-- =====================================================
-- RPC: Resetar contadores diários de mensagens
-- =====================================================
CREATE OR REPLACE FUNCTION chip_resetar_msgs_hoje()
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE chips
    SET
        msgs_enviadas_hoje = 0,
        updated_at = NOW()
    WHERE status IN ('active', 'warming', 'ready');

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN v_count;
END;
$$;

-- =====================================================
-- Adicionar colunas se não existirem
-- =====================================================
DO $$
BEGIN
    -- Colunas no chips
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chips' AND column_name = 'ultimo_erro_codigo') THEN
        ALTER TABLE chips ADD COLUMN ultimo_erro_codigo INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chips' AND column_name = 'ultimo_erro_msg') THEN
        ALTER TABLE chips ADD COLUMN ultimo_erro_msg TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chips' AND column_name = 'ultimo_erro_em') THEN
        ALTER TABLE chips ADD COLUMN ultimo_erro_em TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chips' AND column_name = 'ultima_resposta_em') THEN
        ALTER TABLE chips ADD COLUMN ultima_resposta_em TIMESTAMPTZ;
    END IF;

    -- Colunas no chip_interactions
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chip_interactions' AND column_name = 'destinatario') THEN
        ALTER TABLE chip_interactions ADD COLUMN destinatario TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chip_interactions' AND column_name = 'remetente') THEN
        ALTER TABLE chip_interactions ADD COLUMN remetente TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chip_interactions' AND column_name = 'obteve_resposta') THEN
        ALTER TABLE chip_interactions ADD COLUMN obteve_resposta BOOLEAN;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chip_interactions' AND column_name = 'error_code') THEN
        ALTER TABLE chip_interactions ADD COLUMN error_code INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'chip_interactions' AND column_name = 'error_message') THEN
        ALTER TABLE chip_interactions ADD COLUMN error_message TEXT;
    END IF;
END
$$;

-- =====================================================
-- Índices para performance
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_chip_interactions_chip_tipo_date
ON chip_interactions(chip_id, tipo, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chip_interactions_destinatario
ON chip_interactions(chip_id, destinatario)
WHERE destinatario IS NOT NULL;

-- =====================================================
-- Grant permissions
-- =====================================================
GRANT EXECUTE ON FUNCTION chip_registrar_envio_sucesso(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_registrar_envio_erro(UUID, INTEGER, TEXT) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_registrar_resposta(UUID, TEXT) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_calcular_taxa_resposta(UUID) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_calcular_taxa_delivery(UUID, INTEGER) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_resetar_erros_24h() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION chip_resetar_msgs_hoje() TO authenticated, service_role;
