-- Migration: Criar índices para performance
-- Executar no Supabase SQL Editor

-- Índice para busca de cliente por telefone
CREATE INDEX IF NOT EXISTS idx_clientes_telefone
ON clientes(telefone);

-- Índice para busca de conversa ativa
CREATE INDEX IF NOT EXISTS idx_conversations_cliente_status
ON conversations(cliente_id, status)
WHERE status = 'active';

-- Índice para histórico de interações
CREATE INDEX IF NOT EXISTS idx_interacoes_conversa_data
ON interacoes(conversation_id, created_at DESC);

-- Índice para vagas abertas
CREATE INDEX IF NOT EXISTS idx_vagas_especialidade_status
ON vagas(especialidade_id, status, data)
WHERE status = 'aberta';

-- Índice para fila de mensagens (se tabela existir)
CREATE INDEX IF NOT EXISTS idx_fila_processamento
ON fila_mensagens(status, prioridade DESC, agendar_para)
WHERE status = 'pendente';

-- Índice para busca por tags (GIN index para JSONB)
CREATE INDEX IF NOT EXISTS idx_clientes_tags
ON clientes USING GIN(tags);

-- Índice para envios de campanha
CREATE INDEX IF NOT EXISTS idx_envios_campanha_campanha_status
ON envios_campanha(campanha_id, status);

-- Índice para handoffs
CREATE INDEX IF NOT EXISTS idx_handoffs_conversa_status
ON handoffs(conversation_id, status);

