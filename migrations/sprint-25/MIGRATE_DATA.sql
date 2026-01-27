-- =====================================================
-- Sprint 25: MIGRAÇÃO DE DADOS
-- whatsapp_instances → chips
--
-- EXECUTE APÓS APPLY_ME.sql
-- URL: https://supabase.com/dashboard/project/jyqgbzhqavgpxqacduoi/sql
-- =====================================================

-- =====================================================
-- PASSO 1: Verificar se as tabelas existem
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chips') THEN
        RAISE EXCEPTION 'Tabela chips não existe. Execute APPLY_ME.sql primeiro!';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'whatsapp_instances') THEN
        RAISE EXCEPTION 'Tabela whatsapp_instances não existe. Nenhum dado para migrar.';
    END IF;
END $$;


-- =====================================================
-- PASSO 2: Migrar dados
-- =====================================================
INSERT INTO chips (
    -- Dados básicos
    telefone,
    instance_name,

    -- Estado Evolution
    evolution_connected,

    -- Status (mapeado do status antigo)
    status,

    -- Métricas
    msgs_enviadas_hoje,
    limite_hora,
    limite_dia,

    -- Para chips já conectados, assumir que estão em operação
    fase_warmup,
    trust_score,
    trust_level,

    -- Permissões (chips conectados já podem operar)
    pode_prospectar,
    pode_followup,
    pode_responder,

    -- Auditoria
    created_at,
    updated_at,

    -- Ban info
    banned_at,
    ban_reason
)
SELECT
    -- Dados básicos
    COALESCE(wi.phone, 'unknown_' || wi.instance_id) as telefone,
    wi.instance_name,

    -- Estado Evolution
    (wi.status = 'connected') as evolution_connected,

    -- Mapeamento de status
    CASE
        WHEN wi.status = 'banned' THEN 'banned'
        WHEN wi.status = 'connected' AND wi.is_active = true THEN 'active'
        WHEN wi.status = 'connected' AND wi.is_active = false THEN 'paused'
        WHEN wi.status = 'disconnected' THEN 'pending'
        WHEN wi.status = 'connecting' THEN 'pending'
        ELSE 'pending'
    END as status,

    -- Métricas
    COALESCE(wi.messages_sent_today, 0) as msgs_enviadas_hoje,
    COALESCE(wi.hourly_limit, 50) as limite_hora,
    COALESCE(wi.daily_limit, 500) as limite_dia,

    -- Para chips já conectados, assumir em operação
    CASE
        WHEN wi.status = 'connected' THEN 'operacao'
        ELSE 'repouso'
    END as fase_warmup,

    -- Trust score: chips conectados começam com 70, outros com 50
    CASE
        WHEN wi.status = 'connected' AND wi.is_active = true THEN 70
        WHEN wi.status = 'banned' THEN 0
        ELSE 50
    END as trust_score,

    -- Trust level correspondente
    CASE
        WHEN wi.status = 'connected' AND wi.is_active = true THEN 'amarelo'
        WHEN wi.status = 'banned' THEN 'critico'
        ELSE 'amarelo'
    END as trust_level,

    -- Permissões (chips ativos já podem operar)
    (wi.status = 'connected' AND wi.is_active = true) as pode_prospectar,
    (wi.status = 'connected' AND wi.is_active = true) as pode_followup,
    (wi.status = 'connected') as pode_responder,

    -- Auditoria
    wi.created_at,
    wi.updated_at,

    -- Ban info
    CASE WHEN wi.status = 'banned' THEN wi.updated_at ELSE NULL END as banned_at,
    CASE WHEN wi.status = 'banned' THEN 'Migrado de whatsapp_instances com status banned' ELSE NULL END as ban_reason

FROM whatsapp_instances wi
WHERE NOT EXISTS (
    -- Não duplicar se já existe um chip com mesmo instance_name
    SELECT 1 FROM chips c WHERE c.instance_name = wi.instance_name
);


-- =====================================================
-- PASSO 3: Registrar transições iniciais para auditoria
-- =====================================================
INSERT INTO chip_transitions (
    chip_id,
    from_status,
    to_status,
    from_trust_score,
    to_trust_score,
    reason,
    triggered_by,
    metadata
)
SELECT
    c.id,
    NULL as from_status,
    c.status as to_status,
    NULL as from_trust_score,
    c.trust_score as to_trust_score,
    'Migração de whatsapp_instances para chips (Sprint 25)' as reason,
    'migration' as triggered_by,
    jsonb_build_object(
        'migration_date', now(),
        'source_table', 'whatsapp_instances',
        'original_phone', c.telefone
    ) as metadata
FROM chips c
WHERE c.created_at > now() - interval '5 minutes';  -- Apenas os recém-migrados


-- =====================================================
-- PASSO 4: Relatório de migração
-- =====================================================
DO $$
DECLARE
    total_whatsapp int;
    total_chips int;
    active_chips int;
    pending_chips int;
    banned_chips int;
BEGIN
    SELECT COUNT(*) INTO total_whatsapp FROM whatsapp_instances;
    SELECT COUNT(*) INTO total_chips FROM chips;
    SELECT COUNT(*) INTO active_chips FROM chips WHERE status = 'active';
    SELECT COUNT(*) INTO pending_chips FROM chips WHERE status = 'pending';
    SELECT COUNT(*) INTO banned_chips FROM chips WHERE status = 'banned';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'RELATÓRIO DE MIGRAÇÃO';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'whatsapp_instances: % registros', total_whatsapp;
    RAISE NOTICE 'chips (após migração): % registros', total_chips;
    RAISE NOTICE '  - active: %', active_chips;
    RAISE NOTICE '  - pending: %', pending_chips;
    RAISE NOTICE '  - banned: %', banned_chips;
    RAISE NOTICE '========================================';
END $$;


-- =====================================================
-- VERIFICAÇÃO FINAL
-- =====================================================
SELECT
    'RESUMO DA MIGRAÇÃO' as info,
    (SELECT COUNT(*) FROM whatsapp_instances) as "whatsapp_instances",
    (SELECT COUNT(*) FROM chips) as "chips_total",
    (SELECT COUNT(*) FROM chips WHERE status = 'active') as "chips_active",
    (SELECT COUNT(*) FROM chips WHERE status = 'pending') as "chips_pending",
    (SELECT COUNT(*) FROM chips WHERE status = 'banned') as "chips_banned";
