-- Sprint 44 T04.1: Função de reserva transacional de vagas
-- Evita race conditions com FOR UPDATE NOWAIT

-- Função para reserva atômica de vaga
CREATE OR REPLACE FUNCTION reservar_vaga_transacional(
    p_vaga_id UUID,
    p_cliente_id UUID,
    p_dados_reserva JSONB DEFAULT '{}'
) RETURNS JSONB AS $$
DECLARE
    v_vaga RECORD;
    v_result JSONB;
BEGIN
    -- Lock na vaga para evitar race condition
    SELECT * INTO v_vaga
    FROM vagas
    WHERE id = p_vaga_id
    FOR UPDATE NOWAIT;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga não encontrada',
            'error_code', 'VAGA_NAO_ENCONTRADA'
        );
    END IF;

    IF v_vaga.status != 'aberta' AND v_vaga.status != 'anunciada' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga não está disponível',
            'error_code', 'VAGA_INDISPONIVEL',
            'status_atual', v_vaga.status
        );
    END IF;

    -- Atualizar vaga
    UPDATE vagas
    SET status = 'reservada',
        cliente_id = p_cliente_id,
        updated_at = NOW()
    WHERE id = p_vaga_id;

    -- Criar business event
    INSERT INTO business_events (
        event_type,
        cliente_id,
        vaga_id,
        event_props,
        source,
        created_at
    ) VALUES (
        'vaga_reservada',
        p_cliente_id,
        p_vaga_id,
        p_dados_reserva || jsonb_build_object('via', 'transacional'),
        'backend',
        NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'vaga_id', p_vaga_id,
        'cliente_id', p_cliente_id,
        'status_anterior', v_vaga.status
    );

EXCEPTION
    WHEN lock_not_available THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga em uso por outro processo, tente novamente',
            'error_code', 'LOCK_CONFLICT'
        );
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'error_code', 'INTERNAL_ERROR'
        );
END;
$$ LANGUAGE plpgsql;

-- Função para cancelar reserva transacional
CREATE OR REPLACE FUNCTION cancelar_reserva_transacional(
    p_vaga_id UUID,
    p_motivo TEXT DEFAULT 'cancelamento_usuario'
) RETURNS JSONB AS $$
DECLARE
    v_vaga RECORD;
BEGIN
    -- Lock na vaga
    SELECT * INTO v_vaga
    FROM vagas
    WHERE id = p_vaga_id
    FOR UPDATE NOWAIT;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga não encontrada',
            'error_code', 'VAGA_NAO_ENCONTRADA'
        );
    END IF;

    IF v_vaga.status != 'reservada' THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga não está reservada',
            'error_code', 'STATUS_INVALIDO',
            'status_atual', v_vaga.status
        );
    END IF;

    -- Restaurar vaga para aberta
    UPDATE vagas
    SET status = 'aberta',
        cliente_id = NULL,
        updated_at = NOW()
    WHERE id = p_vaga_id;

    -- Criar business event de cancelamento
    INSERT INTO business_events (
        event_type,
        cliente_id,
        vaga_id,
        event_props,
        source,
        created_at
    ) VALUES (
        'reserva_cancelada',
        v_vaga.cliente_id,
        p_vaga_id,
        jsonb_build_object('motivo', p_motivo, 'via', 'transacional'),
        'backend',
        NOW()
    );

    RETURN jsonb_build_object(
        'success', true,
        'vaga_id', p_vaga_id,
        'motivo', p_motivo
    );

EXCEPTION
    WHEN lock_not_available THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', 'Vaga em uso por outro processo',
            'error_code', 'LOCK_CONFLICT'
        );
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM,
            'error_code', 'INTERNAL_ERROR'
        );
END;
$$ LANGUAGE plpgsql;

-- Comentários para documentação
COMMENT ON FUNCTION reservar_vaga_transacional IS 'Sprint 44 T04.1: Reserva atômica de vaga com lock pessimista';
COMMENT ON FUNCTION cancelar_reserva_transacional IS 'Sprint 44 T04.1: Cancelamento atômico de reserva';
