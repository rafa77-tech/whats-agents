/**
 * Constantes para o modulo Conversas
 * Sprint 43: UX & Operacao Unificada
 */

// ============================================
// Status Constants
// ============================================

export const CONVERSATION_STATUS_LABELS: Record<string, string> = {
  ativa: 'Ativa',
  pausada: 'Pausada',
  encerrada: 'Encerrada',
  arquivada: 'Arquivada',
}

export const CONVERSATION_STATUS_COLORS: Record<string, string> = {
  ativa: 'bg-green-100 text-green-800',
  pausada: 'bg-yellow-100 text-yellow-800',
  encerrada: 'bg-gray-100 text-gray-800',
  arquivada: 'bg-gray-50 text-gray-500',
}

// ============================================
// Control Constants
// ============================================

export const CONTROLLED_BY_LABELS = {
  ai: 'Julia',
  human: 'Humano',
} as const

export const CONTROLLED_BY_COLORS = {
  ai: 'bg-blue-100 text-blue-800',
  human: 'bg-purple-100 text-purple-800',
} as const

// ============================================
// Message Type Constants
// ============================================

export const MESSAGE_TYPE_LABELS = {
  entrada: 'Recebida',
  saida: 'Enviada',
} as const

// ============================================
// Filter Constants
// ============================================

export const DEFAULT_FILTERS = {
  status: undefined,
  controlled_by: undefined,
  search: '',
  chip_id: undefined,
} as const

// ============================================
// Pagination Constants
// ============================================

export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100
