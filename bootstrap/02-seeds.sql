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
    ('supabase_project_ref', 'TROCAR_PELO_REF_DO_PROD', 'Project reference - CRÍTICO para hard guard')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    description = EXCLUDED.description,
    updated_at = now();

-- -----------------------------------------------------------------------------
-- 2. FEATURE FLAGS ESSENCIAIS
-- -----------------------------------------------------------------------------
-- Flags que o sistema espera existir

INSERT INTO public.feature_flags (key, enabled, description)
VALUES
    ('external_handoff', true, 'Habilita handoff externo via link'),
    ('campaign_attribution', true, 'Habilita atribuição de campanhas'),
    ('dynamic_lock', true, 'Habilita lock dinâmico 30/60 min'),
    ('error_classifier', true, 'Habilita classificador de erros')
ON CONFLICT (key) DO UPDATE SET 
    enabled = EXCLUDED.enabled,
    description = EXCLUDED.description,
    updated_at = now();

-- -----------------------------------------------------------------------------
-- 3. JULIA STATUS (Estado inicial)
-- -----------------------------------------------------------------------------
-- Julia começa PAUSADA para validação manual antes de ativar

INSERT INTO public.julia_status (status, motivo, alterado_via)
VALUES ('pausado', 'Deploy inicial - aguardando validação', 'bootstrap')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- VERIFICAÇÃO
-- -----------------------------------------------------------------------------
-- Rodar após aplicar para confirmar:

-- SELECT * FROM app_settings;
-- SELECT * FROM feature_flags;
-- SELECT * FROM julia_status ORDER BY created_at DESC LIMIT 1;
