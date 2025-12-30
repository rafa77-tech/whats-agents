-- =============================================================================
-- SEEDS MÍNIMOS PARA PRODUÇÃO
-- =============================================================================
-- IMPORTANTE: Editar os valores antes de aplicar no PROD!
-- 
-- Este arquivo contém apenas configurações obrigatórias para o sistema funcionar.
-- NÃO contém dados de teste.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. APP SETTINGS (Hard Guards)
-- -----------------------------------------------------------------------------
-- EDITAR ANTES DE APLICAR:
-- - environment: trocar para 'production'
-- - supabase_project_ref: trocar para o ref do projeto PROD

INSERT INTO public.app_settings (key, value, description)
VALUES
    ('environment', 'production', 'Environment marker - CRÍTICO para hard guard'),
    ('supabase_project_ref', 'jyqgbzhqavgpxqacduoi', 'Project reference - CRÍTICO para hard guard')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = now();

-- -----------------------------------------------------------------------------
-- 2. FEATURE FLAGS ESSENCIAIS
-- -----------------------------------------------------------------------------
-- Flags que o sistema espera existir
-- Estrutura: key, value (JSONB), description

INSERT INTO public.feature_flags (key, value, description)
VALUES
    ('external_handoff', '{"enabled": true}'::jsonb, 'Habilita handoff externo via link'),
    ('campaign_attribution', '{"enabled": true}'::jsonb, 'Habilita atribuição de campanhas'),
    ('dynamic_lock', '{"enabled": true}'::jsonb, 'Habilita lock dinâmico 30/60 min'),
    ('error_classifier', '{"enabled": true}'::jsonb, 'Habilita classificador de erros')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = now();

-- -----------------------------------------------------------------------------
-- 3. JULIA STATUS (Estado inicial)
-- -----------------------------------------------------------------------------
-- Julia começa PAUSADA para validação manual antes de ativar
-- alterado_via aceita: 'slack', 'sistema', 'api', 'manual'

INSERT INTO public.julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Deploy inicial - aguardando validação', 'manual');

-- -----------------------------------------------------------------------------
-- VERIFICAÇÃO
-- -----------------------------------------------------------------------------
-- Rodar após aplicar para confirmar:

-- SELECT * FROM app_settings;
-- SELECT * FROM feature_flags;
-- SELECT * FROM julia_status ORDER BY created_at DESC LIMIT 1;
