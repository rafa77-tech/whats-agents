-- =====================================================
-- Sprint 39: Tabela de Agendamento de Warmup
-- Scheduler de atividades para aquecimento de chips
-- =====================================================

-- =====================================================
-- TABELA: warmup_schedule
-- Armazena atividades agendadas para warmup de chips
-- =====================================================
CREATE TABLE IF NOT EXISTS warmup_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chip_id UUID NOT NULL REFERENCES chips(id) ON DELETE CASCADE,

    -- Tipo de atividade
    tipo TEXT NOT NULL CHECK (tipo IN (
        'conversa_par',       -- Conversa com outro chip
        'entrar_grupo',       -- Entrar em grupo WhatsApp
        'mensagem_grupo',     -- Enviar mensagem em grupo
        'atualizar_perfil',   -- Atualizar foto/status
        'enviar_midia',       -- Enviar audio/imagem
        'marcar_lido'         -- Marcar mensagens como lidas
    )),

    -- Agendamento
    scheduled_for TIMESTAMPTZ NOT NULL,
    prioridade INT DEFAULT 5 CHECK (prioridade >= 1 AND prioridade <= 10),

    -- Dados extras para execucao
    dados JSONB DEFAULT '{}',

    -- Status da atividade
    status TEXT NOT NULL DEFAULT 'agendada' CHECK (status IN (
        'agendada',    -- Aguardando execucao
        'executada',   -- Executada com sucesso
        'falhou',      -- Falhou na execucao
        'cancelada'    -- Cancelada manualmente ou por demote
    )),

    -- Resultado da execucao
    executed_at TIMESTAMPTZ,
    resultado JSONB DEFAULT '{}',
    error_message TEXT,

    -- Auditoria
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_warmup_schedule_chip_date
    ON warmup_schedule(chip_id, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_warmup_schedule_pending
    ON warmup_schedule(scheduled_for, prioridade DESC)
    WHERE status = 'agendada';

CREATE INDEX IF NOT EXISTS idx_warmup_schedule_status_date
    ON warmup_schedule(status, scheduled_for);

-- Indice para busca por data (para dashboard)
CREATE INDEX IF NOT EXISTS idx_warmup_schedule_day
    ON warmup_schedule(DATE(scheduled_for AT TIME ZONE 'America/Sao_Paulo'));


-- =====================================================
-- FUNCAO: Gerar atividades de warmup para um chip
-- Chamada pelo job scheduler
-- =====================================================
CREATE OR REPLACE FUNCTION gerar_agenda_warmup(
    p_chip_id UUID,
    p_data DATE DEFAULT CURRENT_DATE
)
RETURNS INT
LANGUAGE plpgsql
AS $$
DECLARE
    v_chip RECORD;
    v_config RECORD;
    v_qtd_atividades INT;
    v_intervalo_min INT;
    v_hora_atual TIME;
    v_inseridos INT := 0;
BEGIN
    -- Buscar dados do chip
    SELECT
        id, fase_warmup, trust_score, limite_dia
    INTO v_chip
    FROM chips
    WHERE id = p_chip_id AND status IN ('warming', 'active');

    IF v_chip.id IS NULL THEN
        RETURN 0;
    END IF;

    -- Configuracao por fase
    CASE v_chip.fase_warmup
        WHEN 'setup' THEN
            v_qtd_atividades := 2 + floor(random() * 4)::int;
            v_intervalo_min := 60;
        WHEN 'primeiros_contatos' THEN
            v_qtd_atividades := 5 + floor(random() * 6)::int;
            v_intervalo_min := 45;
        WHEN 'expansao' THEN
            v_qtd_atividades := 10 + floor(random() * 11)::int;
            v_intervalo_min := 30;
        WHEN 'pre_operacao' THEN
            v_qtd_atividades := 15 + floor(random() * 16)::int;
            v_intervalo_min := 20;
        WHEN 'teste_graduacao' THEN
            v_qtd_atividades := 20 + floor(random() * 21)::int;
            v_intervalo_min := 15;
        WHEN 'operacao' THEN
            v_qtd_atividades := 5 + floor(random() * 11)::int;
            v_intervalo_min := 60;
        ELSE
            RETURN 0; -- repouso nao tem atividades
    END CASE;

    -- Ajustar por trust score
    v_qtd_atividades := LEAST(
        v_qtd_atividades,
        COALESCE(v_chip.limite_dia, 100),
        GREATEST(1, floor(v_qtd_atividades * v_chip.trust_score / 80.0)::int)
    );

    -- Gerar atividades distribuidas entre 8h e 20h
    FOR i IN 1..v_qtd_atividades LOOP
        v_hora_atual := TIME '08:00' + (i - 1) * (INTERVAL '12 hours' / v_qtd_atividades)
                        + (random() * v_intervalo_min || ' minutes')::interval;

        INSERT INTO warmup_schedule (
            chip_id,
            tipo,
            scheduled_for,
            prioridade,
            status
        )
        VALUES (
            p_chip_id,
            (ARRAY['conversa_par', 'marcar_lido', 'enviar_midia', 'mensagem_grupo'])[1 + floor(random() * 4)::int],
            p_data + v_hora_atual,
            GREATEST(1, 10 - i),
            'agendada'
        );

        v_inseridos := v_inseridos + 1;
    END LOOP;

    RETURN v_inseridos;
END;
$$;


-- =====================================================
-- FUNCAO: Estatisticas do scheduler por dia
-- Usada pelo dashboard
-- =====================================================
CREATE OR REPLACE FUNCTION obter_estatisticas_scheduler(
    p_data DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_stats JSONB;
    v_by_type JSONB;
BEGIN
    -- Estatisticas gerais
    SELECT jsonb_build_object(
        'date', p_data::text,
        'totalPlanned', COUNT(*) FILTER (WHERE status IN ('agendada', 'executada', 'falhou', 'cancelada')),
        'totalExecuted', COUNT(*) FILTER (WHERE status = 'executada'),
        'totalFailed', COUNT(*) FILTER (WHERE status = 'falhou'),
        'totalCancelled', COUNT(*) FILTER (WHERE status = 'cancelada')
    )
    INTO v_stats
    FROM warmup_schedule
    WHERE DATE(scheduled_for AT TIME ZONE 'America/Sao_Paulo') = p_data;

    -- Por tipo
    SELECT jsonb_object_agg(
        UPPER(tipo),
        jsonb_build_object(
            'planned', COALESCE(SUM(1), 0),
            'executed', COALESCE(SUM(CASE WHEN status = 'executada' THEN 1 ELSE 0 END), 0),
            'failed', COALESCE(SUM(CASE WHEN status = 'falhou' THEN 1 ELSE 0 END), 0)
        )
    )
    INTO v_by_type
    FROM warmup_schedule
    WHERE DATE(scheduled_for AT TIME ZONE 'America/Sao_Paulo') = p_data
    GROUP BY tipo;

    -- Garantir todos os tipos existem
    v_by_type := COALESCE(v_by_type, '{}'::jsonb);

    -- Adicionar tipos que podem estar faltando
    IF NOT v_by_type ? 'CONVERSA_PAR' THEN
        v_by_type := v_by_type || '{"CONVERSA_PAR": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;
    IF NOT v_by_type ? 'MARCAR_LIDO' THEN
        v_by_type := v_by_type || '{"MARCAR_LIDO": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;
    IF NOT v_by_type ? 'ENTRAR_GRUPO' THEN
        v_by_type := v_by_type || '{"ENTRAR_GRUPO": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;
    IF NOT v_by_type ? 'ENVIAR_MIDIA' THEN
        v_by_type := v_by_type || '{"ENVIAR_MIDIA": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;
    IF NOT v_by_type ? 'MENSAGEM_GRUPO' THEN
        v_by_type := v_by_type || '{"MENSAGEM_GRUPO": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;
    IF NOT v_by_type ? 'ATUALIZAR_PERFIL' THEN
        v_by_type := v_by_type || '{"ATUALIZAR_PERFIL": {"planned": 0, "executed": 0, "failed": 0}}'::jsonb;
    END IF;

    v_stats := v_stats || jsonb_build_object('byType', v_by_type);

    RETURN v_stats;
END;
$$;


-- =====================================================
-- TRIGGER: Atualizar updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_warmup_schedule_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_warmup_schedule_updated ON warmup_schedule;
CREATE TRIGGER trg_warmup_schedule_updated
    BEFORE UPDATE ON warmup_schedule
    FOR EACH ROW
    EXECUTE FUNCTION update_warmup_schedule_timestamp();


-- =====================================================
-- COMENTARIOS
-- =====================================================
COMMENT ON TABLE warmup_schedule IS 'Atividades de warmup agendadas para chips';
COMMENT ON COLUMN warmup_schedule.tipo IS 'Tipo de atividade: conversa_par, entrar_grupo, mensagem_grupo, atualizar_perfil, enviar_midia, marcar_lido';
COMMENT ON COLUMN warmup_schedule.prioridade IS 'Prioridade 1-10, maior = mais prioritario';
COMMENT ON COLUMN warmup_schedule.dados IS 'Dados extras para execucao (ex: par_id para conversa_par)';
COMMENT ON FUNCTION gerar_agenda_warmup IS 'Gera atividades de warmup para um chip baseado na fase atual';
COMMENT ON FUNCTION obter_estatisticas_scheduler IS 'Retorna estatisticas do scheduler para uma data';
