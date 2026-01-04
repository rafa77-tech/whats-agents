-- Migration: create_dashboard_notifications
-- Sprint 28 - E07: Sistema de Notificacoes

-- Tabela de notificacoes do dashboard
CREATE TABLE IF NOT EXISTS dashboard_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    data JSONB,
    read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_user
    ON dashboard_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_unread
    ON dashboard_notifications(user_id, read) WHERE read = FALSE;
CREATE INDEX IF NOT EXISTS idx_dashboard_notifications_created
    ON dashboard_notifications(created_at DESC);

-- Configuracoes de notificacao por usuario
CREATE TABLE IF NOT EXISTS dashboard_notification_config (
    user_id UUID PRIMARY KEY,
    push_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    toast_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    types JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Push subscriptions
CREATE TABLE IF NOT EXISTS dashboard_push_subscriptions (
    user_id UUID PRIMARY KEY,
    subscription JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS (opcional - habilitar se necessario)
-- ALTER TABLE dashboard_notifications ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE dashboard_notification_config ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE dashboard_push_subscriptions ENABLE ROW LEVEL SECURITY;

-- Enable Realtime para notificacoes em tempo real
-- ALTER PUBLICATION supabase_realtime ADD TABLE dashboard_notifications;

-- Comentario: Esta migration cria as tabelas necessarias para o sistema de
-- notificacoes do dashboard. O user_id referencia usuarios do sistema de auth,
-- que podem ser tanto da tabela auth.users quanto de uma tabela dashboard_users
-- customizada. Ajuste as foreign keys conforme necessario.
