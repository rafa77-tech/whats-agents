/**
 * Tipos centralizados para o módulo Ajuda
 * Sprint 43: UX & Operação Unificada
 */

// ============================================
// Tipos de Pedido de Ajuda
// ============================================

export type PedidoAjudaStatus = 'pendente' | 'respondido' | 'timeout' | 'cancelado'

export interface PedidoAjuda {
  id: string
  conversa_id: string
  cliente_id: string
  hospital_id?: string
  pergunta_original: string
  contexto?: string
  status: PedidoAjudaStatus
  resposta?: string
  respondido_por?: string
  respondido_em?: string
  criado_em: string
  clientes?: { nome: string; telefone: string } | null
  hospitais?: { nome: string } | null
}

// ============================================
// Tipos de Request/Response
// ============================================

export interface ListarPedidosParams {
  status?: string // comma-separated list: "pendente,timeout" or empty for all
}

export interface ResponderPedidoRequest {
  resposta: string
}

export interface ResponderPedidoResponse {
  id: string
  status: 'respondido'
  resposta: string
  respondido_por: string
  respondido_em: string
}

// ============================================
// Tipos de Configuração de Status
// ============================================

export interface StatusConfig {
  label: string
  color: string
  icon: string
}

export const STATUS_CONFIG: Record<PedidoAjudaStatus, StatusConfig> = {
  pendente: {
    label: 'Pendente',
    color: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
    icon: 'Clock',
  },
  respondido: {
    label: 'Respondido',
    color: 'bg-status-success text-status-success-foreground border-status-success-border',
    icon: 'CheckCircle2',
  },
  timeout: {
    label: 'Timeout',
    color: 'bg-trust-laranja text-trust-laranja-foreground border-trust-laranja',
    icon: 'Clock',
  },
  cancelado: {
    label: 'Cancelado',
    color: 'bg-status-neutral text-status-neutral-foreground border-status-neutral-border',
    icon: 'HelpCircle',
  },
}
