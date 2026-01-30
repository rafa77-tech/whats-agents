-- Sprint 41: RPC para atualizar status de entrega de uma interação
-- Busca interação pelo provider_message_id e atualiza o delivery_status

CREATE OR REPLACE FUNCTION interacao_atualizar_delivery_status(
    p_provider_message_id TEXT,
    p_status TEXT,
    p_chip_id UUID DEFAULT NULL
)
RETURNS TABLE (
    interacao_id UUID,
    atualizado BOOLEAN,
    status_anterior TEXT,
    status_novo TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_interacao_id UUID;
    v_status_anterior TEXT;
BEGIN
    -- Buscar interação pelo provider_message_id
    SELECT id, delivery_status
    INTO v_interacao_id, v_status_anterior
    FROM interacoes
    WHERE provider_message_id = p_provider_message_id
    LIMIT 1;

    -- Se não encontrou, retorna sem atualizar
    IF v_interacao_id IS NULL THEN
        RETURN QUERY SELECT
            NULL::UUID AS interacao_id,
            FALSE AS atualizado,
            NULL::TEXT AS status_anterior,
            p_status AS status_novo;
        RETURN;
    END IF;

    -- Atualizar status (só avança na progressão: pending -> sent -> delivered -> read)
    -- Não retrocede status (ex: read -> delivered)
    IF v_status_anterior IS NULL
       OR (v_status_anterior = 'pending' AND p_status IN ('sent', 'delivered', 'read', 'failed'))
       OR (v_status_anterior = 'sent' AND p_status IN ('delivered', 'read', 'failed'))
       OR (v_status_anterior = 'delivered' AND p_status = 'read')
    THEN
        UPDATE interacoes
        SET
            delivery_status = p_status,
            delivery_status_at = NOW(),
            chip_id = COALESCE(p_chip_id, chip_id)
        WHERE id = v_interacao_id;

        RETURN QUERY SELECT
            v_interacao_id AS interacao_id,
            TRUE AS atualizado,
            v_status_anterior AS status_anterior,
            p_status AS status_novo;
    ELSE
        -- Status não mudou ou seria retrocesso
        RETURN QUERY SELECT
            v_interacao_id AS interacao_id,
            FALSE AS atualizado,
            v_status_anterior AS status_anterior,
            v_status_anterior AS status_novo;
    END IF;
END;
$$;

COMMENT ON FUNCTION interacao_atualizar_delivery_status IS
    'Atualiza status de entrega de uma interação de forma atômica. Só avança na progressão de status.';
